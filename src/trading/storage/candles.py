"""Validated candle storage backed by DuckDB with Parquet export."""

from __future__ import annotations

import json
from collections.abc import Iterable
from datetime import UTC, date, datetime, timedelta
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
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS adjustment_bases (
                market VARCHAR NOT NULL,
                symbol VARCHAR NOT NULL,
                timeframe VARCHAR NOT NULL,
                as_of_date DATE NOT NULL,
                ledger_hash VARCHAR NOT NULL,
                basis_hash VARCHAR NOT NULL,
                PRIMARY KEY (market, symbol, timeframe)
            )
            """
        )

    def bind_adjustment_basis(
        self,
        market: MarketId,
        symbol: str,
        timeframe: Timeframe,
        *,
        as_of_date: date,
        ledger_hash: str,
        basis_hash: str,
    ) -> None:
        """Bind one candle series to a single immutable action-adjustment basis."""
        row = self._connection.execute(
            """SELECT as_of_date, ledger_hash, basis_hash FROM adjustment_bases
               WHERE market = ? AND symbol = ? AND timeframe = ?""",
            [market.value, symbol, timeframe.value],
        ).fetchone()
        expected = (as_of_date, ledger_hash, basis_hash)
        if row is not None:
            if row != expected:
                raise ValueError(
                    f"adjustment basis differs for {market.value}/{symbol}/{timeframe.value}; "
                    "rebuild into a clean versioned store"
                )
            return
        count_row = self._connection.execute(
            """SELECT count(*) FROM candles
               WHERE market = ? AND symbol = ? AND timeframe = ?""",
            [market.value, symbol, timeframe.value],
        ).fetchone()
        if count_row is None:
            raise RuntimeError("failed to check existing candle series")
        existing_count = count_row[0]
        if existing_count:
            raise ValueError(
                f"existing series lacks an adjustment basis: "
                f"{market.value}/{symbol}/{timeframe.value}; rebuild into a clean store"
            )
        self._connection.execute(
            """INSERT INTO adjustment_bases VALUES (?, ?, ?, ?, ?, ?)""",
            [market.value, symbol, timeframe.value, as_of_date, ledger_hash, basis_hash],
        )

    def append(self, candles: Iterable[Candle]) -> int:
        """Insert validated candles, skipping exact duplicate deliveries."""
        inserted = 0
        self._connection.execute("BEGIN TRANSACTION")
        try:
            for candle in candles:
                existing = self._connection.execute(
                    """
                    SELECT open, high, low, close, volume, source, adj_factor
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
        except Exception:
            self._connection.execute("ROLLBACK")
            raise
        self._connection.execute("COMMIT")
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
        self.write_adjustment_manifest(path)
        return path

    def write_adjustment_manifest(self, parquet_path: Path) -> Path:
        """Write the action basis for every series beside its Parquet snapshot."""
        rows = self._connection.execute(
            """SELECT market, symbol, timeframe, as_of_date, ledger_hash, basis_hash
               FROM adjustment_bases ORDER BY market, symbol, timeframe"""
        ).fetchall()
        manifest = {
            "schema_version": 1,
            "adjustment_bases": [
                {
                    "market": row[0],
                    "symbol": row[1],
                    "timeframe": row[2],
                    "as_of_date": row[3].isoformat(),
                    "ledger_hash": row[4],
                    "basis_hash": row[5],
                }
                for row in rows
            ],
        }
        manifest_path = parquet_path.with_suffix(parquet_path.suffix + ".manifest.json")
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        return manifest_path

    def load_parquet(self, path: Path) -> int:
        """Load a Parquet snapshot through the normal candle validations."""
        rows = self._connection.execute(
            """
            SELECT market, symbol, timeframe, ts_open_utc, open, high, low, close,
                   volume, source, ingest_ts, adj_factor
            FROM read_parquet(?)
            ORDER BY ts_open_utc
            """,
            [str(path)],
        ).fetchall()
        candles = [self._from_row(row) for row in rows]
        manifest_path = path.with_suffix(path.suffix + ".manifest.json")
        if manifest_path.exists():
            try:
                manifest = json.loads(manifest_path.read_text())
            except json.JSONDecodeError as error:
                raise ValueError("invalid Parquet adjustment manifest JSON") from error
            if (
                not isinstance(manifest, dict)
                or manifest.get("schema_version") != 1
                or not isinstance(manifest.get("adjustment_bases"), list)
            ):
                raise ValueError("unsupported Parquet adjustment manifest")
            manifest_scopes: set[tuple[MarketId, str, Timeframe]] = set()
            for item in manifest["adjustment_bases"]:
                if not isinstance(item, dict):
                    raise ValueError("invalid adjustment basis record")
                try:
                    market = MarketId(item["market"])
                    symbol = item["symbol"]
                    timeframe = Timeframe(item["timeframe"])
                    as_of_date = date.fromisoformat(item["as_of_date"])
                    ledger_hash = item["ledger_hash"]
                    basis_hash = item["basis_hash"]
                except (KeyError, TypeError, ValueError) as error:
                    raise ValueError("invalid adjustment basis fields") from error
                if (
                    not isinstance(symbol, str)
                    or not isinstance(ledger_hash, str)
                    or not isinstance(basis_hash, str)
                    or len(ledger_hash) != 64
                    or len(basis_hash) != 64
                    or any(character not in "0123456789abcdef" for character in ledger_hash)
                    or any(character not in "0123456789abcdef" for character in basis_hash)
                ):
                    raise ValueError("adjustment basis fields must contain valid SHA-256 hashes")
                self.bind_adjustment_basis(
                    market,
                    symbol,
                    timeframe,
                    as_of_date=as_of_date,
                    ledger_hash=ledger_hash,
                    basis_hash=basis_hash,
                )
                manifest_scopes.add((market, symbol, timeframe))
            for candle in candles:
                scope = (candle.market, candle.symbol, candle.timeframe)
                if candle.adj_factor is not None and scope not in manifest_scopes:
                    raise ValueError("adjusted Parquet candle has no adjustment basis record")
        elif any(candle.adj_factor is not None for candle in candles):
            raise ValueError("adjusted Parquet candles require an adjustment manifest")
        return self.append(candles)

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
