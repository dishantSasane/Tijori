from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from trading.core.enums import MarketId, Timeframe
from trading.core.models import Candle
from trading.storage.us_equity_corporate_actions import (
    USCorporateAction,
    adjust_for_corporate_actions,
)


def candle(
    *,
    symbol: str = "AAPL",
    ts_open_utc: datetime = datetime(2020, 8, 28, 13, 30, tzinfo=UTC),
    close: Decimal = Decimal("500"),
    adj_factor: Decimal | None = None,
) -> Candle:
    return Candle(
        market=MarketId.US_EQUITY,
        symbol=symbol,
        timeframe=Timeframe.D1,
        ts_open_utc=ts_open_utc,
        open=close - Decimal("5"),
        high=close + Decimal("5"),
        low=close - Decimal("10"),
        close=close,
        volume=Decimal("1000"),
        source="alpaca",
        ingest_ts=datetime(2020, 8, 29, tzinfo=UTC),
        adj_factor=adj_factor,
    )


def split(
    *, revision: int = 1, announced_date: date = date(2020, 7, 30), ratio: str = "4"
) -> USCorporateAction:
    return USCorporateAction(
        action_id=f"aapl-split-{revision}",
        event_id="aapl-split-2020",
        revision=revision,
        market=MarketId.US_EQUITY,
        symbol="AAPL",
        kind="split",
        announced_date=announced_date,
        effective_date=date(2020, 8, 31),
        ratio_or_cash_amount=Decimal(ratio),
        source_ref="alpaca-corporate-actions",
    )


def test_known_answer_4_for_1_split_known_by_as_of() -> None:
    # Apple's real 4-for-1 split, effective 2020-08-31: a pre-split bar must
    # be divided by 4 in price and multiplied by 4 in volume.
    pre_split_bar = candle(
        ts_open_utc=datetime(2020, 8, 28, 13, 30, tzinfo=UTC), close=Decimal("500")
    )
    result = adjust_for_corporate_actions([pre_split_bar], [split()], as_of=date(2020, 9, 1))
    assert len(result) == 1
    assert result[0].close == Decimal("125")
    assert result[0].volume == Decimal("4000")
    assert result[0].adj_factor == Decimal("0.25")


def test_action_unknown_as_of_leaves_candle_raw() -> None:
    pre_split_bar = candle(ts_open_utc=datetime(2020, 8, 28, 13, 30, tzinfo=UTC))
    result = adjust_for_corporate_actions(
        [pre_split_bar],
        [split()],
        as_of=date(2020, 7, 29),  # before announcement
    )
    assert result[0].close == Decimal("500")
    assert result[0].adj_factor is None


def test_bar_on_or_after_effective_date_untouched() -> None:
    post_split_bar = candle(
        ts_open_utc=datetime(2020, 8, 31, 13, 30, tzinfo=UTC), close=Decimal("125")
    )
    result = adjust_for_corporate_actions([post_split_bar], [split()], as_of=date(2020, 9, 1))
    assert result[0].close == Decimal("125")
    assert result[0].adj_factor is None


def test_already_adjusted_candle_fails_closed() -> None:
    bar = candle(adj_factor=Decimal("1"))
    with pytest.raises(ValueError):
        adjust_for_corporate_actions([bar], [split()], as_of=date(2020, 9, 1))


def test_duplicate_action_id_fails_closed() -> None:
    bar = candle()
    with pytest.raises(ValueError):
        adjust_for_corporate_actions([bar], [split(), split()], as_of=date(2020, 9, 1))
