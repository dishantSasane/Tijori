import json
from datetime import UTC, date, datetime
from decimal import Decimal, localcontext
from pathlib import Path

import pytest

from trading.core.enums import MarketId, Timeframe
from trading.core.models import Candle
from trading.storage.adjusted_ingestion import append_adjusted_candles
from trading.storage.candles import CandleStore, DuplicateCandleError
from trading.storage.corporate_actions import (
    CorporateActionKind,
    ShareAdjustment,
    adjust_for_share_actions,
    inspect_unhandled_actions,
    parse_nse_corporate_action_row,
    prepare_candles_for_storage,
    screen_backtest_symbols,
)

FIXTURES = Path(__file__).parents[1] / "fixtures" / "upstox"


def candle(
    *,
    symbol: str = "RELIANCE",
    timeframe: Timeframe = Timeframe.D1,
    ts_open_utc: datetime = datetime(2024, 1, 1, 3, 45, tzinfo=UTC),
    adj_factor: Decimal | None = None,
) -> Candle:
    return Candle(
        market=MarketId.IN_EQUITY,
        symbol=symbol,
        timeframe=timeframe,
        ts_open_utc=ts_open_utc,
        open=Decimal("100"),
        high=Decimal("110"),
        low=Decimal("90"),
        close=Decimal("105"),
        volume=Decimal("1000"),
        source="upstox",
        ingest_ts=datetime(2024, 1, 3, tzinfo=UTC),
        adj_factor=adj_factor,
    )


def split(
    *,
    action_id: str = "nse-notice-001",
    event_id: str = "reliance-event-2024-01-02",
    revision: int = 1,
    published_date: date = date(2024, 1, 1),
    effective_date: date = date(2024, 1, 2),
    ratio: str = "2",
    symbol: str = "RELIANCE",
) -> ShareAdjustment:
    return ShareAdjustment(
        action_id=action_id,
        event_id=event_id,
        revision=revision,
        market=MarketId.IN_EQUITY,
        symbol=symbol,
        kind="split",
        published_date=published_date,
        effective_date=effective_date,
        new_shares_per_old_share=Decimal(ratio),
        source_ref="https://example.test/notice",
    )


def test_two_for_one_split_adjusts_only_pre_effective_bars() -> None:
    before = candle()
    on_effective_date = candle(ts_open_utc=datetime(2024, 1, 2, 3, 45, tzinfo=UTC))

    adjusted = adjust_for_share_actions(
        [before, on_effective_date],
        [split()],
        as_of=date(2024, 1, 3),
    )

    assert adjusted[0].open == Decimal("50")
    assert adjusted[0].high == Decimal("55")
    assert adjusted[0].low == Decimal("45")
    assert adjusted[0].close == Decimal("52.5")
    assert adjusted[0].volume == Decimal("2000")
    assert adjusted[0].adj_factor == Decimal("0.5")
    assert adjusted[1] == on_effective_date
    assert before.open == Decimal("100")


def test_raw_nestle_ratio_known_answer_scales_price_and_volume_by_ten() -> None:
    adjusted = adjust_for_share_actions(
        [candle(symbol="NESTLEIND")],
        [split(ratio="10", symbol="NESTLEIND")],
        as_of=date(2024, 1, 3),
    )[0]

    assert adjusted.open == Decimal("10")
    assert adjusted.high == Decimal("11")
    assert adjusted.low == Decimal("9")
    assert adjusted.close == Decimal("10.5")
    assert adjusted.volume == Decimal("10000")
    assert adjusted.adj_factor == Decimal("0.1")


