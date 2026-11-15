"""Validated candle storage backed by DuckDB with Parquet export."""

from __future__ import annotations

import json
from collections.abc import Iterable
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from typing import cast

import duckdb

from trading.core.enums import MarketId, Timeframe
from trading.core.models import Candle


class DuplicateCandleError(ValueError):
    """Raised when a candle key already exists with different values."""


def _is_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


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

    def _bind_adjustment_basis(
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
        return self.append_with_adjustment_bases(candles, {})

    def append_with_adjustment_bases(
        self,
        candles: Iterable[Candle],
        adjustment_bases: dict[tuple[MarketId, str, Timeframe], tuple[date, str, str]],
    ) -> int:
        """Append atomically with per-series bases; raw append cannot bypass a bound basis."""
        candle_list = list(candles)
        inserted = 0
        self._connection.execute("BEGIN TRANSACTION")
        try:
            scopes = {(candle.market, candle.symbol, candle.timeframe) for candle in candle_list}
            if set(adjustment_bases) - scopes:
                raise ValueError("adjustment basis provided for a series absent from the candles")
            for market, symbol, timeframe in scopes:
                basis = adjustment_bases.get((market, symbol, timeframe))
                if basis is None:
                    bound = self._connection.execute(
                        """SELECT 1 FROM adjustment_bases
                           WHERE market = ? AND symbol = ? AND timeframe = ?""",
                        [market.value, symbol, timeframe.value],
                    ).fetchone()
                    if bound is not None:
                        raise ValueError(
                            f"series has a bound adjustment basis: "
                            f"{market.value}/{symbol}/{timeframe.value}"
                        )
                else:
                    self._bind_adjustment_basis(
                        market,
                        symbol,
                        timeframe,
                        as_of_date=basis[0],
                        ledger_hash=basis[1],
                        basis_hash=basis[2],
                    )
            for candle in candle_list:
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
            """SELECT series.market, series.symbol, series.timeframe,
                      basis.as_of_date, basis.ledger_hash, basis.basis_hash,
                      count(*) FILTER (WHERE candles.adj_factor IS NOT NULL)
               FROM (SELECT DISTINCT market, symbol, timeframe FROM candles) AS series
               JOIN candles USING (market, symbol, timeframe)
               LEFT JOIN adjustment_bases AS basis USING (market, symbol, timeframe)
               GROUP BY series.market, series.symbol, series.timeframe,
                        basis.as_of_date, basis.ledger_hash, basis.basis_hash
               ORDER BY series.market, series.symbol, series.timeframe"""
        ).fetchall()
        entries = []
        for row in rows:
            if row[3] is None and row[6] > 0:
                raise ValueError("adjusted candle series has no corporate-action basis")
            entries.append(
                {
                    "market": row[0],
                    "symbol": row[1],
                    "timeframe": row[2],
                    "status": "bound" if row[3] is not None else "unversioned",
                    "as_of_date": row[3].isoformat() if row[3] is not None else None,
                    "ledger_hash": row[4],
                    "basis_hash": row[5],
                }
            )
        manifest = {
            "schema_version": 1,
            "parquet_sha256": self._sha256_file(parquet_path),
            "series_adjustment": entries,
        }
        manifest_path = parquet_path.with_suffix(parquet_path.suffix + ".manifest.json")
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        return manifest_path

    @staticmethod
    def _sha256_file(path: Path) -> str:
        digest = sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

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
        if not manifest_path.exists():
            raise ValueError("Parquet import requires its adjustment manifest sidecar")
        try:
            manifest = json.loads(manifest_path.read_text())
        except json.JSONDecodeError as error:
            raise ValueError("invalid Parquet adjustment manifest JSON") from error
        if (
            not isinstance(manifest, dict)
            or manifest.get("schema_version") != 1
            or not isinstance(manifest.get("series_adjustment"), list)
            or manifest.get("parquet_sha256") != self._sha256_file(path)
        ):
            raise ValueError("Parquet adjustment manifest is invalid or belongs to another file")

        manifest_scopes: set[tuple[MarketId, str, Timeframe]] = set()
        adjustment_bases: dict[tuple[MarketId, str, Timeframe], tuple[date, str, str]] = {}
        for item in manifest["series_adjustment"]:
            if not isinstance(item, dict):
                raise ValueError("invalid adjustment series record")
            try:
                market = MarketId(item["market"])
                symbol = item["symbol"]
                timeframe = Timeframe(item["timeframe"])
            except (KeyError, TypeError, ValueError) as error:
                raise ValueError("invalid adjustment series identity") from error
            if not isinstance(symbol, str):
                raise ValueError("adjustment series symbol must be a string")
            scope = (market, symbol, timeframe)
            if scope in manifest_scopes:
                raise ValueError("duplicate adjustment series record")
            manifest_scopes.add(scope)
            if item.get("status") == "bound":
                try:
                    as_of_date = date.fromisoformat(item["as_of_date"])
                    ledger_hash = item["ledger_hash"]
                    basis_hash = item["basis_hash"]
                except (KeyError, TypeError, ValueError) as error:
                    raise ValueError("invalid adjustment basis fields") from error
                if not _is_sha256(ledger_hash) or not _is_sha256(basis_hash):
                    raise ValueError("adjustment basis fields must contain valid SHA-256 hashes")
                adjustment_bases[scope] = (as_of_date, ledger_hash, basis_hash)
            elif item.get("status") != "unversioned":
                raise ValueError("unsupported adjustment series status")

        candle_scopes = {(item.market, item.symbol, item.timeframe) for item in candles}
        if manifest_scopes != candle_scopes:
            raise ValueError("adjustment manifest series do not match Parquet contents")
        return self.append_with_adjustment_bases(candles, adjustment_bases)

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
