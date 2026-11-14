"""Validated candle storage backed by DuckDB with Parquet export."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import cast

import duckdb

from trading.core.enums import MarketId, Timeframe
from trading.core.models import Candle


class DuplicateCandleError(ValueError):
    """Raised when a candle key already exists with different values."""


class CandleStore:
    """Store closed candles in a local DuckDB database.

    The database is the queryable source of truth. `export_parquet` produces a
    portable snapshot for research and backup without changing stored data.
    """

    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self._connection = duckdb.connect(str(self.root / "candles.duckdb"))
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS candles (
                market VARCHAR NOT NULL,
                symbol VARCHAR NOT NULL,
                timeframe VARCHAR NOT NULL,
                ts_open_utc TIMESTAMP NOT NULL,
                open DECIMAL(38, 18) NOT NULL,
                high DECIMAL(38, 18) NOT NULL,
                low DECIMAL(38, 18) NOT NULL,
                close DECIMAL(38, 18) NOT NULL,
                volume DECIMAL(38, 18) NOT NULL,
                source VARCHAR NOT NULL,
                ingest_ts TIMESTAMP NOT NULL,
                adj_factor DECIMAL(38, 18),
                UNIQUE (market, symbol, timeframe, ts_open_utc)
            )
            """
        )

    def append(self, candles: Iterable[Candle]) -> int:
        """Insert validated candles, skipping exact duplicate deliveries."""
        inserted = 0
        for candle in candles:
            existing = self._connection.execute(
                """
                SELECT open, high, low, close, volume, source, ingest_ts, adj_factor
                FROM candles
                WHERE market = ? AND symbol = ? AND timeframe = ? AND ts_open_utc = ?
                """,
                [
                    candle.market.value,
                    candle.symbol,
                    candle.timeframe.value,
                    self._to_db_timestamp(candle.ts_open_utc),
                ],
            ).fetchone()
            if existing is not None:
                if not self._matches(candle, existing):
                    raise DuplicateCandleError(
                        "candle key already exists with different values: "
                        f"{candle.market.value}/{candle.symbol}/{candle.timeframe.value}/"
                        f"{candle.ts_open_utc.isoformat()}"
                    )
                continue
            self._connection.execute(
                """
                INSERT INTO candles VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    candle.market.value,
                    candle.symbol,
                    candle.timeframe.value,
                    self._to_db_timestamp(candle.ts_open_utc),
                    candle.open,
                    candle.high,
                    candle.low,
                    candle.close,
                    candle.volume,
                    candle.source,
                    self._to_db_timestamp(candle.ingest_ts),
                    candle.adj_factor,
                ],
            )
            inserted += 1
        return inserted

    def query(
        self,
        market: MarketId,
        symbol: str,
        timeframe: Timeframe,
        *,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[Candle]:
        """Return candles in ascending open-time order within an optional half-open range."""
        clauses = ["market = ?", "symbol = ?", "timeframe = ?"]
        parameters: list[object] = [market.value, symbol, timeframe.value]
        if start is not None:
            clauses.append("ts_open_utc >= ?")
            parameters.append(self._to_db_timestamp(start))
        if end is not None:
            clauses.append("ts_open_utc < ?")
            parameters.append(self._to_db_timestamp(end))
        rows = self._connection.execute(
            "SELECT * FROM candles WHERE " + " AND ".join(clauses) + " ORDER BY ts_open_utc",
            parameters,
        ).fetchall()
        return [self._from_row(row) for row in rows]

    def export_parquet(self, path: Path) -> Path:
        """Export all stored candles to a Parquet file and return its path."""
        path.parent.mkdir(parents=True, exist_ok=True)
        self._connection.execute("COPY candles TO ? (FORMAT PARQUET)", [str(path)])
        return path

    def close(self) -> None:
        self._connection.close()

    def __enter__(self) -> CandleStore:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    @staticmethod
    def _matches(candle: Candle, row: tuple[object, ...]) -> bool:
        values = (
            candle.open,
            candle.high,
            candle.low,
            candle.close,
            candle.volume,
            candle.source,
            CandleStore._to_db_timestamp(candle.ingest_ts),
            candle.adj_factor,
        )
        return values == row

    @staticmethod
    def _from_row(row: tuple[object, ...]) -> Candle:
        stored = cast(
            tuple[
                str,
                str,
                str,
                datetime,
                Decimal,
                Decimal,
                Decimal,
                Decimal,
                Decimal,
                str,
                datetime,
                Decimal | None,
            ],
            row,
        )
        return Candle(
            market=MarketId(stored[0]),
            symbol=stored[1],
            timeframe=Timeframe(stored[2]),
            ts_open_utc=stored[3].replace(tzinfo=UTC),
            open=stored[4],
            high=stored[5],
            low=stored[6],
            close=stored[7],
            volume=stored[8],
            source=stored[9],
            ingest_ts=stored[10].replace(tzinfo=UTC),
            adj_factor=stored[11],
        )

    @staticmethod
    def _to_db_timestamp(value: datetime) -> datetime:
        if value.utcoffset() != timedelta(0):
            raise ValueError("candle timestamps must be UTC")
        return value.replace(tzinfo=None)