def test_upstox_nestle_2024_split_known_answer_is_pre_adjusted() -> None:
    """Upstox returns this prior close on the post-split price scale."""
    payload = json.loads((FIXTURES / "upstox_nestle_2024_split.json").read_text())
    rows = {
        row[0][:10]: row
        for row in payload["data"]["candles"]
        if row[0][:10] in {"2024-01-04", "2024-01-05"}
    }

    assert set(rows) == {"2024-01-04", "2024-01-05"}
    pre_split_close = Decimal(str(rows["2024-01-04"][4]))
    ex_date_close = Decimal(str(rows["2024-01-05"][4]))

    # NSE circular 03/2024 sets the 10:1 split effective 2024-01-05.
    # A smooth close across the 10:1 ex-date indicates that this provider
    # series has already removed the split discontinuity. Other later actions
    # may also have changed the absolute historical scale, so do not infer a
    # raw pre-split price by dividing this value by ten.
    assert pre_split_close == Decimal("1355.8")
    assert ex_date_close == Decimal("1333.2")
    assert Decimal("0.98") < ex_date_close / pre_split_close < Decimal("1.02")


def test_provider_adjusted_nestle_event_is_skipped_by_pre_storage_adjuster() -> None:
    payload = json.loads((FIXTURES / "upstox_nestle_2024_split.json").read_text())
    rows = [
        row for row in payload["data"]["candles"] if row[0][:10] in {"2024-01-04", "2024-01-05"}
    ]
    candles = [
        Candle(
            market=MarketId.IN_EQUITY,
            symbol="NESTLEIND",
            timeframe=Timeframe.D1,
            ts_open_utc=datetime.fromisoformat(row[0]).astimezone(UTC),
            open=Decimal(str(row[1])),
            high=Decimal(str(row[2])),
            low=Decimal(str(row[3])),
            close=Decimal(str(row[4])),
            volume=Decimal(str(row[5])),
            source="upstox",
            ingest_ts=datetime(2024, 1, 8, tzinfo=UTC),
        )
        for row in rows
    ]
    event = split(
        event_id="nestleind-split-2024-01-05",
        effective_date=date(2024, 1, 5),
        ratio="10",
        symbol="NESTLEIND",
    )

    prepared = prepare_candles_for_storage(
        candles,
        [event],
        as_of=date(2024, 1, 8),
        provider_adjusted_action_keys={("NESTLEIND", date(2024, 1, 5))},
    )
    assert [item.close for item in prepared] == [Decimal("1333.2"), Decimal("1355.8")]
    assert all(item.adj_factor is None for item in prepared)


def test_daily_bar_timestamp_is_compared_using_india_session_date() -> None:
    # Upstox daily bars can be timestamped at midnight IST (18:30 UTC prior day).
    bar_on_effective_session = candle(ts_open_utc=datetime(2024, 1, 1, 18, 30, tzinfo=UTC))

    adjusted = adjust_for_share_actions(
        [bar_on_effective_session],
        [split()],
        as_of=date(2024, 1, 2),
    )

    assert adjusted == [bar_on_effective_session]


def test_bonus_issue_uses_share_ratio_mechanics() -> None:
    action = ShareAdjustment(
        action_id="nse-notice-bonus",
        event_id="reliance-bonus-2024-01-02",
        revision=1,
        market=MarketId.IN_EQUITY,
        symbol="RELIANCE",
        kind="bonus",
        published_date=date(2024, 1, 1),
        effective_date=date(2024, 1, 2),
        new_shares_per_old_share=Decimal("3"),
        source_ref="https://example.test/bonus",
    )

    adjusted = adjust_for_share_actions([candle()], [action], as_of=date(2024, 1, 2))[0]

    with localcontext() as context:
        context.prec = 50
        expected_third = Decimal(1) / Decimal(3)
        expected_open = Decimal(100) * expected_third
    assert adjusted.open == expected_open
    assert adjusted.volume == Decimal("3000")
    assert adjusted.adj_factor == expected_third


def test_one_for_one_bonus_known_answer_halves_price_and_doubles_volume() -> None:
    action = ShareAdjustment(
        action_id="synthetic-bonus-1-for-1",
        event_id="synthetic-bonus-2024-01-02",
        revision=1,
        market=MarketId.IN_EQUITY,
        symbol="RELIANCE",
        kind="bonus",
        published_date=date(2024, 1, 1),
        effective_date=date(2024, 1, 2),
        new_shares_per_old_share=Decimal("2"),
        source_ref="synthetic-known-answer",
    )

    adjusted = adjust_for_share_actions([candle()], [action], as_of=date(2024, 1, 2))[0]

    assert adjusted.open == Decimal("50")
    assert adjusted.high == Decimal("55")
    assert adjusted.low == Decimal("45")
    assert adjusted.close == Decimal("52.5")
    assert adjusted.volume == Decimal("2000")
    assert adjusted.adj_factor == Decimal("0.5")


