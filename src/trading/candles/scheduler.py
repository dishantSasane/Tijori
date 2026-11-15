"""Per-market session state machine: docs/specs/CANDLE_BUILDER_AND_SCHEDULER_SPEC.md §3.

`CLOSED -> PRE_OPEN -> OPEN -> POST_CLOSE -> CLOSED`, driven by `tick(now)`.
Session open/close/holiday truth comes from an injected `SessionTimes`
Protocol (a real `exchange_calendars`-backed implementation is a follow-up,
not this spec's job -- it only needs the shape).
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from enum import StrEnum
from typing import Protocol


class SessionState(StrEnum):
    CLOSED = "closed"
    PRE_OPEN = "pre_open"
    OPEN = "open"
    POST_CLOSE = "post_close"


class SessionTimes(Protocol):
    def is_trading_day(self, market: str, now: datetime) -> bool: ...
    def pre_open_at(self, market: str, now: datetime) -> datetime: ...
    def session_open_at(self, market: str, now: datetime) -> datetime: ...
    def session_close_at(self, market: str, now: datetime) -> datetime: ...


class MarketScheduler:
    def __init__(
        self,
        market: str,
        calendar: SessionTimes,
        *,
        on_pre_open: Callable[[], None] | None = None,
        on_open: Callable[[], None] | None = None,
        on_session_close: Callable[[], None] | None = None,
        post_market_routine: Callable[[], None] | None = None,
    ) -> None:
        self.market = market
        self._calendar = calendar
        self._on_pre_open = on_pre_open
        self._on_open = on_open
        self._on_session_close = on_session_close
        self._post_market_routine = post_market_routine
        self.state = SessionState.CLOSED
        self.post_market_routine_failed = False
        self._completed_pre_open_at: datetime | None = None

    def tick(self, now: datetime) -> SessionState:
        """Advance the state machine as far as `now` allows, firing each
        transition's hook exactly once. A holiday never transitions past
        CLOSED (§3.2) -- `PRE_OPEN`/`OPEN` simply never fire that day.
        Once a full cycle completes for a given session (identified by its
        `pre_open_at` instant), re-ticking later the same day must not
        re-fire the hooks -- only a new session (a different `pre_open_at`,
        i.e. the next trading day) can start the cycle again.
        """
        if not self._calendar.is_trading_day(self.market, now):
            self.state = SessionState.CLOSED
            return self.state

        pre_open_at = self._calendar.pre_open_at(self.market, now)
        if self.state is SessionState.CLOSED and pre_open_at == self._completed_pre_open_at:
            return self.state  # already ran today's session; wait for the next one

        if self.state is SessionState.CLOSED:
            if now >= pre_open_at:
                self.state = SessionState.PRE_OPEN
                if self._on_pre_open:
                    self._on_pre_open()

        if self.state is SessionState.PRE_OPEN:
            if now >= self._calendar.session_open_at(self.market, now):
                self.state = SessionState.OPEN
                if self._on_open:
                    self._on_open()

        if self.state is SessionState.OPEN:
            if now >= self._calendar.session_close_at(self.market, now):
                if self._on_session_close:
                    self._on_session_close()
                self.state = SessionState.POST_CLOSE

        if self.state is SessionState.POST_CLOSE:
            try:
                if self._post_market_routine:
                    self._post_market_routine()
                self.post_market_routine_failed = False
            except Exception:  # noqa: BLE001 -- §3.4: never block CLOSED on a failure
                self.post_market_routine_failed = True
            self.state = SessionState.CLOSED
            self._completed_pre_open_at = pre_open_at

        return self.state

    def is_open(self) -> bool:
        return self.state is SessionState.OPEN
