"""Append-only local registry for reproducible research experiments."""

from __future__ import annotations

import json
import math
from datetime import UTC, datetime
from pathlib import Path
from threading import RLock
from uuid import uuid4

import duckdb
from pydantic import Field, field_validator, model_validator

from trading.backtest.holdout import ConsumedHoldout, HoldoutEvaluator
from trading.backtest.holdout_seals import SealedShortlist
from trading.backtest.multiple_testing import P1_FAMILY_SIZE
from trading.backtest.promotion import HoldoutDecision
from trading.core.models import Contract


class ExperimentRecord(Contract):
    """Immutable identifiers and metrics for one attempted candidate run."""

    experiment_id: str = Field(default_factory=lambda: str(uuid4()))
    recorded_at_utc: datetime
    supersedes_experiment_id: str | None = None
    status: str = Field(min_length=1)
    error: str | None = None
    candidate_id: str = Field(min_length=1)
    candidate_version: str = Field(min_length=1)
    parameters_json: str
    catalog_hash: str = Field(min_length=1)
    data_snapshot_id: str = Field(min_length=1)
    universe_version: str = Field(min_length=1)
    calendar_version: str = Field(min_length=1)
    corporate_action_version: str = Field(min_length=1)
    cost_model_version: str = Field(min_length=1)
    sizing_version: str = Field(min_length=1)
    split_plan_id: str = Field(min_length=1)
    data_window_id: str = Field(min_length=1)
    partition: str = Field(min_length=1)
    code_revision: str = Field(min_length=1)
    environment_version: str = Field(min_length=1)
    parser_version: str = Field(min_length=1)
    sample_start: str = Field(min_length=1)
    sample_end: str = Field(min_length=1)
    instrument_count: int = Field(ge=0)
    time_block_count: int = Field(ge=0)
    test_family_size: int = Field(gt=0)
    metrics_json: str

    @field_validator("parameters_json")
    @classmethod
    def _require_parameters_object(cls, value: str) -> str:
        _parse_json_object(value)
        return value

    @field_validator("metrics_json")
    @classmethod
    def _require_metrics_object(cls, value: str) -> str:
        parsed = _parse_json_object(value)
        if not _finite_json(parsed):
            raise ValueError("metrics cannot contain non-finite values")
        return value

    @model_validator(mode="after")
    def _check_run_contract(self) -> ExperimentRecord:
        if self.test_family_size != P1_FAMILY_SIZE:
            raise ValueError("test_family_size differs from the frozen P1 catalog")
        if self.recorded_at_utc.utcoffset() != UTC.utcoffset(None):
            raise ValueError("recorded_at_utc must be UTC")
        if self.sample_end <= self.sample_start:
            raise ValueError("sample range must have positive duration")
        if self.status == "completed":
            metrics = _parse_json_object(self.metrics_json)
            required = {
                "trade_count",
                "net_return",
                "max_drawdown",
                "cost_drag",
                "positive_instrument_fraction",
                "uncertainty",
            }
            if not required.issubset(metrics):
                raise ValueError("completed runs must include required metric evidence")
            for key, value in metrics.items():
                if value is None and f"{key}_reason" not in metrics:
                    raise ValueError(f"null metric {key} requires a reason")
        return self


def _parse_json_object(value: str) -> dict[str, object]:
    try:
        parsed = json.loads(
            value,
            parse_constant=_reject_json_constant,
            parse_float=_finite_json_float,
        )
    except json.JSONDecodeError as error:
        raise ValueError("registry payload must be valid JSON") from error
    if not isinstance(parsed, dict):
        raise ValueError("registry payload must be a JSON object")
    return parsed


def _finite_json_float(value: str) -> float:
    parsed = float(value)
    if not math.isfinite(parsed):
        raise ValueError("JSON numbers must be finite")
    return parsed


