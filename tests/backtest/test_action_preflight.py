"""Both replay entry points enforce reviewed source coverage and action gates."""

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from test_runner import bar, signal

from trading.backtest.fills import BacktestProfile
from trading.backtest.reference import run_reference
from trading.backtest.runner import run_long_only
from trading.storage.action_register import ActionRegister
from trading.storage.corporate_actions import CorporateActionKind

TEST_DATASET_SHA256 = "a" * 64


@pytest.fixture(params=[run_long_only, run_reference])
def runner(request):
    return request.param


def register(*actions: tuple[str, CorporateActionKind, date]) -> ActionRegister:
    return ActionRegister.model_validate(
        {
            "events": [
                {
                    "event_id": event_id,
                    "isin": "INE002A01018",
                    "symbol": "RELIANCE",
                    "ex_date": day,
                    "action_type": kind.value,
                    "original_ratio": "recorded manually",
                    "source_url": "https://example.test/action",
                }
                for event_id, kind, day in actions
            ],
            "coverage": [
                {
                    "symbol": "RELIANCE",
                    "timeframe": "1d",
                    "candle_snapshot_sha256": TEST_DATASET_SHA256,
                    "isin": "INE002A01018",
                    "start": "2025-12-31",
                    "end": "2026-01-03",
                    "verified": True,
                    "source_url": "https://example.test/coverage",
                    "reviewer": "fixture-reviewer",
                    "review_date": "2026-01-04",
                }
            ],
        }
    )


def replay(runner, *, source="test", **kwargs):
    candles = [
        bar(0, "10", "11", "9", "10").model_copy(update={"symbol": "RELIANCE", "source": source}),
        bar(1, "13", "14", "8", "13").model_copy(update={"symbol": "RELIANCE", "source": source}),
    ]
    return runner(
        candles,
        [signal(0).model_copy(update={"id": "preflight-entry", "symbol": "RELIANCE"})],
        quantity=Decimal("1"),
        profile=BacktestProfile(),
        candle_snapshot_sha256=(TEST_DATASET_SHA256 if kwargs.get("action_register") else None),
        **kwargs,
    )


def test_real_source_without_register_fails_closed(runner):
    with pytest.raises(ValueError, match="register is required"):
        replay(runner, source="upstox")


def test_synthetic_test_bars_can_run_without_external_evidence(runner):
    result = replay(runner)
    assert len(result.trades) == 1
    assert result.action_review_flags == ()


def test_verified_empty_event_list_still_requires_window_coverage(runner):
    with pytest.raises(ValueError, match="does not cover"):
        replay(runner, action_register=ActionRegister())
    result = replay(runner, action_register=register())
    assert len(result.trades) == 1


@pytest.mark.parametrize(
    "kind", [CorporateActionKind.DEMERGER, CorporateActionKind.RIGHTS, CorporateActionKind.OTHER]
)
def test_unhandled_complex_event_blocks_replay(runner, kind):
    with pytest.raises(ValueError, match="RELIANCE"):
        replay(
            runner,
            action_register=register(("event-1", kind, date(2026, 1, 2))),
        )


@pytest.mark.parametrize("kind", [CorporateActionKind.SPLIT, CorporateActionKind.BONUS])
def test_share_action_in_window_blocks_until_position_replay_exists(runner, kind):
    with pytest.raises(ValueError, match="share-action replay"):
        replay(
            runner,
            action_register=register(("event-1", kind, date(2026, 1, 2))),
            reviewed_action_keys={"event-1"},
        )


def test_exact_review_permits_complex_event_but_keeps_audit_flag(runner):
    result = replay(
        runner,
        action_register=register(("demerger-1", CorporateActionKind.DEMERGER, date(2026, 1, 2))),
        reviewed_action_keys={"demerger-1"},
    )
    (flag,) = result.action_review_flags
    assert flag.event_key == "demerger-1"
    assert flag.source_ref == "https://example.test/action"
    assert flag.requires_review


def test_review_of_one_same_day_same_kind_event_does_not_hide_another(runner):
    with pytest.raises(ValueError, match="RELIANCE"):
        replay(
            runner,
            action_register=register(
                ("demerger-1", CorporateActionKind.DEMERGER, date(2026, 1, 2)),
                ("demerger-2", CorporateActionKind.DEMERGER, date(2026, 1, 2)),
            ),
            reviewed_action_keys={"demerger-1"},
        )


def test_action_type_from_register_is_not_inferred_from_details():
    action = register(("unknown-1", CorporateActionKind.OTHER, date(2026, 1, 2)))
    assert action.notices()[0].kind is CorporateActionKind.OTHER


def test_exchange_local_date_is_used_for_coverage():
    candle = bar(0, "10", "11", "9", "10").model_copy(
        update={
            "symbol": "RELIANCE",
            "ts_open_utc": datetime(2026, 1, 1, 20, tzinfo=UTC),
        }
    )
    result = run_long_only(
        [candle],
        [],
        quantity=Decimal("1"),
        profile=BacktestProfile(),
        action_register=register(),
        candle_snapshot_sha256=TEST_DATASET_SHA256,
    )
    assert result.trades == []