def test_daily_ingestion_adjusts_before_appending(tmp_path: Path) -> None:
    with CandleStore(tmp_path / "daily-store") as store:
        inserted = append_adjusted_candles(
            store,
            [candle()],
            [split()],
            as_of=date(2024, 1, 3),
            action_ledger_complete=True,
        )
        stored = store.query(MarketId.IN_EQUITY, "RELIANCE", Timeframe.D1)[0]

    assert inserted == 1
    assert stored.close == Decimal("52.5")
    assert stored.volume == Decimal("2000")
    assert stored.adj_factor == Decimal("0.5")


@pytest.mark.parametrize("ratio", ["3", "0.3333333333333333333333333333"])
def test_repeating_decimal_adjustment_is_idempotent_after_storage_rounding(
    tmp_path: Path, ratio: str
) -> None:
    action = split(ratio=ratio)
    with CandleStore(tmp_path / f"ratio-{ratio}") as store:
        first = append_adjusted_candles(
            store,
            [candle()],
            [action],
            as_of=date(2024, 1, 3),
            action_ledger_complete=True,
        )
        second = append_adjusted_candles(
            store,
            [candle()],
            [action],
            as_of=date(2024, 1, 3),
            action_ledger_complete=True,
        )

    assert first == 1
    assert second == 0


def test_share_adjustment_math_is_independent_of_ambient_decimal_context() -> None:
    action = split(ratio="3")
    with localcontext() as context:
        context.prec = 6
        low_precision_result = adjust_for_share_actions(
            [candle()], [action], as_of=date(2024, 1, 3)
        )
    with localcontext() as context:
        context.prec = 40
        high_precision_result = adjust_for_share_actions(
            [candle()], [action], as_of=date(2024, 1, 3)
        )

    assert low_precision_result == high_precision_result


def test_storage_rejects_mixing_corporate_action_bases(tmp_path: Path) -> None:
    with CandleStore(tmp_path / "versioned-store") as store:
        append_adjusted_candles(
            store,
            [candle()],
            [],
            as_of=date(2024, 1, 3),
            action_ledger_complete=True,
        )
        later_bar = candle(ts_open_utc=datetime(2024, 1, 2, 3, 45, tzinfo=UTC))
        with pytest.raises(ValueError, match="adjustment basis differs"):
            append_adjusted_candles(
                store,
                [later_bar],
                [split()],
                as_of=date(2024, 1, 3),
                action_ledger_complete=True,
            )


def test_storage_rejects_existing_series_without_basis_metadata(tmp_path: Path) -> None:
    with CandleStore(tmp_path / "unversioned-store") as store:
        store.append([candle()])
        with pytest.raises(ValueError, match="lacks an adjustment basis"):
            append_adjusted_candles(
                store,
                [candle(ts_open_utc=datetime(2024, 1, 2, 3, 45, tzinfo=UTC))],
                [],
                as_of=date(2024, 1, 3),
                action_ledger_complete=True,
            )


def test_direct_append_cannot_bypass_a_bound_adjustment_basis(tmp_path: Path) -> None:
    with CandleStore(tmp_path / "bound-store") as store:
        append_adjusted_candles(
            store,
            [candle()],
            [],
            as_of=date(2024, 1, 3),
            action_ledger_complete=True,
        )
        later_bar = candle(ts_open_utc=datetime(2024, 1, 2, 3, 45, tzinfo=UTC))
        with pytest.raises(ValueError, match="bound adjustment basis"):
            store.append([later_bar])