def _finite_json(value: object) -> bool:
    if isinstance(value, float):
        return math.isfinite(value)
    if isinstance(value, dict):
        return all(_finite_json(child) for child in value.values())
    if isinstance(value, list):
        return all(_finite_json(child) for child in value)
    return True


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON number is not permitted: {value}")


class ExperimentRegistry:
    """DuckDB-backed append-only experiment log."""

    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path.resolve()
        self._connection = duckdb.connect(str(path))
        self._lock = RLock()
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS experiments (
                experiment_id VARCHAR PRIMARY KEY,
                recorded_at_utc VARCHAR NOT NULL,
                supersedes_experiment_id VARCHAR,
                status VARCHAR NOT NULL,
                error VARCHAR,
                candidate_id VARCHAR NOT NULL,
                candidate_version VARCHAR NOT NULL,
                parameters_json VARCHAR NOT NULL,
                catalog_hash VARCHAR NOT NULL,
                data_snapshot_id VARCHAR NOT NULL,
                universe_version VARCHAR NOT NULL,
                calendar_version VARCHAR NOT NULL,
                corporate_action_version VARCHAR NOT NULL,
                cost_model_version VARCHAR NOT NULL,
                sizing_version VARCHAR NOT NULL,
                split_plan_id VARCHAR NOT NULL,
                data_window_id VARCHAR NOT NULL,
                partition VARCHAR NOT NULL,
                code_revision VARCHAR NOT NULL,
                environment_version VARCHAR NOT NULL,
                parser_version VARCHAR NOT NULL,
                sample_start VARCHAR NOT NULL,
                sample_end VARCHAR NOT NULL,
                instrument_count INTEGER NOT NULL,
                time_block_count INTEGER NOT NULL,
                test_family_size INTEGER NOT NULL,
                metrics_json VARCHAR NOT NULL,
                inserted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS holdout_candidate_decisions (
                plan_id VARCHAR NOT NULL,
                candidate_id VARCHAR NOT NULL,
                candidate_version VARCHAR NOT NULL,
                experiment_id VARCHAR NOT NULL UNIQUE,
                PRIMARY KEY (plan_id, candidate_id, candidate_version)
            )
            """
        )

    def append(self, record: ExperimentRecord) -> None:
        """Insert a run once; never update/delete prior evidence."""
        if record.partition == "holdout":
            raise PermissionError(
                "holdout records require append_holdout_decision with consumed authorization"
            )
        self._append(record)

    def append_holdout_decision(
        self,
        record: ExperimentRecord,
        *,
        decision: HoldoutDecision,
        authorization: ConsumedHoldout,
        holdout_guard: HoldoutEvaluator,
        shortlist: SealedShortlist,
    ) -> ExperimentRecord:
        """Durably record one authorized P1d decision without exposing holdout rows.

        The supplied record is already the complete candidate evaluation. This
        method binds its final status and machine-readable reasons to the
        append-only registry only after the one-shot ledger confirms the caller
        holds the minted authorization token.
        """
        self._require_holdout_authorization(authorization, holdout_guard)
        if shortlist.shortlist_hash != authorization.shortlist_hash:
            raise ValueError("sealed shortlist does not match the holdout authorization")
        if record.partition != "holdout":
            raise ValueError("holdout decision records must use the holdout partition")
        if (
            record.split_plan_id != authorization.plan_id
            or record.data_window_id != authorization.data_window_id
        ):
            raise ValueError("holdout decision record does not match the authorization plan")
        if record.status != "completed":
            raise ValueError("holdout decision requires complete metric evidence")
        if not shortlist.contains(
            candidate_id=record.candidate_id,
            candidate_version=record.candidate_version,
            parameters_json=record.parameters_json,
            catalog_hash=record.catalog_hash,
        ):
            raise ValueError("holdout decision candidate is not in the sealed shortlist")
        stored = record.model_copy(
            update={
                "status": decision.status,
                "error": json.dumps(
                    {"holdout_reasons": list(decision.reasons)},
                    separators=(",", ":"),
                ),
            }
        )
        self._append_holdout(stored)
        return stored

    def _append_holdout(self, record: ExperimentRecord) -> None:
        """Append a P1d result once per plan/candidate in one DB transaction."""
        with self._lock:
            try:
                self._connection.execute("BEGIN TRANSACTION")
                self._connection.execute(
                    """
                    INSERT INTO holdout_candidate_decisions
                    (plan_id, candidate_id, candidate_version, experiment_id)
                    VALUES (?, ?, ?, ?)
                    """,
                    [
                        record.split_plan_id,
                        record.candidate_id,
                        record.candidate_version,
                        record.experiment_id,
                    ],
                )
                self._append(record)
                self._connection.execute("COMMIT")
            except Exception:
                self._connection.execute("ROLLBACK")
                raise

    def _append(self, record: ExperimentRecord) -> None:
        """Insert a validated record; callers enforce partition-specific gates."""
        payload = record.model_dump(mode="python")
        payload["recorded_at_utc"] = record.recorded_at_utc.isoformat()
        columns = list(payload)
        values = list(payload.values())
        placeholders = ", ".join("?" for _ in values)
        column_list = ", ".join(columns)
        self._connection.execute(
            f"INSERT INTO experiments ({column_list}) VALUES ({placeholders})",
            values,
        )

    def records_for_selection(self) -> list[ExperimentRecord]:
        """Return development/validation only; holdout rows remain inaccessible."""
        return self._records("partition IN ('development', 'validation')")

    def holdout_records(
        self,
        *,
        authorization: ConsumedHoldout,
        holdout_guard: HoldoutEvaluator,
    ) -> list[ExperimentRecord]:
        """Retrieve holdout rows after a consumed plan has been confirmed."""
        self._require_holdout_authorization(authorization, holdout_guard)
        return self._records(
            "partition = 'holdout'",
            split_plan_id=authorization.plan_id,
            data_window_id=authorization.data_window_id,
        )

    def _require_holdout_authorization(
        self,
        authorization: ConsumedHoldout,
        holdout_guard: HoldoutEvaluator,
    ) -> None:
        if holdout_guard.path != self.path:
            raise PermissionError("holdout authorization must use the same authoritative database")
        if not holdout_guard.validate_authorization(authorization):
            raise PermissionError("invalid holdout authorization seal")
        if not holdout_guard.is_consumed(
            authorization.plan_id,
            authorization.data_window_id,
            shortlist_hash=authorization.shortlist_hash,
            rejection_rule_hash=authorization.rejection_rule_hash,
            metrics_hash=authorization.metrics_hash,
            family_hash=authorization.family_hash,
        ):
            raise PermissionError("holdout authorization is not in the authoritative ledger")

    def _records(
        self,
        where_clause: str,
        *,
        split_plan_id: str | None = None,
        data_window_id: str | None = None,
    ) -> list[ExperimentRecord]:
        filters: list[str] = []
        parameters: list[str] = []
        if split_plan_id is not None:
            filters.append("split_plan_id = ?")
            parameters.append(split_plan_id)
        if data_window_id is not None:
            filters.append("data_window_id = ?")
            parameters.append(data_window_id)
        query = (
            "SELECT * EXCLUDE (inserted_at) FROM experiments WHERE "
            + where_clause
            + (" AND " + " AND ".join(filters) if filters else "")
            + " ORDER BY inserted_at, experiment_id"
        )
        with self._lock:
            rows = self._connection.execute(query, parameters).fetchall()
        names = [column[0] for column in self._connection.description]
        records: list[ExperimentRecord] = []
        for row in rows:
            values = dict(zip(names, row, strict=True))
            values["recorded_at_utc"] = datetime.fromisoformat(values["recorded_at_utc"])
            records.append(ExperimentRecord.model_validate(values))
        return records

    def __init_subclass__(cls) -> None:
        raise TypeError("ExperimentRegistry cannot be subclassed to broaden data access")

    def close(self) -> None:
        self._connection.close()

    def __enter__(self) -> ExperimentRegistry:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
