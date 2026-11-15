"""One-shot holdout access guard with durable consumption state."""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import date
from hashlib import sha256
from pathlib import Path
from threading import RLock
from typing import TypeVar

import duckdb
from pydantic import Field, model_validator

from trading.backtest.splits import ResearchSplitPlan
from trading.core.models import Contract

ResultT = TypeVar("ResultT")


class HoldoutPlan(Contract):
    plan_id: str = Field(min_length=1)
    data_window_id: str = Field(min_length=1)
    holdout_start: date
    holdout_end: date
    source_snapshot_id: str = Field(min_length=1)
    universe_version: str = Field(min_length=1)
    calendar_version: str = Field(min_length=1)
    corporate_action_version: str = Field(min_length=1)
    shortlist_hash: str = Field(min_length=1)
    rejection_rule_hash: str = Field(min_length=1)
    metrics_hash: str = Field(min_length=1)
    family_hash: str = Field(min_length=1)

    @model_validator(mode="after")
    def _validate_data_window_id(self) -> HoldoutPlan:
        if self.holdout_end <= self.holdout_start:
            raise ValueError("holdout range must have positive duration")
        expected = holdout_window_id(
            holdout_start=self.holdout_start,
            holdout_end=self.holdout_end,
            source_snapshot_id=self.source_snapshot_id,
            universe_version=self.universe_version,
            calendar_version=self.calendar_version,
            corporate_action_version=self.corporate_action_version,
        )
        if self.data_window_id != expected:
            raise ValueError("data_window_id does not match canonical holdout identity")
        return self


def holdout_window_id(
    *,
    holdout_start: date,
    holdout_end: date,
    source_snapshot_id: str,
    universe_version: str,
    calendar_version: str,
    corporate_action_version: str,
) -> str:
    identity = {
        "holdout_start": holdout_start.isoformat(),
        "holdout_end": holdout_end.isoformat(),
        "source_snapshot_id": source_snapshot_id,
        "universe_version": universe_version,
        "calendar_version": calendar_version,
        "corporate_action_version": corporate_action_version,
    }
    canonical = json.dumps(identity, sort_keys=True, separators=(",", ":"))
    return sha256(canonical.encode()).hexdigest()


def holdout_plan_from_split(
    split: ResearchSplitPlan,
    *,
    shortlist_hash: str,
    rejection_rule_hash: str,
    metrics_hash: str,
    family_hash: str,
) -> HoldoutPlan:
    """Derive holdout identity and plan IDs from a frozen split contract."""
    data_window = holdout_window_id(
        holdout_start=split.holdout.start,
        holdout_end=split.holdout.end,
        source_snapshot_id=split.source_snapshot_id,
        universe_version=split.universe_version,
        calendar_version=split.calendar_version,
        corporate_action_version=split.corporate_action_version,
    )
    frozen_id = sha256(f"{split.plan_id}:{split.content_hash}".encode()).hexdigest()
    return HoldoutPlan(
        plan_id=frozen_id,
        data_window_id=data_window,
        holdout_start=split.holdout.start,
        holdout_end=split.holdout.end,
        source_snapshot_id=split.source_snapshot_id,
        universe_version=split.universe_version,
        calendar_version=split.calendar_version,
        corporate_action_version=split.corporate_action_version,
        shortlist_hash=shortlist_hash,
        rejection_rule_hash=rejection_rule_hash,
        metrics_hash=metrics_hash,
        family_hash=family_hash,
    )


class HoldoutAlreadyConsumedError(RuntimeError):
    """Raised when a holdout plan has already been evaluated."""


class ConsumedHoldout(Contract):
    plan_id: str
    data_window_id: str
    shortlist_hash: str
    rejection_rule_hash: str
    metrics_hash: str
    family_hash: str
    authorization_hash: str


