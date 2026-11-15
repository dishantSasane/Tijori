"""Universe filters: pure predicates over candles already in hand.

Each filter takes only candles with ``ts_open_utc`` strictly before the
scan's ``as_of`` cutoff -- callers (scanner.py, backtest.py) are responsible
for not handing these functions anything from the future. That is the
system's no-look-ahead rule (AGENTS.md §4.5) applied to the scanner instead
of a strategy.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date, timedelta
from decimal import Decimal

from trading.core.models import Candle

#: ponytail: fixed thresholds, not yet config-driven. Move to config/ if the
#: owner wants to tune these without a code change.
MIN_AVG_TURNOVER_INR = Decimal("5000000")  # Rs 50 lakh/day average
LOOKBACK_DAYS = 20
MAX_STALE_DAYS = 5


def recent_window(candles: Sequence[Candle], as_of: date, lookback_days: int) -> list[Candle]:
    """Closed daily candles strictly before ``as_of``, most recent ``lookback_days``."""
    eligible = [c for c in candles if c.ts_open_utc.date() < as_of]
    return eligible[-lookback_days:] if lookback_days > 0 else eligible


def passes_data_quality(
    candles: Sequence[Candle], as_of: date, *, max_stale_days: int = MAX_STALE_DAYS
) -> bool:
    """Reject symbols with no recent candle (AGENTS.md §4.2: fail closed on stale data)."""
    window = recent_window(candles, as_of, LOOKBACK_DAYS)
    if not window:
        return False
    return (as_of - window[-1].ts_open_utc.date()) <= timedelta(days=max_stale_days)


def average_turnover(candles: Sequence[Candle], as_of: date) -> Decimal:
    """Mean of close * volume over the lookback window (0 if no data)."""
    window = recent_window(candles, as_of, LOOKBACK_DAYS)
    if not window:
        return Decimal(0)
    total = sum((c.close * c.volume for c in window), Decimal(0))
    return total / len(window)


def passes_liquidity(
    candles: Sequence[Candle], as_of: date, *, min_avg_turnover: Decimal = MIN_AVG_TURNOVER_INR
) -> bool:
    return average_turnover(candles, as_of) >= min_avg_turnover
