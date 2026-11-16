"""Synthetic records only: these are not claims about real issuer actions."""

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import ValidationError

from trading.core.enums import Timeframe
from trading.storage.action_register import (
    ActionRegister,
    action_register_sha256,
    load_action_register,
)

TEST_DATASET_SHA256 = "a" * 64


def event(**changes: object) -> dict[str, object]:
    return {
        "event_id": "synthetic-1",
        "isin": "IN0000000001",
        "symbol": "INFY",
        "ex_date": "2024-02-01",
        "publication_date": "2024-01-10",
        "action_type": "bonus",
        "original_ratio": "1:1",
        "verified_factor": "2",
        "source_url": "https://example.org/synthetic",
        "reviewer": "fixture-reviewer",
        "review_date": "2024-01-11",
        "price_basis": "raw",
        "volume_basis": "raw",
        **changes,
    }


def register(**changes: object) -> ActionRegister:
    return ActionRegister.model_validate({"events": [event(**changes)]})


def test_reviewed_raw_bonus_requires_publication_and_does_not_parse_ratio() -> None:
    result = register(original_ratio="unparsed original text")
    assert result.approved_adjustments(as_of=date(2024, 1, 9)) == ()
    approved = result.approved_adjustments(as_of=date(2024, 2, 1))
    assert approved[0].new_shares_per_old_share == Decimal("2")
    assert approved[0].published_date == date(2024, 1, 10)
    assert result.notices()[0].effective_date == date(2024, 2, 1)


@pytest.mark.parametrize(
    "changes",
    [
        {"publication_date": None},
        {"reviewer": None, "review_date": None},
        {"verified_factor": None},
        {"price_basis": "unknown"},
        {"volume_basis": "unknown"},
        {"volume_basis": "provider_adjusted"},
    ],
)
def test_incomplete_evidence_never_approves(changes: dict[str, object]) -> None:
    result = register(**changes)
    assert result.approved_adjustments(as_of=date(2024, 3, 1)) == ()
    assert len(result.blocked_events(as_of=date(2024, 3, 1))) == 1
    assert len(result.notices()) == 1


@pytest.mark.parametrize("kind", ["demerger", "rights", "dividend", "other"])
def test_complex_events_always_block(kind: str) -> None:
    result = register(action_type=kind, verified_factor=None)
    assert result.approved_adjustments(as_of=date(2024, 3, 1)) == ()
    assert result.blocked_events(as_of=date(2024, 3, 1)) == result.events
    with pytest.raises(ValidationError):
        register(action_type=kind)


def test_provider_adjusted_records_are_separate() -> None:
    result = register(
        price_basis="provider_adjusted", volume_basis="provider_adjusted", verified_factor=None
    )
    assert result.approved_adjustments(as_of=date(2024, 3, 1)) == ()
    assert result.provider_adjusted_events(as_of=date(2024, 3, 1)) == result.events
    assert result.blocked_events(as_of=date(2024, 3, 1)) == ()


