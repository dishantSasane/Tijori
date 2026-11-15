"""Covers docs/specs/CANDLE_BUILDER_AND_SCHEDULER_SPEC.md §3's session
state machine: CLOSED -> PRE_OPEN -> OPEN -> POST_CLOSE -> CLOSED.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from trading.candles.scheduler import MarketScheduler, SessionState

MKT = "in_equity"


class FixedCalendar:
    def __init__(
        self, *, trading_day: bool, pre_open: datetime, open_: datetime, close: datetime
    ) -> None:
        self.trading_day = trading_day
        self.pre_open = pre_open
        self.open_ = open_
        self.close = close

    def is_trading_day(self, market: str, now: datetime) -> bool:
        return self.trading_day

    def pre_open_at(self, market: str, now: datetime) -> datetime:
        return self.pre_open

    def session_open_at(self, market: str, now: datetime) -> datetime:
        return self.open_

    def session_close_at(self, market: str, now: datetime) -> datetime:
        return self.close


def _calendar() -> FixedCalendar:
    base = datetime(2026, 1, 5, 0, 0, tzinfo=UTC)
    return FixedCalendar(
        trading_day=True,
        pre_open=base + timedelta(hours=3, minutes=15),
        open_=base + timedelta(hours=3, minutes=45),
        close=base + timedelta(hours=10),
    )


def test_holiday_never_leaves_closed() -> None:
    calendar = FixedCalendar(
        trading_day=False,
        pre_open=datetime(2026, 1, 5, tzinfo=UTC),
        open_=datetime(2026, 1, 5, tzinfo=UTC),
        close=datetime(2026, 1, 5, tzinfo=UTC),
    )
    scheduler = MarketScheduler(MKT, calendar)
    scheduler.tick(datetime(2026, 1, 5, 12, 0, tzinfo=UTC))
    assert scheduler.state == SessionState.CLOSED


def test_full_session_cycle_fires_each_hook_exactly_once() -> None:
    calendar = _calendar()
    calls = {"pre_open": 0, "open": 0, "session_close": 0, "post_market": 0}
    scheduler = MarketScheduler(
        MKT,
        calendar,
        on_pre_open=lambda: calls.__setitem__("pre_open", calls["pre_open"] + 1),
        on_open=lambda: calls.__setitem__("open", calls["open"] + 1),
        on_session_close=lambda: calls.__setitem__("session_close", calls["session_close"] + 1),
        post_market_routine=lambda: calls.__setitem__("post_market", calls["post_market"] + 1),
    )
    base = datetime(2026, 1, 5, 0, 0, tzinfo=UTC)

    scheduler.tick(base)  # before pre-open
    assert scheduler.state == SessionState.CLOSED

    scheduler.tick(calendar.pre_open)
    assert scheduler.state == SessionState.PRE_OPEN
    assert calls["pre_open"] == 1

    scheduler.tick(calendar.open_)
    assert scheduler.state == SessionState.OPEN
    assert calls["open"] == 1

    scheduler.tick(calendar.close)
    assert (
        scheduler.state == SessionState.CLOSED
    )  # POST_CLOSE resolves to CLOSED within the same tick
    assert calls["session_close"] == 1
    assert calls["post_market"] == 1

    # No hook fires a second time on a later tick the same day.
    scheduler.tick(calendar.close + timedelta(minutes=1))
    assert calls == {"pre_open": 1, "open": 1, "session_close": 1, "post_market": 1}


def test_post_market_routine_failure_still_reaches_closed_and_is_flagged() -> None:
    calendar = _calendar()

    def boom() -> None:
        raise RuntimeError("report generation failed")

    scheduler = MarketScheduler(MKT, calendar, post_market_routine=boom)
    scheduler.tick(calendar.pre_open)
    scheduler.tick(calendar.open_)
    scheduler.tick(calendar.close)
    assert scheduler.state == SessionState.CLOSED  # never stuck in POST_CLOSE
    assert scheduler.post_market_routine_failed is True


def test_is_open_reflects_state() -> None:
    calendar = _calendar()
    scheduler = MarketScheduler(MKT, calendar)
    assert scheduler.is_open() is False
    scheduler.tick(calendar.pre_open)
    scheduler.tick(calendar.open_)
    assert scheduler.is_open() is True
    scheduler.tick(calendar.close)
    assert scheduler.is_open() is False
