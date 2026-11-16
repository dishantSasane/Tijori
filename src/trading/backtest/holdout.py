"""One-shot holdout access guard with durable consumption state."""

from __future__ import annotations

import fcntl
import json
import secrets
from collections.abc import Callable, Iterator
from contextlib import contextmanager
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
    dataset_manifest_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    cost_model_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    split_plan_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_snapshot_id: str = Field(min_length=1)
    universe_version: str = Field(min_length=1)
    calendar_version: str = Field(min_length=1)
    corporate_action_version: str = Field(min_length=1)
    shortlist_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    rejection_rule_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    metrics_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    family_hash: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def _validate_data_window_id(self) -> HoldoutPlan:
        if self.holdout_end <= self.holdout_start:
            raise ValueError("holdout range must have positive duration")
        expected = holdout_window_id(
            holdout_start=self.holdout_start,
            holdout_end=self.holdout_end,
            dataset_manifest_hash=self.dataset_manifest_hash,
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
    dataset_manifest_hash: str,
    source_snapshot_id: str,
    universe_version: str,
    calendar_version: str,
    corporate_action_version: str,
) -> str:
    identity = {
        "holdout_start": holdout_start.isoformat(),
        "holdout_end": holdout_end.isoformat(),
        "dataset_manifest_hash": dataset_manifest_hash,
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
    dataset_manifest_hash: str,
    cost_model_hash: str,
) -> HoldoutPlan:
    """Derive holdout identity and plan IDs from a frozen split contract."""
    data_window = holdout_window_id(
        holdout_start=split.holdout.start,
        holdout_end=split.holdout.end,
        dataset_manifest_hash=dataset_manifest_hash,
        source_snapshot_id=split.source_snapshot_id,
        universe_version=split.universe_version,
        calendar_version=split.calendar_version,
        corporate_action_version=split.corporate_action_version,
    )
    frozen_id = sha256(
        json.dumps(
            {
                "split_plan_id": split.plan_id,
                "split_plan_hash": split.content_hash,
                "shortlist_hash": shortlist_hash,
                "rejection_rule_hash": rejection_rule_hash,
                "metrics_hash": metrics_hash,
                "family_hash": family_hash,
                "dataset_manifest_hash": dataset_manifest_hash,
                "cost_model_hash": cost_model_hash,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    return HoldoutPlan(
        plan_id=frozen_id,
        data_window_id=data_window,
        holdout_start=split.holdout.start,
        holdout_end=split.holdout.end,
        dataset_manifest_hash=dataset_manifest_hash,
        cost_model_hash=cost_model_hash,
        split_plan_hash=split.content_hash,
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
    """Proof of a real `reserve_once` consumption.

    `authorization_token` is a cryptographically random secret minted inside
    `_consume` and never derivable from the plan's own (public, pre-registered)
    fields -- unlike a hash of those fields, it cannot be reconstructed by a
    caller who never actually went through consumption. `validate_authorization`
    checks it against the ledger row, so a forged or copied-but-never-issued
    token is rejected even if every other field matches a real, consumed plan.
    """

    plan_id: str
    data_window_id: str
    dataset_manifest_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    cost_model_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    split_plan_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    shortlist_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    rejection_rule_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    metrics_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    family_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    authorization_token: str = Field(min_length=1)


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
                dataset_manifest_hash VARCHAR NOT NULL,
                cost_model_hash VARCHAR NOT NULL,
                split_plan_hash VARCHAR NOT NULL,
                source_snapshot_id VARCHAR NOT NULL,
                universe_version VARCHAR NOT NULL,
                calendar_version VARCHAR NOT NULL,
                corporate_action_version VARCHAR NOT NULL,
                shortlist_hash VARCHAR NOT NULL,
                rejection_rule_hash VARCHAR NOT NULL,
                metrics_hash VARCHAR NOT NULL,
                family_hash VARCHAR NOT NULL,
                authorization_token VARCHAR NOT NULL UNIQUE,
                consumed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        self._require_authorization_token_column()
        self._lock = RLock()

    def _require_authorization_token_column(self) -> None:
        """`CREATE TABLE IF NOT EXISTS` leaves a pre-fix ledger file on its old
        schema (no `authorization_token` column) untouched -- fail with a clear
        message instead of letting `_consume`'s INSERT hit a confusing DuckDB
        binder error. There is no migration path: this project has not gone
        live, so any ledger predating this fix is development-only data; the
        fix is to delete that `.duckdb` file and re-run, not to migrate it.
        """
        columns = {
            row[0]
            for row in self._connection.execute(
                "SELECT column_name FROM duckdb_columns() WHERE table_name = 'consumed_holdouts'"
            ).fetchall()
        }
        required_columns = {
            "authorization_token",
            "dataset_manifest_hash",
            "cost_model_hash",
            "split_plan_hash",
        }
        if not required_columns.issubset(columns):
            raise RuntimeError(
                f"{self.path} predates the current holdout seal schema (holdout.py's one-shot "
                "guard forgery fix) and has no safe migration path. Delete this file and "
                "re-run -- it can only hold pre-launch development data."
            )

    def evaluate_once(self, plan: HoldoutPlan, evaluator: Callable[[], ResultT]) -> ResultT:
        """Record consumption transactionally, then evaluate once.

        If evaluation fails after consumption, the plan remains consumed: even
        a partial result may reveal holdout information.
        """
        self._consume(plan)
        return evaluator()

    def reserve_once(self, plan: HoldoutPlan) -> ConsumedHoldout:
        """Durably consume the holdout and return authorization for its rows."""
        token = self._consume(plan)
        return ConsumedHoldout(
            plan_id=plan.plan_id,
            data_window_id=plan.data_window_id,
            dataset_manifest_hash=plan.dataset_manifest_hash,
            cost_model_hash=plan.cost_model_hash,
            split_plan_hash=plan.split_plan_hash,
            shortlist_hash=plan.shortlist_hash,
            rejection_rule_hash=plan.rejection_rule_hash,
            metrics_hash=plan.metrics_hash,
            family_hash=plan.family_hash,
            authorization_token=token,
        )

    def _consume(self, plan: HoldoutPlan) -> str:
        """Insert the consumption row and return its freshly minted secret token."""
        token = secrets.token_hex(32)
        with self._lock, self._reservation_file_lock():
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
                        dataset_manifest_hash, cost_model_hash, split_plan_hash,
                        source_snapshot_id, universe_version, calendar_version,
                        corporate_action_version, shortlist_hash, rejection_rule_hash,
                        metrics_hash, family_hash, authorization_token
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        plan.plan_id,
                        plan.data_window_id,
                        plan.holdout_start,
                        plan.holdout_end,
                        plan.dataset_manifest_hash,
                        plan.cost_model_hash,
                        plan.split_plan_hash,
                        plan.source_snapshot_id,
                        plan.universe_version,
                        plan.calendar_version,
                        plan.corporate_action_version,
                        plan.shortlist_hash,
                        plan.rejection_rule_hash,
                        plan.metrics_hash,
                        plan.family_hash,
                        token,
                    ],
                )
                self._connection.execute("COMMIT")
                transaction_started = False
                return token
            except duckdb.ConstraintException as error:
                if transaction_started:
                    self._connection.execute("ROLLBACK")
                raise HoldoutAlreadyConsumedError(plan.data_window_id) from error
            except Exception:
                if transaction_started:
                    self._connection.execute("ROLLBACK")
                raise

    @contextmanager
    def _reservation_file_lock(self) -> Iterator[None]:
        """Serialize overlapping-window checks across connections and processes."""
        lock_path = self.path.with_suffix(self.path.suffix + ".reservation.lock")
        with lock_path.open("a+b") as lock_file:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)

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
        """ "Has this plan been consumed?" -- a status check for bookkeeping,
        not an access-control gate. Every argument here is public/pre-registered
        (never a secret), so this answers "did *someone* consume this plan",
        never "is *this specific caller* the one who did". Never use this
        alone to decide whether to hand over holdout rows -- that's
        `validate_authorization`'s job, which checks the caller's actual
        `authorization_token` against the ledger.
        """
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

    def validate_authorization(self, authorization: ConsumedHoldout) -> bool:
        """True only if `authorization_token` matches the ledger row this
        evaluator actually wrote during a real `reserve_once` call -- a value
        an outsider cannot guess or recompute from the plan's public fields.
        """
        if not isinstance(authorization, ConsumedHoldout):
            return False
        with self._lock:
            row = self._connection.execute(
                """
                SELECT 1 FROM consumed_holdouts
                WHERE plan_id = ? AND data_window_id = ? AND dataset_manifest_hash = ?
                  AND cost_model_hash = ? AND split_plan_hash = ? AND shortlist_hash = ?
                  AND rejection_rule_hash = ? AND metrics_hash = ? AND family_hash = ?
                  AND authorization_token = ?
                """,
                [
                    authorization.plan_id,
                    authorization.data_window_id,
                    authorization.dataset_manifest_hash,
                    authorization.cost_model_hash,
                    authorization.split_plan_hash,
                    authorization.shortlist_hash,
                    authorization.rejection_rule_hash,
                    authorization.metrics_hash,
                    authorization.family_hash,
                    authorization.authorization_token,
                ],
            ).fetchone()
            return row is not None

    def close(self) -> None:
        self._connection.close()

    def __enter__(self) -> HoldoutEvaluator:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