class HoldoutEvaluator:
    """Atomically consumes a plan before exposing its result."""

    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path.resolve()
        self._connection = duckdb.connect(str(path))
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS consumed_holdouts (
                plan_id VARCHAR PRIMARY KEY,
                data_window_id VARCHAR NOT NULL UNIQUE,
                holdout_start DATE NOT NULL,
                holdout_end DATE NOT NULL,
                source_snapshot_id VARCHAR NOT NULL,
                universe_version VARCHAR NOT NULL,
                calendar_version VARCHAR NOT NULL,
                corporate_action_version VARCHAR NOT NULL,
                shortlist_hash VARCHAR NOT NULL,
                rejection_rule_hash VARCHAR NOT NULL,
                metrics_hash VARCHAR NOT NULL,
                family_hash VARCHAR NOT NULL,
                consumed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        self._lock = RLock()

    def evaluate_once(self, plan: HoldoutPlan, evaluator: Callable[[], ResultT]) -> ResultT:
        """Record consumption transactionally, then evaluate once.

        If evaluation fails after consumption, the plan remains consumed: even
        a partial result may reveal holdout information.
        """
        self._consume(plan)
        return evaluator()

    def reserve_once(self, plan: HoldoutPlan) -> ConsumedHoldout:
        """Durably consume the holdout and return authorization for its rows."""
        self._consume(plan)
        return ConsumedHoldout(
            plan_id=plan.plan_id,
            data_window_id=plan.data_window_id,
            shortlist_hash=plan.shortlist_hash,
            rejection_rule_hash=plan.rejection_rule_hash,
            metrics_hash=plan.metrics_hash,
            family_hash=plan.family_hash,
            authorization_hash=_authorization_hash(plan),
        )

    def _consume(self, plan: HoldoutPlan) -> None:
        with self._lock:
            transaction_started = False
            try:
                self._connection.execute("BEGIN TRANSACTION")
                transaction_started = True
                overlap = self._connection.execute(
                    """
                    SELECT 1 FROM consumed_holdouts
                    WHERE holdout_start < ? AND ? < holdout_end
                    LIMIT 1
                    """,
                    [plan.holdout_end, plan.holdout_start],
                ).fetchone()
                if overlap is not None:
                    self._connection.execute("ROLLBACK")
                    transaction_started = False
                    raise HoldoutAlreadyConsumedError("overlapping holdout interval")
                self._connection.execute(
                    """
                    INSERT INTO consumed_holdouts (
                        plan_id, data_window_id, holdout_start, holdout_end,
                        source_snapshot_id, universe_version, calendar_version,
                        corporate_action_version, shortlist_hash, rejection_rule_hash,
                        metrics_hash, family_hash
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        plan.plan_id,
                        plan.data_window_id,
                        plan.holdout_start,
                        plan.holdout_end,
                        plan.source_snapshot_id,
                        plan.universe_version,
                        plan.calendar_version,
                        plan.corporate_action_version,
                        plan.shortlist_hash,
                        plan.rejection_rule_hash,
                        plan.metrics_hash,
                        plan.family_hash,
                    ],
                )
                self._connection.execute("COMMIT")
                transaction_started = False
            except duckdb.ConstraintException as error:
                if transaction_started:
                    self._connection.execute("ROLLBACK")
                raise HoldoutAlreadyConsumedError(plan.data_window_id) from error
            except Exception:
                if transaction_started:
                    self._connection.execute("ROLLBACK")
                raise

    def is_consumed(
        self,
        plan_id: str,
        data_window_id: str | None = None,
        *,
        shortlist_hash: str | None = None,
        rejection_rule_hash: str | None = None,
        metrics_hash: str | None = None,
        family_hash: str | None = None,
    ) -> bool:
        with self._lock:
            parameters: list[str] = [plan_id]
            query = "SELECT 1 FROM consumed_holdouts WHERE plan_id = ?"
            if data_window_id is not None:
                query += " AND data_window_id = ?"
                parameters.append(data_window_id)
            for column, value in (
                ("shortlist_hash", shortlist_hash),
                ("rejection_rule_hash", rejection_rule_hash),
                ("metrics_hash", metrics_hash),
                ("family_hash", family_hash),
            ):
                if value is not None:
                    query += f" AND {column} = ?"
                    parameters.append(value)
            return self._connection.execute(query, parameters).fetchone() is not None

    @staticmethod
    def validate_authorization(authorization: ConsumedHoldout) -> bool:
        if not isinstance(authorization, ConsumedHoldout):
            return False
        return authorization.authorization_hash == _authorization_hash(authorization)

    def close(self) -> None:
        self._connection.close()

    def __enter__(self) -> HoldoutEvaluator:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()


def _authorization_hash(value: HoldoutPlan | ConsumedHoldout) -> str:
    payload = {
        "plan_id": value.plan_id,
        "data_window_id": value.data_window_id,
        "shortlist_hash": value.shortlist_hash,
        "rejection_rule_hash": value.rejection_rule_hash,
        "metrics_hash": value.metrics_hash,
        "family_hash": value.family_hash,
    }
    return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