def test_failed_candle_append_does_not_leave_adjustment_basis(tmp_path: Path) -> None:
    with CandleStore(tmp_path / "atomic-store") as store:
        first = candle()
        conflicting = candle().model_copy(update={"close": Decimal("106")})
        with pytest.raises(DuplicateCandleError):
            append_adjusted_candles(
                store,
                [first, conflicting],
                [],
                as_of=date(2024, 1, 3),
                action_ledger_complete=True,
            )

        action = split()
        assert (
            append_adjusted_candles(
                store,
                [first],
                [action],
                as_of=date(2024, 1, 3),
                action_ledger_complete=True,
            )
            == 1
        )


def test_parquet_requires_matching_manifest_for_import(tmp_path: Path) -> None:
    with CandleStore(tmp_path / "source") as source:
        append_adjusted_candles(
            source,
            [candle()],
            [],
            as_of=date(2024, 1, 3),
            action_ledger_complete=True,
        )
        parquet = source.export_parquet(tmp_path / "source.parquet")

    manifest_path = parquet.with_suffix(".parquet.manifest.json")
    manifest = json.loads(manifest_path.read_text())
    manifest["parquet_sha256"] = "0" * 64
    manifest_path.write_text(json.dumps(manifest))
    with CandleStore(tmp_path / "target") as target:
        with pytest.raises(ValueError, match="belongs to another file"):
            target.load_parquet(parquet)


def test_actions_after_as_of_date_do_not_change_history() -> None:
    original = candle()

    adjusted = adjust_for_share_actions(
        [original],
        [split(effective_date=date(2024, 1, 4))],
        as_of=date(2024, 1, 3),
    )

    assert adjusted == [original]


def test_actions_for_other_symbols_do_not_change_candles() -> None:
    original = candle()

    adjusted = adjust_for_share_actions(
        [original],
        [split(symbol="TCS")],
        as_of=date(2024, 1, 3),
    )

    assert adjusted == [original]


def test_share_adjustment_rejects_unsupported_market() -> None:
    with pytest.raises(ValueError, match="India equities only"):
        ShareAdjustment(
            action_id="us-notice-001",
            event_id="us-event-001",
            revision=1,
            market=MarketId.US_EQUITY,
            symbol="RELIANCE",
            kind="split",
            published_date=date(2024, 1, 1),
            effective_date=date(2024, 1, 2),
            new_shares_per_old_share=Decimal("2"),
            source_ref="https://example.test/us-notice",
        )


def test_multiple_known_actions_compose_without_mutating_input() -> None:
    original = candle()
    actions = [
        split(),
        ShareAdjustment(
            action_id="nse-notice-bonus",
            event_id="reliance-bonus-2024-01-03",
            revision=1,
            market=MarketId.IN_EQUITY,
            symbol="RELIANCE",
            kind="bonus",
            published_date=date(2024, 1, 1),
            effective_date=date(2024, 1, 3),
            new_shares_per_old_share=Decimal("2"),
            source_ref="https://example.test/bonus",
        ),
    ]

    adjusted = adjust_for_share_actions(
        [original],
        actions,
        as_of=date(2024, 1, 3),
    )[0]

    assert adjusted.open == Decimal("25")
    assert adjusted.volume == Decimal("4000")
    assert adjusted.adj_factor == Decimal("0.25")
    assert original.open == Decimal("100")


def test_adjustment_rejects_candles_already_marked_adjusted() -> None:
    already_adjusted = candle(adj_factor=Decimal("0.5"))

    with pytest.raises(ValueError, match="already adjusted"):
        adjust_for_share_actions(
            [already_adjusted],
            [split()],
            as_of=date(2024, 1, 1),
        )


@pytest.mark.parametrize("ratio", ["0", "-1", "1"])
def test_share_adjustment_rejects_invalid_ratio(ratio: str) -> None:
    with pytest.raises(ValueError):
        split(ratio=ratio)


def test_share_adjustment_rejects_unknown_action_kind() -> None:
    with pytest.raises(ValueError):
        ShareAdjustment.model_validate(
            {
                "action_id": "nse-notice-dividend",
                "event_id": "reliance-dividend-2024-01-02",
                "revision": 1,
                "market": MarketId.IN_EQUITY,
                "symbol": "RELIANCE",
                "kind": "dividend",
                "published_date": date(2024, 1, 1),
                "effective_date": date(2024, 1, 2),
                "new_shares_per_old_share": Decimal("2"),
                "source_ref": "https://example.test/dividend",
            }
        )


