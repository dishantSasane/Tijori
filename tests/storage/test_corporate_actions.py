from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from trading.core.enums import MarketId, Timeframe
from trading.core.models import Candle
from trading.storage.corporate_actions import ShareAdjustment, adjust_for_share_actions


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

    assert adjusted.open == Decimal(100) / Decimal(3)
    assert adjusted.volume == Decimal("3000")
    assert adjusted.adj_factor == Decimal(1) / Decimal(3)


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
    assert after_correction.adj_factor == Decimal(1) / Decimal(3)


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


def test_non_daily_candle_is_rejected() -> None:
    with pytest.raises(ValueError, match="daily candles only"):
        adjust_for_share_actions(
            [candle(timeframe=Timeframe.M5)],
            [split()],
            as_of=date(2024, 1, 3),
        )
