from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest

from trading.backtest.fills import BacktestProfile
from trading.backtest.orb import NseRegularSession, run_p1_t5_candidate, run_t5_orb
from trading.core.enums import MarketId, Timeframe
from trading.core.models import Candle

IST_OFFSET = timedelta(hours=5, minutes=30)
SESSION_DATE = date(2026, 1, 5)
SESSION_OPEN = datetime(2026, 1, 5, 3, 45, tzinfo=UTC)
SESSION_CLOSE = datetime(2026, 1, 5, 10, 0, tzinfo=UTC)


def full_session() -> list[Candle]:
    bars: list[Candle] = []
    for index in range(75):
        timestamp = SESSION_OPEN + timedelta(minutes=5 * index)
        local_time = (timestamp + IST_OFFSET).time()
        open_price, high, low, close = "100", "101", "99", "100"
        if local_time.hour == 9 and local_time.minute == 15:
            high, low = "101", "99"
        elif local_time.hour == 9 and local_time.minute == 20:
            high, low = "102", "98"
        elif local_time.hour == 9 and local_time.minute == 25:
            high, low = "101", "99"
        bars.append(
            Candle(
                market=MarketId.IN_EQUITY,
                symbol="TEST",
                timeframe=Timeframe.M5,
                ts_open_utc=timestamp,
                open=Decimal(open_price),
                high=Decimal(high),
                low=Decimal(low),
                close=Decimal(close),
                volume=Decimal("100"),
                source="test",
                ingest_ts=timestamp,
            )
        )
    return bars


def session() -> NseRegularSession:
    return NseRegularSession(
        session_date=SESSION_DATE,
        open_utc=SESSION_OPEN,
        close_utc=SESSION_CLOSE,
        calendar_version="test-calendar-v1",
    )


def test_orb_uses_closed_bar_breakout_and_next_open_fill() -> None:
    bars = full_session()
    bars[3] = bars[3].model_copy(update={"close": Decimal("102.06"), "high": Decimal("103")})
    bars[4] = bars[4].model_copy(update={"open": Decimal("103")})
    # A later bar reaches the target based on the actual, next-open fill.
    bars[5] = bars[5].model_copy(update={"high": Decimal("107.1")})

    result = run_t5_orb(
        bars,
        session=session(),
        target_multiple=Decimal("1"),
        quantity=Decimal("1"),
        profile=BacktestProfile(),
    )

    assert result.session_complete
    assert result.trade is not None
    assert result.trade.entry_bar == 4
    assert result.trade.entry_price == Decimal("103")
    assert result.trade.exit_reason == "target"
    assert result.trade.exit_price == Decimal("107")


def test_t5_candidate_id_binds_the_frozen_target_multiple() -> None:
    bars = full_session()
    bars[3] = bars[3].model_copy(update={"close": Decimal("103"), "high": Decimal("104")})
    bars[4] = bars[4].model_copy(update={"open": Decimal("103")})
    bars[5] = bars[5].model_copy(update={"high": Decimal("108")})
    result = run_p1_t5_candidate(
        "t5-orb-m15-v1",
        bars,
        session=session(),
        quantity=Decimal("1"),
        profile=BacktestProfile(),
    )
    assert result.trade is not None
    assert result.trade.target_price == Decimal("109")


def test_orb_applies_adverse_slippage_and_fees_to_entry_and_target() -> None:
    bars = full_session()
    bars[3] = bars[3].model_copy(update={"close": Decimal("103"), "high": Decimal("104")})
    bars[4] = bars[4].model_copy(update={"open": Decimal("103")})
    bars[5] = bars[5].model_copy(update={"high": Decimal("108")})
    result = run_t5_orb(
        bars,
        session=session(),
        target_multiple=Decimal("1"),
        quantity=Decimal("1"),
        profile=BacktestProfile(brokerage=Decimal("1"), slippage_bps=Decimal("5")),
    )
    assert result.trade is not None
    assert result.trade.entry_price == Decimal("103.0515")
    assert result.trade.target_price == Decimal("107.0515")
    assert result.trade.exit_price == Decimal("106.99797425")
    assert result.trade.fees == Decimal("2")


