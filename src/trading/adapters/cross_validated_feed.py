"""Cross-validate two independent candle sources (e.g. the chosen primary
live-data feed vs. Angel One/Fyers) and flag meaningful discrepancies rather
than silently trusting either one.

`detect_discrepancies` is pure and source-agnostic: it only compares candles
both feeds report for the same (market, symbol, timeframe, ts_open_utc), so
it works for any two `Candle` lists regardless of which adapters produced
them. A missing candle on one side is not itself a discrepancy (feeds can
legitimately have different coverage); only a close-price divergence beyond
`tolerance_bps` on a timestamp both feeds agree exists is flagged.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import Field

from trading.core.enums import MarketId, Timeframe
from trading.core.models import Candle, Contract

#: Default tolerance before two feeds' close prices count as disagreeing --
#: wide enough to absorb ordinary feed-timing/rounding differences, narrow
#: enough to catch a genuinely wrong candle. A real discrepancy on either
#: feed is a data-integrity problem, not a trading signal; this never feeds
#: the risk engine or sizing, only an audit flag.
DEFAULT_TOLERANCE_BPS = Decimal(50)


class FeedDiscrepancy(Contract):
    market: MarketId
    symbol: str
    timeframe: Timeframe
    ts_open_utc: datetime
    primary_close: Decimal
    secondary_close: Decimal
    divergence_bps: Decimal = Field(ge=0)


def _bps_divergence(a: Decimal, b: Decimal) -> Decimal:
    reference = max(abs(a), abs(b))
    if reference == 0:
        return Decimal(0)
    return abs(a - b) / reference * Decimal(10_000)


def detect_discrepancies(
    primary: list[Candle],
    secondary: list[Candle],
    *,
    tolerance_bps: Decimal = DEFAULT_TOLERANCE_BPS,
) -> list[FeedDiscrepancy]:
    """Compare candles both feeds report for the same identity+timestamp;
    return one `FeedDiscrepancy` per pair whose close prices diverge by more
    than `tolerance_bps`. Raises on a feed reporting the same identity twice
    at the same timestamp -- that is a feed-side bug, not a value to average.
    """
    if tolerance_bps < 0:
        raise ValueError("tolerance_bps must be non-negative")

    def _index(
        candles: list[Candle],
    ) -> dict[tuple[MarketId, str, Timeframe, datetime], Candle]:
        index: dict[tuple[MarketId, str, Timeframe, datetime], Candle] = {}
        for candle in candles:
            key = (candle.market, candle.symbol, candle.timeframe, candle.ts_open_utc)
            if key in index:
                raise ValueError(f"duplicate candle for the same identity+timestamp: {key}")
            index[key] = candle
        return index

    primary_by_key = _index(primary)
    secondary_by_key = _index(secondary)

    discrepancies: list[FeedDiscrepancy] = []
    for key, primary_candle in primary_by_key.items():
        secondary_candle = secondary_by_key.get(key)
        if secondary_candle is None:
            continue
        divergence = _bps_divergence(primary_candle.close, secondary_candle.close)
        if divergence > tolerance_bps:
            market, symbol, timeframe, ts_open_utc = key
            discrepancies.append(
                FeedDiscrepancy(
                    market=market,
                    symbol=symbol,
                    timeframe=timeframe,
                    ts_open_utc=ts_open_utc,
                    primary_close=primary_candle.close,
                    secondary_close=secondary_candle.close,
                    divergence_bps=divergence,
                )
            )
    return sorted(discrepancies, key=lambda item: str(item.ts_open_utc))
