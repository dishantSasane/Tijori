"""Daily scanner: rank candidates that pass the universe filters.

Minimal, clearly-scoped selection logic (per the P4 task brief): the
strategy candidate library (T1/T2/T4/T6/ORB) lives on an unmerged branch
(PR #53), so this does not depend on it. Ranking here is a simple momentum
score -- "how far above its 20-day average is the close" -- good enough to
order a shortlist. Swap in a real strategy's score once one is merged; the
filter/shortlist/backtest machinery around it does not need to change.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from decimal import Decimal

from trading.core.models import Candle
from trading.indicators.moving_averages import sma
from trading.scanner.filters import (
    LOOKBACK_DAYS,
    average_turnover,
    passes_data_quality,
    passes_liquidity,
    recent_window,
)
from trading.scanner.models import ScannerIdea

#: ponytail: fixed target/reconsider bands, not a strategy. Replace with a
#: real strategy's entry/stop/target once T1/T2/T4/T6/ORB land (see PR #53).
TARGET_PCT = Decimal("0.08")
RECONSIDER_PCT = Decimal("0.05")


def scan_symbol(symbol: str, candles: Sequence[Candle], as_of: date) -> ScannerIdea | None:
    """Return a ScannerIdea for ``symbol`` on ``as_of`` if it passes every filter.

    ``candles`` may contain candles at or after ``as_of`` -- this function
    (and the filters it calls) only ever look at candles strictly before
    ``as_of``, so a caller can safely pass a symbol's full history and let
    this function enforce the as-of cutoff itself.
    """
    if not passes_data_quality(candles, as_of):
        return None
    if not passes_liquidity(candles, as_of):
        return None
    window = recent_window(candles, as_of, LOOKBACK_DAYS)
    closes = [c.close for c in window]
    sma_values = sma(closes, LOOKBACK_DAYS)
    baseline = sma_values[-1]
    if baseline is None or baseline <= 0:
        return None
    last = window[-1]
    rank_score = float(last.close) / baseline - 1.0
    if rank_score <= 0:
        return None
    return ScannerIdea(
        symbol=symbol,
        market=last.market,
        as_of=as_of,
        last_close=last.close,
        avg_turnover=average_turnover(candles, as_of),
        rank_score=rank_score,
        target_price=last.close * (1 + TARGET_PCT),
        reconsider_price=last.close * (1 - RECONSIDER_PCT),
        reasons=("liquidity_ok", "data_fresh", "above_20d_average"),
    )


def run_scan(
    universe: Sequence[str], candles_by_symbol: dict[str, Sequence[Candle]], as_of: date
) -> list[ScannerIdea]:
    """Scan ``universe``, returning ideas ranked best-first."""
    ideas = [
        idea
        for symbol in universe
        if (idea := scan_symbol(symbol, candles_by_symbol.get(symbol, ()), as_of)) is not None
    ]
    return sorted(ideas, key=lambda idea: idea.rank_score, reverse=True)
