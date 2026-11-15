"""Live tick -> candle builder: docs/specs/CANDLE_BUILDER_AND_SCHEDULER_SPEC.md §2.

One `CandleBuilder` per `(market, symbol, timeframe)`. Bars close on a timer
(driven by `advance(now)`), never on the arrival of the next bar's first tick
-- §2.2. A zero-tick window still emits a bar, carrying forward the previous
close -- §2.3. `open` is the price of the chronologically-earliest tick seen
in the window (by the tick's own timestamp), `close` the chronologically-
latest -- §2.4, resolving the ambiguity `TEST_SPEC_CANDLES.md` §1.3 flagged.

`CandleAggregator` (§2.5) rolls up already-closed smaller-timeframe candles
into a bigger timeframe using the identical timer-driven close rule, so there
is exactly one "close trigger" algorithm, reused at every level.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal

from trading.core.enums import MarketId, Timeframe
from trading.core.models import Candle, Tick

_TIMEFRAME_SECONDS: dict[Timeframe, int] = {
    Timeframe.M1: 60,
    Timeframe.M5: 300,
    Timeframe.M15: 900,
    Timeframe.H1: 3600,
    Timeframe.D1: 86400,
}


def floor_to_timeframe(ts_utc: datetime, timeframe: Timeframe) -> datetime:
    """Floor `ts_utc` to the nearest timeframe boundary, in UTC (AGENTS.md §6)."""
    seconds = _TIMEFRAME_SECONDS[timeframe]
    epoch = datetime(1970, 1, 1, tzinfo=ts_utc.tzinfo)
    elapsed = (ts_utc - epoch).total_seconds()
    floored = int(elapsed // seconds) * seconds
    return epoch + timedelta(seconds=floored)


class _OpenBar:
    """Accumulator for one in-progress window, fed either ticks or closed
    sub-candles (same fields either way: a timestamp, a price/OHLC, a size).
    """

    def __init__(self, bar_open: datetime) -> None:
        self.bar_open = bar_open
        self.open: Decimal | None = None
        self.high: Decimal | None = None
        self.low: Decimal | None = None
        self.close: Decimal | None = None
        self.volume: Decimal = Decimal(0)
        self._open_ts: datetime | None = None
        self._close_ts: datetime | None = None
        self.tick_count = 0

    def fold_point(
        self,
        *,
        ts: datetime,
        open_price: Decimal,
        high: Decimal,
        low: Decimal,
        close_price: Decimal,
        size: Decimal,
    ) -> None:
        self.tick_count += 1
        self.high = high if self.high is None else max(self.high, high)
        self.low = low if self.low is None else min(self.low, low)
        self.volume += size
        if self._open_ts is None or ts < self._open_ts:
            self._open_ts = ts
            self.open = open_price
        if self._close_ts is None or ts >= self._close_ts:
            self._close_ts = ts
            self.close = close_price


class CandleBuilder:
    def __init__(
        self, *, market: MarketId, symbol: str, timeframe: Timeframe, source: str = "tick_builder"
    ) -> None:
        self.market = market
        self.symbol = symbol
        self.timeframe = timeframe
        self.source = source
        self._current: _OpenBar | None = None
        self._last_closed_window: datetime | None = None
        self._last_close_price: Decimal | None = None
        self._closed: list[Candle] = []
        self.dropped_late_ticks: list[Tick] = []
        self.no_prior_close_skipped: list[datetime] = []

    def push_tick(self, tick: Tick) -> None:
        window = floor_to_timeframe(tick.ts_utc, self.timeframe)
        if self._last_closed_window is not None and window <= self._last_closed_window:
            # §2.4: a tick for a window that has already closed and been
            # emitted -- dropped, never reopens or mutates the emitted Candle.
            self.dropped_late_ticks.append(tick)
            return
        # Catch up (and zero-volume-synthesize) any windows strictly before
        # this tick's window, using the exact same timer-driven logic as a
        # scheduler-driven advance() call -- never a second, divergent
        # closing path (§2.2/§2.3).
        self.advance(window)
        if self._current is None or window != self._current.bar_open:
            self._current = _OpenBar(window)
        self._current.fold_point(
            ts=tick.ts_utc,
            open_price=tick.price,
            high=tick.price,
            low=tick.price,
            close_price=tick.price,
            size=tick.size,
        )

    def advance(self, now: datetime) -> list[Candle]:
        """Close every window whose `bar_open + timeframe <= now`, timer-driven,
        independent of tick arrival (§2.2). Synthesizes zero-volume bars for
        any skipped windows so no fixed-length lookback sees a gap (§2.3).
        """
        newly_closed: list[Candle] = []
        if self._current is None:
            # Nothing open yet -- but time may still be advancing with zero
            # ticks ever arriving; synthesize forward from the last close if
            # we have one to carry forward (if not, there is nothing to seed
            # an opening price from, so §2.3 point 1 skips rather than
            # invents a price -- recorded once per distinct window asked).
            if self._last_closed_window is None or self._last_close_price is None:
                # ponytail: records only the single most-recently-due window,
                # not every skipped window before the first tick ever arrives
                # -- add multi-window backfill if a real feed needs it.
                due_window = floor_to_timeframe(now - _delta(self.timeframe), self.timeframe)
                if (
                    due_window + _delta(self.timeframe) <= now
                    and due_window not in self.no_prior_close_skipped
                ):
                    self.no_prior_close_skipped.append(due_window)
                return newly_closed
            next_window = self._last_closed_window + _delta(self.timeframe)
            while next_window + _delta(self.timeframe) <= now:
                candle = self._synthesize_zero_volume(next_window)
                if candle is not None:  # always true here: _last_close_price is set
                    newly_closed.append(candle)
                next_window += _delta(self.timeframe)
            return newly_closed

        while self._current.bar_open + _delta(self.timeframe) <= now:
            closed = self._close_current()
            if closed is not None:
                newly_closed.append(closed)
        return newly_closed

    def _close_current(self) -> Candle | None:
        bar = self._current
        assert bar is not None
        if (
            bar.tick_count == 0
            or bar.open is None
            or bar.high is None
            or bar.low is None
            or bar.close is None
        ):
            candle = self._synthesize_zero_volume(bar.bar_open)
        else:
            candle = Candle(
                market=self.market,
                symbol=self.symbol,
                timeframe=self.timeframe,
                ts_open_utc=bar.bar_open,
                open=bar.open,
                high=bar.high,
                low=bar.low,
                close=bar.close,
                volume=bar.volume,
                source=self.source,
                ingest_ts=bar.bar_open,
            )
        self._register_closed(candle)
        self._current = _OpenBar(bar.bar_open + _delta(self.timeframe))
        return candle

    def _synthesize_zero_volume(self, bar_open: datetime) -> Candle | None:
        if self._last_close_price is None:
            # §2.3 point 1: the very first bar of a symbol's session with zero
            # ticks has no prior close to carry forward -- skip rather than
            # invent a price.
            self.no_prior_close_skipped.append(bar_open)
            return None
        price = self._last_close_price
        return Candle(
            market=self.market,
            symbol=self.symbol,
            timeframe=self.timeframe,
            ts_open_utc=bar_open,
            open=price,
            high=price,
            low=price,
            close=price,
            volume=Decimal(0),
            source=self.source,
            ingest_ts=bar_open,
        )

    def _register_closed(self, candle: Candle | None) -> None:
        if candle is None:
            return
        self._closed.append(candle)
        self._last_closed_window = candle.ts_open_utc
        self._last_close_price = candle.close

    def poll_closed_candles(self) -> list[Candle]:
        """`ADAPTERS.md` §1 shape: only ever returns already-closed bars."""
        return list(self._closed)


class CandleAggregator:
    """Rolls up closed smaller-timeframe candles into one bigger timeframe
    (§2.5). `push_candle` plays the role `push_tick` plays for `CandleBuilder`.
    """

    def __init__(
        self, *, market: MarketId, symbol: str, timeframe: Timeframe, source: str = "tick_builder"
    ) -> None:
        self.market = market
        self.symbol = symbol
        self.timeframe = timeframe
        self.source = source
        self._current: _OpenBar | None = None
        self._closed: list[Candle] = []

    def push_candle(self, sub_candle: Candle) -> None:
        window = floor_to_timeframe(sub_candle.ts_open_utc, self.timeframe)
        if self._current is None or window != self._current.bar_open:
            if self._current is not None:
                self._close_current()
            self._current = _OpenBar(window)
        self._current.fold_point(
            ts=sub_candle.ts_open_utc,
            open_price=sub_candle.open,
            high=sub_candle.high,
            low=sub_candle.low,
            close_price=sub_candle.close,
            size=sub_candle.volume,
        )

    def advance(self, now: datetime) -> list[Candle]:
        closed: list[Candle] = []
        while self._current is not None and self._current.bar_open + _delta(self.timeframe) <= now:
            candle = self._close_current()
            if candle is not None:
                closed.append(candle)
        return closed

    def _close_current(self) -> Candle | None:
        bar = self._current
        if (
            bar is None
            or bar.tick_count == 0
            or bar.open is None
            or bar.high is None
            or bar.low is None
            or bar.close is None
        ):
            self._current = None
            return None
        candle = Candle(
            market=self.market,
            symbol=self.symbol,
            timeframe=self.timeframe,
            ts_open_utc=bar.bar_open,
            open=bar.open,
            high=bar.high,
            low=bar.low,
            close=bar.close,
            volume=bar.volume,
            source=self.source,
            ingest_ts=bar.bar_open,
        )
        self._closed.append(candle)
        self._current = None
        return candle

    def poll_closed_candles(self) -> list[Candle]:
        return list(self._closed)


def candle_from_daily_bar(
    *,
    market: MarketId,
    symbol: str,
    ts_open_utc: datetime,
    open_: Decimal,
    high: Decimal,
    low: Decimal,
    close: Decimal,
    volume: Decimal,
    ingest_ts: datetime,
) -> Candle:
    """Direct construction from an end-of-day provider file, not ticks
    (TEST_SPEC_CANDLES.md §1.6). `source="nse_bhavcopy"` distinguishes it from
    `CandleBuilder`'s `"tick_builder"` for audit purposes.
    """
    return Candle(
        market=market,
        symbol=symbol,
        timeframe=Timeframe.D1,
        ts_open_utc=ts_open_utc,
        open=open_,
        high=high,
        low=low,
        close=close,
        volume=volume,
        source="nse_bhavcopy",
        ingest_ts=ingest_ts,
    )


def _delta(timeframe: Timeframe) -> timedelta:
    return timedelta(seconds=_TIMEFRAME_SECONDS[timeframe])