def test_unpublished_action_is_not_used_in_an_earlier_replay() -> None:
    original = candle()

    adjusted = adjust_for_share_actions(
        [original],
        [split(published_date=date(2024, 1, 3))],
        as_of=date(2024, 1, 2),
    )

    assert adjusted == [original]


def test_each_replay_uses_only_the_latest_published_action_revision() -> None:
    original = candle()
    revisions = [
        split(action_id="notice-v1", event_id="event-1", revision=1, ratio="2"),
        split(
            action_id="notice-v2",
            event_id="event-1",
            revision=2,
            published_date=date(2024, 1, 3),
            ratio="3",
        ),
    ]

    on_effective_date = adjust_for_share_actions([original], revisions, as_of=date(2024, 1, 2))[0]
    after_correction = adjust_for_share_actions([original], revisions, as_of=date(2024, 1, 3))[0]

    assert on_effective_date.adj_factor == Decimal("0.5")
    with localcontext() as context:
        context.prec = 50
        expected_third = Decimal(1) / Decimal(3)
    assert after_correction.adj_factor == expected_third


def test_duplicate_action_revision_is_rejected() -> None:
    action = split(action_id="notice-v1", event_id="event-1", revision=1)
    duplicate = split(action_id="notice-v1b", event_id="event-1", revision=1)

    with pytest.raises(ValueError, match="duplicate corporate action revision"):
        adjust_for_share_actions([candle()], [action, duplicate], as_of=date(2024, 1, 3))


def test_bonus_issue_rejects_ratio_that_reduces_share_count() -> None:
    with pytest.raises(ValueError, match="bonus issues must increase"):
        ShareAdjustment(
            action_id="nse-notice-bonus-invalid",
            event_id="reliance-bonus-invalid",
            revision=1,
            market=MarketId.IN_EQUITY,
            symbol="RELIANCE",
            kind="bonus",
            published_date=date(2024, 1, 1),
            effective_date=date(2024, 1, 2),
            new_shares_per_old_share=Decimal("0.5"),
            source_ref="https://example.test/bonus",
        )


def test_reverse_split_can_reduce_share_count() -> None:
    adjusted = adjust_for_share_actions(
        [candle()],
        [split(ratio="0.2")],
        as_of=date(2024, 1, 2),
    )[0]

    assert adjusted.open == Decimal("500")
    assert adjusted.volume == Decimal("200")
    assert adjusted.adj_factor == Decimal("5")


@pytest.mark.parametrize("timeframe", [Timeframe.M1, Timeframe.M5, Timeframe.M15, Timeframe.H1])
def test_intraday_bars_before_effective_session_are_adjusted(timeframe: Timeframe) -> None:
    before = candle(timeframe=timeframe, ts_open_utc=datetime(2024, 1, 1, 3, 45, tzinfo=UTC))
    on_effective_date = candle(
        timeframe=timeframe,
        ts_open_utc=datetime(2024, 1, 2, 3, 45, tzinfo=UTC),
    )

    adjusted = adjust_for_share_actions(
        [before, on_effective_date], [split()], as_of=date(2024, 1, 3)
    )

    assert adjusted[0].close == Decimal("52.5")
    assert adjusted[0].volume == Decimal("2000")
    assert adjusted[1] == on_effective_date


@pytest.mark.parametrize(
    ("purpose", "expected_kind"),
    [
        ("Demerger", CorporateActionKind.DEMERGER),
        ("Demerger of XYZ Limited", CorporateActionKind.DEMERGER),
        ("Rights 1:4 @ Premium Rs 25/-", CorporateActionKind.RIGHTS),
        ("Rights Issue", CorporateActionKind.RIGHTS),
        ("Face Value Split (Sub-Division)", CorporateActionKind.SPLIT),
        ("Bonus 1:1", CorporateActionKind.BONUS),
        ("Interim Dividend - Rs 5 Per Share", CorporateActionKind.DIVIDEND),
        ("Unexpected corporate benefit", CorporateActionKind.OTHER),
    ],
)
def test_nse_corporate_action_row_parser_classifies_unhandled_types(
    purpose: str, expected_kind: CorporateActionKind
) -> None:
    notice = parse_nse_corporate_action_row(
        {
            "SYMBOL": "TEST",
            "PURPOSE": purpose,
            "EX-DATE": "15-May-2025",
        },
        source_ref="https://example.test/nse-actions.csv",
    )

    assert notice.symbol == "TEST"
    assert notice.effective_date == date(2025, 5, 15)
    assert notice.kind is expected_kind


