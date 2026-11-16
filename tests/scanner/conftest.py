from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from trading.core.enums import MarketId, Timeframe
from trading.core.models import Candle


def make_daily_candles(
    symbol: str,
    start: date,
    closes: list[float],
    *,
    volume: Decimal = Decimal("1000000"),
) -> list[Candle]:
    """Build a run of daily candles with ``closes`` starting at ``start``."""
    ingest = datetime.combine(start, datetime.min.time(), tzinfo=UTC)
    candles = []
    for offset, close in enumerate(closes):
        day = start + timedelta(days=offset)
        price = Decimal(str(close))
        candles.append(
            Candle(
                market=MarketId.IN_EQUITY,
                symbol=symbol,
                timeframe=Timeframe.D1,
                ts_open_utc=datetime.combine(day, datetime.min.time(), tzinfo=UTC),
                open=price,
                high=price,
                low=price,
                close=price,
                volume=volume,
                source="test",
                ingest_ts=ingest,
            )
        )
    return candles