def test_orb_uses_strict_buffer_and_does_not_use_breakout_bar_high() -> None:
    bars = full_session()
    bars[3] = bars[3].model_copy(update={"close": Decimal("102.051"), "high": Decimal("110")})
    result = run_t5_orb(
        bars,
        session=session(),
        target_multiple=Decimal("1"),
        quantity=Decimal("1"),
        profile=BacktestProfile(),
    )
    assert result.trade is None
    assert result.entry_attempted is False


def test_orb_accepts_signal_closing_at_1130_but_ignores_later_signals() -> None:
    bars = full_session()
    bars[26] = bars[26].model_copy(update={"close": Decimal("103"), "high": Decimal("104")})
    bars[27] = bars[27].model_copy(update={"open": Decimal("103")})
    result = run_t5_orb(
        bars,
        session=session(),
        target_multiple=Decimal("1"),
        quantity=Decimal("1"),
        profile=BacktestProfile(),
    )
    assert result.entry_attempted
    assert result.trade is not None
    assert result.trade.entry_bar == 27

    after_cutoff = full_session()
    after_cutoff[27] = after_cutoff[27].model_copy(
        update={"close": Decimal("103"), "high": Decimal("104")}
    )
    after_cutoff[28] = after_cutoff[28].model_copy(update={"close": Decimal("104")})
    ignored = run_t5_orb(
        after_cutoff,
        session=session(),
        target_multiple=Decimal("1"),
        quantity=Decimal("1"),
        profile=BacktestProfile(),
    )
    assert not ignored.entry_attempted
    assert ignored.trade is None


def test_orb_uses_stop_first_if_stop_and_target_touch_same_bar() -> None:
    bars = full_session()
    bars[3] = bars[3].model_copy(update={"close": Decimal("103"), "high": Decimal("104")})
    bars[4] = bars[4].model_copy(update={"open": Decimal("103")})
    bars[5] = bars[5].model_copy(update={"high": Decimal("110"), "low": Decimal("97")})
    result = run_t5_orb(
        bars,
        session=session(),
        target_multiple=Decimal("1"),
        quantity=Decimal("1"),
        profile=BacktestProfile(),
    )
    assert result.trade is not None
    assert result.trade.exit_reason == "stop"
    assert result.trade.exit_price == Decimal("98")


def test_orb_squares_off_at_1515_using_1510_bar_close() -> None:
    bars = full_session()
    bars[3] = bars[3].model_copy(update={"close": Decimal("103"), "high": Decimal("104")})
    bars[4] = bars[4].model_copy(update={"open": Decimal("103")})
    bars[71] = bars[71].model_copy(update={"close": Decimal("104")})
    result = run_t5_orb(
        bars,
        session=session(),
        target_multiple=Decimal("2"),
        quantity=Decimal("1"),
        profile=BacktestProfile(),
    )
    assert result.trade is not None
    assert result.trade.exit_reason == "square_off"
    assert result.trade.exit_bar == 71
    assert result.trade.exit_price == Decimal("104")


def test_orb_marks_truncated_session_incomplete_and_excludes_trade() -> None:
    bars = full_session()
    bars[3] = bars[3].model_copy(update={"close": Decimal("103"), "high": Decimal("104")})
    bars[4] = bars[4].model_copy(update={"open": Decimal("103")})
    with pytest.raises(ValueError, match="begin with the 09:15"):
        run_t5_orb(
            bars[1:],
            session=session(),
            target_multiple=Decimal("1"),
            quantity=Decimal("1"),
            profile=BacktestProfile(),
        )

    incomplete = run_t5_orb(
        bars[:-1],
        session=session(),
        target_multiple=Decimal("1"),
        quantity=Decimal("1"),
        profile=BacktestProfile(),
    )
    assert not incomplete.session_complete
    assert incomplete.trade is None
    assert incomplete.reason == "session_incomplete_trade_not_counted"


def test_orb_rejects_non_regular_or_unversioned_calendar_session() -> None:
    bars = full_session()
    special = NseRegularSession(
        session_date=SESSION_DATE,
        open_utc=SESSION_OPEN,
        close_utc=SESSION_CLOSE - timedelta(minutes=30),
        calendar_version="test-calendar-v1",
    )
    with pytest.raises(ValueError, match="regular 09:15-15:30"):
        run_t5_orb(
            bars,
            session=special,
            target_multiple=Decimal("1"),
            quantity=Decimal("1"),
            profile=BacktestProfile(),
        )