def test_unhandled_action_report_flags_demerger_and_rights_in_backtest_window() -> None:
    rows = [
        {
            "SYMBOL": "DEMERGERCO",
            "PURPOSE": "Demerger of XYZ Limited",
            "EX-DATE": "15-May-2025",
        },
        {
            "SYMBOL": "RIGHTSCO",
            "PURPOSE": "Rights 1:4 @ Premium Rs 25/-",
            "EX-DATE": "20-May-2025",
        },
        {"SYMBOL": "SPLITCO", "PURPOSE": "Face Value Split", "EX-DATE": "16-May-2025"},
        {"SYMBOL": "OUTSIDE", "PURPOSE": "Demerger", "EX-DATE": "01-Jun-2025"},
        {"SYMBOL": "OTHER", "PURPOSE": "Unexpected corporate benefit", "EX-DATE": "17-May-2025"},
    ]
    notices = [
        parse_nse_corporate_action_row(row, source_ref="https://example.test/actions.csv")
        for row in rows
    ]

    report = inspect_unhandled_actions(
        notices,
        symbols={"DEMERGERCO", "RIGHTSCO", "SPLITCO", "OTHER"},
        start=date(2025, 5, 1),
        end=date(2025, 5, 31),
    )

    assert [(flag.symbol, flag.kind) for flag in report] == [
        ("DEMERGERCO", CorporateActionKind.DEMERGER),
        ("OTHER", CorporateActionKind.OTHER),
        ("RIGHTSCO", CorporateActionKind.RIGHTS),
        ("SPLITCO", CorporateActionKind.SPLIT),
    ]
    assert all(flag.requires_review for flag in report)
    assert all("no automatic adjustment" in flag.reason for flag in report)

    covered_report = inspect_unhandled_actions(
        notices,
        symbols={"DEMERGERCO", "RIGHTSCO", "SPLITCO", "OTHER"},
        start=date(2025, 5, 1),
        end=date(2025, 5, 31),
        handled_action_keys={("SPLITCO", date(2025, 5, 16))},
    )
    assert [(flag.symbol, flag.kind) for flag in covered_report] == [
        ("DEMERGERCO", CorporateActionKind.DEMERGER),
        ("OTHER", CorporateActionKind.OTHER),
        ("RIGHTSCO", CorporateActionKind.RIGHTS),
    ]

    screened = screen_backtest_symbols(
        notices,
        symbols={"DEMERGERCO", "RIGHTSCO", "SPLITCO", "OTHER"},
        start=date(2025, 5, 1),
        end=date(2025, 5, 31),
        handled_action_keys={("SPLITCO", date(2025, 5, 16))},
    )
    assert screened.eligible_symbols == ("SPLITCO",)
    assert screened.blocked_symbols == ("DEMERGERCO", "OTHER", "RIGHTSCO")
    assert len(screened.flags) == 3

    reviewed = screen_backtest_symbols(
        notices,
        symbols={"DEMERGERCO", "RIGHTSCO", "SPLITCO", "OTHER"},
        start=date(2025, 5, 1),
        end=date(2025, 5, 31),
        handled_action_keys={("SPLITCO", date(2025, 5, 16))},
        reviewed_action_keys={("DEMERGERCO", date(2025, 5, 15), CorporateActionKind.DEMERGER)},
    )
    assert reviewed.eligible_symbols == ("DEMERGERCO", "SPLITCO")
    assert reviewed.blocked_symbols == ("OTHER", "RIGHTSCO")
