"""Deterministic single-session T5 opening-range-breakout replay."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from trading.backtest.fills import BacktestProfile, Position, fill_at_next_open
from trading.core.enums import MarketId, Timeframe
from trading.core.models import Candle
from trading.strategies.p1_catalog import get_p1_candidate

_IST = ZoneInfo("Asia/Kolkata")
_BAR_DURATION = timedelta(minutes=5)
_EXPECTED_BARS = 75
_OPEN_LOCAL = time(9, 15)
_CUTOFF_LOCAL = time(11, 30)
_SQUARE_OFF_LOCAL = time(15, 15)
_BUFFER = Decimal("0.0005")
_ALLOWED_TARGET_MULTIPLES = {Decimal("1.0"), Decimal("1.5"), Decimal("2.0")}


@dataclass(frozen=True)
class NseRegularSession:
    """One regular NSE session supplied by a versioned, verified calendar."""

    session_date: date
    open_utc: datetime
    close_utc: datetime
    calendar_version: str


@dataclass(frozen=True)
class OrbTrade:
    entry_bar: int
    exit_bar: int
    entry_price: Decimal
    exit_price: Decimal
    quantity: Decimal
    stop_price: Decimal
    target_price: Decimal
    fees: Decimal
    pnl: Decimal
    exit_reason: str


@dataclass(frozen=True)
class OrbResult:
    session_complete: bool
    entry_attempted: bool
    trade: OrbTrade | None
    open_position: bool
    reason: str | None = None


def _local_time(timestamp: datetime) -> time:
    return timestamp.astimezone(_IST).time().replace(tzinfo=None)


def _validate_session(candles: list[Candle], session: NseRegularSession) -> None:
    if not session.calendar_version.strip():
        raise ValueError("calendar_version is required")
    if session.open_utc.tzinfo is None or session.close_utc.tzinfo is None:
        raise ValueError("calendar session timestamps must be timezone-aware")
    if session.open_utc.utcoffset() != timedelta(0) or session.close_utc.utcoffset() != timedelta(
        0
    ):
        raise ValueError("calendar session timestamps must be UTC")
    if (
        session.open_utc.astimezone(_IST).date() != session.session_date
        or session.close_utc.astimezone(_IST).date() != session.session_date
        or _local_time(session.open_utc) != _OPEN_LOCAL
        or _local_time(session.close_utc) != time(15, 30)
    ):
        raise ValueError("T5 supports only regular 09:15-15:30 NSE sessions")
    if not candles:
        raise ValueError("a complete regular session requires candle data")
    first = candles[0]
    if first.market is not MarketId.IN_EQUITY or first.timeframe is not Timeframe.M5:
        raise ValueError("T5 requires NSE equity 5-minute candles")
    identity = (first.market, first.symbol, first.timeframe)
    previous: datetime | None = None
    for candle in candles:
        if (candle.market, candle.symbol, candle.timeframe) != identity:
            raise ValueError("T5 input must contain one symbol and timeframe")
        if candle.ts_open_utc.tzinfo is None or candle.ts_open_utc.utcoffset() != timedelta(0):
            raise ValueError("candle timestamps must be UTC")
        if candle.ts_open_utc.astimezone(_IST).date() != session.session_date:
            raise ValueError("candle lies outside the supplied calendar session")
        if any(price <= 0 for price in (candle.open, candle.high, candle.low, candle.close)):
            raise ValueError("OHLC prices must be positive")
        if previous is not None and candle.ts_open_utc != previous + _BAR_DURATION:
            raise ValueError("T5 session bars must be unique, ordered, and gap-free")
        previous = candle.ts_open_utc
    if candles[0].ts_open_utc != session.open_utc:
        raise ValueError("T5 session must begin with the 09:15 opening bar")
    expected_opens = [session.open_utc + _BAR_DURATION * index for index in range(len(candles))]
    if [candle.ts_open_utc for candle in candles] != expected_opens:
        raise ValueError("T5 session bars must be unique, ordered, and gap-free")
    if len(candles) > _EXPECTED_BARS:
        raise ValueError("T5 session contains bars beyond the regular session")


def _sell_fill(price: Decimal, profile: BacktestProfile) -> Decimal:
    return price * (Decimal("1") - profile.slippage_bps / Decimal("10000"))


def run_t5_orb(
    candles: list[Candle],
    *,
    session: NseRegularSession,
    target_multiple: Decimal,
    quantity: Decimal,
    profile: BacktestProfile,
) -> OrbResult:
    """Replay one frozen T5 variant on one regular session.

    A complete valid session has 75 contiguous five-minute bars. A truncated
    contiguous prefix remains visible as incomplete; any gap or malformed
    calendar/session input fails closed. A trade from a truncated session is
    never returned as a completed, scorecard-eligible result.
    """
    if target_multiple not in _ALLOWED_TARGET_MULTIPLES:
        raise ValueError("target_multiple must be one of the three frozen P1 variants")
    if quantity <= 0:
        raise ValueError("quantity must be positive")
    _validate_session(candles, session)
    session_complete = len(candles) == _EXPECTED_BARS
    if len(candles) < 3:
        return OrbResult(False, False, None, False, "incomplete_opening_range")

    opening_bars = candles[:3]
    range_high = max(bar.high for bar in opening_bars)
    range_low = min(bar.low for bar in opening_bars)
    range_size = range_high - range_low
    if range_size <= 0:
        return OrbResult(session_complete, False, None, False, "invalid_opening_range")

    signal_index: int | None = None
    threshold = range_high * (Decimal("1") + _BUFFER)
    for index in range(3, min(len(candles), 75)):
        bar = candles[index]
        close_time = _local_time(bar.ts_open_utc + _BAR_DURATION)
        if close_time > _CUTOFF_LOCAL:
            break
        if bar.close > threshold:
            signal_index = index
            break
    if signal_index is None:
        return OrbResult(session_complete, False, None, False, None)

    entry_index = signal_index + 1
    square_off_index = 71  # the 15:10 bar closes at the 15:15 square-off time
    if (
        entry_index >= len(candles)
        or _local_time(candles[entry_index].ts_open_utc) >= _SQUARE_OFF_LOCAL
    ):
        return OrbResult(session_complete, True, None, False, "entry_expired")

    entry = fill_at_next_open(
        candles[entry_index].open,
        side="buy",
        quantity=quantity,
        profile=profile,
    )
    if entry.price <= range_low:
        return OrbResult(session_complete, True, None, False, "entry_at_or_below_stop")
    stop = range_low
    target = entry.price + target_multiple * range_size
    position = Position(quantity=quantity, entry_price=entry.price, stop=stop)

    last_exit_index = min(square_off_index, len(candles) - 1)
    for index in range(entry_index, last_exit_index + 1):
        bar = candles[index]
        stop_touched = bar.low <= stop
        target_touched = bar.high >= target
        if stop_touched:
            raw_exit = bar.open if bar.open < stop else stop
            exit_price = _sell_fill(raw_exit, profile)
            reason = "stop"
        elif target_touched:
            raw_exit = bar.open if bar.open >= target else target
            exit_price = _sell_fill(raw_exit, profile)
            reason = "target"
        else:
            continue
        fees = entry.fees + profile.exit_fee
        trade = OrbTrade(
            entry_bar=entry_index,
            exit_bar=index,
            entry_price=position.entry_price,
            exit_price=exit_price,
            quantity=quantity,
            stop_price=stop,
            target_price=target,
            fees=fees,
            pnl=(exit_price - entry.price) * quantity - fees,
            exit_reason=reason,
        )
        if not session_complete:
            return OrbResult(False, True, None, False, "session_incomplete_trade_not_counted")
        return OrbResult(True, True, trade, False, None)

    if len(candles) > square_off_index:
        bar = candles[square_off_index]
        exit_price = _sell_fill(bar.close, profile)
        fees = entry.fees + profile.exit_fee
        trade = OrbTrade(
            entry_bar=entry_index,
            exit_bar=square_off_index,
            entry_price=entry.price,
            exit_price=exit_price,
            quantity=quantity,
            stop_price=stop,
            target_price=target,
            fees=fees,
            pnl=(exit_price - entry.price) * quantity - fees,
            exit_reason="square_off",
        )
        if not session_complete:
            return OrbResult(False, True, None, False, "session_incomplete_trade_not_counted")
        return OrbResult(True, True, trade, False, None)
    return OrbResult(False, True, None, True, "open_at_incomplete_session_end")


def run_p1_t5_candidate(
    candidate_id: str,
    candles: list[Candle],
    *,
    session: NseRegularSession,
    quantity: Decimal,
    profile: BacktestProfile,
) -> OrbResult:
    """Run a T5 candidate by its immutable catalog ID and frozen target."""
    candidate = get_p1_candidate(candidate_id)
    if candidate.family != "T5" or candidate.timeframe != Timeframe.M5.value:
        raise ValueError("candidate ID is not a frozen T5 5-minute variant")
    target_multiple = Decimal(str(dict(candidate.parameters)["target_multiple"]))
    return run_t5_orb(
        candles,
        session=session,
        target_multiple=target_multiple,
        quantity=quantity,
        profile=profile,
    )