@pytest.mark.parametrize(
    "changes",
    [
        {"verified_factor": "NaN"},
        {"verified_factor": "Infinity"},
        {"verified_factor": "1"},
        {"verified_factor": "0"},
        {"verified_factor": "0.5"},
        {"review_date": "2024-01-01"},
        {"source_url": "file:///tmp/source"},
        {"reviewer": " "},
        {"symbol": "reliance"},  # lowercase -- not a valid NSE trading symbol shape
        {"symbol": "THIS-SYMBOL-IS-WAY-TOO-LONG-FOR-NSE"},
        {"typo": True},
    ],
)
def test_invalid_records_fail_closed(changes: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        register(**changes)


def test_symbol_is_no_longer_restricted_to_the_original_five_symbol_pilot() -> None:
    """`PilotSymbol`/`NseEquitySymbol` was broadened (full-universe selector
    switch) to any validly-shaped NSE symbol, not just the original five --
    this does not weaken per-record review discipline, only which symbols
    may be named at all.
    """
    result = register(symbol="SONAL")
    assert result.events[0].symbol == "SONAL"


def test_duplicate_events_and_conflicting_identity_rejected() -> None:
    for second in [event(), event(event_id="synthetic-2", isin="IN0000000002")]:
        with pytest.raises(ValidationError):
            ActionRegister.model_validate({"events": [event(), second]})


def test_example_has_no_events_or_verified_coverage() -> None:
    result = load_action_register(Path("config/corporate_actions.example.yaml"))
    assert result.events == ()
    assert {item.symbol for item in result.coverage} == {
        "RELIANCE",
        "INFY",
        "TCS",
        "HDFCBANK",
        "ICICIBANK",
    }
    assert all(not item.verified for item in result.coverage)
    assert not result.covers(
        "INFY", Timeframe.D1, date(2024, 1, 1), date(2024, 2, 1), TEST_DATASET_SHA256
    )


def test_coverage_is_explicit_bounded_and_requires_review() -> None:
    row = {
        "symbol": "INFY",
        "timeframe": "1d",
        "candle_snapshot_sha256": TEST_DATASET_SHA256,
        "start": "2024-01-01",
        "end": "2024-12-31",
    }
    assert not ActionRegister.model_validate({"coverage": [row]}).coverage[0].verified
    with pytest.raises(ValidationError):
        ActionRegister.model_validate({"coverage": [{**row, "verified": True}]})
    row.update(
        verified=True,
        isin="IN0000000001",
        reviewer="fixture",
        review_date="2025-01-01",
        source_url="https://example.org/coverage",
    )
    result = ActionRegister.model_validate({"coverage": [row]})
    assert result.covers(
        "INFY", Timeframe.D1, date(2024, 1, 1), date(2024, 12, 31), TEST_DATASET_SHA256
    )
    assert not result.covers(
        "INFY", Timeframe.D1, date(2023, 12, 31), date(2024, 12, 31), TEST_DATASET_SHA256
    )
    assert not result.covers(
        "INFY", Timeframe.M5, date(2024, 1, 1), date(2024, 12, 31), TEST_DATASET_SHA256
    )
    assert not result.covers("INFY", Timeframe.D1, date(2024, 1, 1), date(2024, 12, 31), "b" * 64)
    assert not result.covers(
        "TCS", Timeframe.D1, date(2024, 1, 1), date(2024, 12, 31), TEST_DATASET_SHA256
    )


@pytest.mark.parametrize("content", ["events: []\nevents: []", "[]", "events: &x [*x]"])
def test_loader_rejects_ambiguous_or_invalid_yaml(tmp_path: Path, content: str) -> None:
    path = tmp_path / "actions.yaml"
    path.write_text(content)
    with pytest.raises(ValueError):
        load_action_register(path)


def test_distinct_same_day_actions_keep_distinct_event_ids() -> None:
    result = ActionRegister.model_validate({"events": [event(), event(event_id="second-id")]})
    assert [notice.event_id for notice in result.notices()] == ["synthetic-1", "second-id"]


def test_loader_size_bound(tmp_path: Path) -> None:
    path = tmp_path / "large.yaml"
    path.write_bytes(b" " * 262_145)
    with pytest.raises(ValueError, match="256 KiB"):
        load_action_register(path)


def test_review_date_gates_approval_and_reverse_split_is_supported() -> None:
    result = register(action_type="split", verified_factor="0.5", review_date="2024-02-10")
    assert result.approved_adjustments(as_of=date(2024, 2, 9)) == ()
    assert result.approved_adjustments(as_of=date(2024, 2, 10))[
        0
    ].new_shares_per_old_share == Decimal("0.5")


def test_overlapping_coverage_and_reversed_windows_rejected() -> None:
    row = {
        "symbol": "INFY",
        "timeframe": "1d",
        "start": "2024-01-01",
        "end": "2024-12-31",
    }
    with pytest.raises(ValidationError):
        ActionRegister.model_validate({"coverage": [row, row]})
    other_timeframe = {**row, "timeframe": "5m"}
    assert len(ActionRegister.model_validate({"coverage": [row, other_timeframe]}).coverage) == 2
    with pytest.raises(ValidationError):
        ActionRegister.model_validate({"coverage": [{**row, "end": "2023-01-01"}]})


def test_coverage_hash_must_be_a_sha256_digest() -> None:
    row = {
        "symbol": "INFY",
        "timeframe": "1d",
        "candle_snapshot_sha256": "not-a-hash",
        "start": "2024-01-01",
        "end": "2024-12-31",
        "verified": True,
        "isin": "IN0000000001",
        "reviewer": "fixture",
        "review_date": "2025-01-01",
        "source_url": "https://example.org/coverage",
    }
    with pytest.raises(ValidationError):
        ActionRegister.model_validate({"coverage": [row]})


def test_action_register_hash_is_order_independent_and_covers_evidence() -> None:
    first_event = event(event_id="event-a")
    second_event = event(event_id="event-b", ex_date="2024-03-01")
    first_coverage = {
        "symbol": "INFY",
        "timeframe": "1d",
        "candle_snapshot_sha256": TEST_DATASET_SHA256,
        "start": "2024-01-01",
        "end": "2024-12-31",
        "verified": False,
        "source_url": "https://example.org/evidence#sha256=abc",
    }
    second_coverage = {
        **first_coverage,
        "timeframe": "5m",
        "candle_snapshot_sha256": "b" * 64,
    }
    left = ActionRegister.model_validate(
        {"events": [first_event, second_event], "coverage": [first_coverage, second_coverage]}
    )
    right = ActionRegister.model_validate(
        {"events": [second_event, first_event], "coverage": [second_coverage, first_coverage]}
    )

    assert action_register_sha256(left) == action_register_sha256(right)
    assert len(action_register_sha256(left)) == 64
    changed = ActionRegister.model_validate(
        {
            "events": [first_event, second_event],
            "coverage": [
                first_coverage,
                {**second_coverage, "source_url": "https://example.org/other"},
            ],
        }
    )
    assert action_register_sha256(left) != action_register_sha256(changed)
