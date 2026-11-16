"""Scanner backtest: replay the scanner day-by-day, measure forward outcomes.

This is *not* a strategy backtest (src/trading/backtest/). A strategy
backtest asks "if I had traded every signal, what would my P&L be." A
scanner backtest asks a narrower question: "on each day the scanner would
have shortlisted this symbol, what happened to its price over the next N
days?" There are no fills, fees, or positions here -- just a forward return
measured against the same no-look-ahead rule as everywhere else (AGENTS.md
§4.5): the decision to shortlist a symbol on day T only ever sees candles
with ts_open_utc.date() < T; the *measurement* of the outcome is the one
place this module is deliberately allowed to look at candles on or after T,
because that's what "forward outcome" means.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date, timedelta
from decimal import Decimal

from trading.core.models import Candle
from trading.scanner.models import ScannerIdea
from trading.scanner.scanner import run_scan


class ScannerOutcome:
    """Forward outcome for one shortlisted idea, ``horizon_days`` after ``as_of``."""

    def __init__(self, idea: ScannerIdea, forward_return_pct: Decimal | None) -> None:
        self.idea = idea
        self.forward_return_pct = forward_return_pct


def _candle_on_or_after(candles: Sequence[Candle], target: date) -> Candle | None:
    for candle in candles:
        if candle.ts_open_utc.date() >= target:
            return candle
    return None


def replay(
    universe: Sequence[str],
    candles_by_symbol: dict[str, Sequence[Candle]],
    session_dates: Sequence[date],
    *,
    horizon_days: int = 10,
) -> list[ScannerOutcome]:
    """Run the scanner on each date in ``session_dates`` and score forward outcomes.

    ``session_dates`` should be ascending trading days already known to have
    data (e.g. from the candle store); the scanner itself still re-derives
    its own as-of cutoff per call, so dates out of order are harmless but
    pointless.
    """
    outcomes: list[ScannerOutcome] = []
    for as_of in session_dates:
        ideas = run_scan(universe, candles_by_symbol, as_of)
        for idea in ideas:
            future = candles_by_symbol.get(idea.symbol, ())
            exit_candle = _candle_on_or_after(future, as_of + timedelta(days=horizon_days))
            forward_return_pct: Decimal | None = None
            if exit_candle is not None:
                forward_return_pct = (exit_candle.close - idea.last_close) / idea.last_close
            outcomes.append(ScannerOutcome(idea, forward_return_pct))
    return outcomes


def summarize(outcomes: Sequence[ScannerOutcome]) -> dict[str, Decimal | int]:
    """Hit rate and average forward return over outcomes that resolved."""
    resolved = [o.forward_return_pct for o in outcomes if o.forward_return_pct is not None]
    if not resolved:
        return {"count": 0, "hit_rate": Decimal(0), "avg_return_pct": Decimal(0)}
    wins = sum(1 for r in resolved if r > 0)
    return {
        "count": len(resolved),
        "hit_rate": Decimal(wins) / len(resolved),
        "avg_return_pct": sum(resolved, Decimal(0)) / len(resolved),
    }
