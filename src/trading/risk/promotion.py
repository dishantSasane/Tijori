"""Promotion gate: docs/RISK_SPEC.md §2A. Moves a strategy from
approval-required to auto-eligible only after (1) it passed the P1d holdout
evaluation with its pre-written rejection rule not triggered, and (2) it ran
a declared minimum period in paper/approval mode with live results matching
backtest expectations within a stated tolerance. Both conditions are checked
and recorded before the `promoted` flag is set; the flag change itself is a
human action, logged in the audit trail (I10 -- mode/eligibility can only be
escalated by an explicit human action, never inferred from a passing check).

`PromotionConfig`'s numbers are owner-confirmed per strategy, not hardcoded
in this module -- same "proposed defaults, owner confirms" discipline as
every other number in `config/risk.yaml` (AGENTS.md §4 rule 9: this module
never weakens a check to make a strategy pass).
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from trading.risk.audit import AuditLog


@dataclass(frozen=True)
class PromotionConfig:
    """Owner-confirmed thresholds for one strategy's promotion gate. Never a
    module-level constant -- different strategies may reasonably need
    different minimum periods/tolerances, and the owner decides, not this
    code (RISK_SPEC.md §2A's thresholds are "proposed defaults ... the owner
    confirms them").
    """

    min_paper_period_days: int
    tolerance_pct: Decimal  # e.g. Decimal(20) means live must be within +-20% of backtest

    def __post_init__(self) -> None:
        if self.min_paper_period_days < 0:
            raise ValueError("min_paper_period_days must be non-negative")
        if self.tolerance_pct < 0:
            raise ValueError("tolerance_pct must be non-negative")


@dataclass(frozen=True)
class HoldoutResult:
    """BUILD_ORDER.md P1d's one-shot evaluation outcome for this strategy."""

    passed: bool
    rejection_rule_triggered: bool

    def __post_init__(self) -> None:
        if self.passed and self.rejection_rule_triggered:
            raise ValueError(
                "a holdout result cannot both pass and have triggered its rejection rule"
            )


@dataclass(frozen=True)
class PaperTrackRecord:
    """The strategy's live paper/approval-mode run so far."""

    days_running: int
    live_result_pct: Decimal

    def __post_init__(self) -> None:
        if self.days_running < 0:
            raise ValueError("days_running must be non-negative")


@dataclass(frozen=True)
class PromotionEligibility:
    eligible: bool
    reasons: tuple[str, ...]  # non-empty always -- "why" is never left implicit


def evaluate(
    holdout: HoldoutResult,
    track_record: PaperTrackRecord,
    backtest_expected_pct: Decimal,
    config: PromotionConfig,
) -> PromotionEligibility:
    """Pure check -- no side effects, no persistence, no audit write. The
    flag change itself (`promote()` below) is the human action; this
    function only answers "would this be allowed."
    """
    reasons: list[str] = []

    if not holdout.passed or holdout.rejection_rule_triggered:
        reasons.append("holdout_not_passed_or_rejection_rule_triggered")

    if track_record.days_running < config.min_paper_period_days:
        reasons.append(
            f"paper_period_too_short: {track_record.days_running} < {config.min_paper_period_days}"
        )

    if backtest_expected_pct == 0:
        # Relative tolerance is undefined against a zero expectation -- this
        # is a config/strategy-spec problem to fix, not something this gate
        # should silently paper over with an absolute fallback no one asked
        # for (AGENTS.md §4 rule 9).
        reasons.append("backtest_expected_pct_is_zero_relative_tolerance_undefined")
    else:
        drift_pct = (
            abs(track_record.live_result_pct - backtest_expected_pct)
            / abs(backtest_expected_pct)
            * Decimal(100)
        )
        if drift_pct > config.tolerance_pct:
            reasons.append(
                f"live_result_outside_tolerance: drift={drift_pct}% "
                f"> tolerance={config.tolerance_pct}%"
            )

    return PromotionEligibility(eligible=len(reasons) == 0, reasons=tuple(reasons))


class PromotionNotEligibleError(RuntimeError):
    """Raised by `promote()` if called against an ineligible evaluation --
    the flag can never be set by bypassing `evaluate()`'s own conditions.
    """


class PromotionStore:
    """Persists the `promoted` flag per strategy. Backed by the shared
    SQLite state_db (`strategy_promotions` table) so it survives restart
    the same way kill-switch/mode state does.
    """

    def __init__(self, conn: sqlite3.Connection, audit: AuditLog) -> None:
        self._conn = conn
        self._audit = audit

    def is_promoted(self, strategy_id: str) -> bool:
        row = self._conn.execute(
            "SELECT promoted FROM strategy_promotions WHERE strategy_id = ?", (strategy_id,)
        ).fetchone()
        return bool(row and row[0])

    def promote(
        self,
        strategy_id: str,
        eligibility: PromotionEligibility,
        *,
        actor: str,
        now: datetime,
    ) -> None:
        """The flag-flip action. Requires an already-computed, eligible
        `PromotionEligibility` and an explicit human `actor` -- there is no
        code path that sets `promoted=True` as a side effect of `evaluate()`
        returning True; a human (or a human-authorized process) must still
        call this.
        """
        if not eligibility.eligible:
            raise PromotionNotEligibleError(
                f"cannot promote {strategy_id}: not eligible ({', '.join(eligibility.reasons)})"
            )
        self._conn.execute(
            "INSERT INTO strategy_promotions (strategy_id, promoted, promoted_by, promoted_ts) "
            "VALUES (?, 1, ?, ?) "
            "ON CONFLICT(strategy_id) DO UPDATE SET promoted=1, promoted_by=excluded.promoted_by, "
            "promoted_ts=excluded.promoted_ts",
            (strategy_id, actor, now.isoformat()),
        )
        self._conn.commit()
        self._audit.write(
            ts_utc=now,
            event_type="strategy_promoted",
            actor=actor,
            payload={"strategy_id": strategy_id},
        )

    def demote(self, strategy_id: str, *, actor: str, reason: str, now: datetime) -> None:
        """Demotion is not gated the way promotion is -- an immediate safety
        downgrade (e.g. live drifting outside tolerance) should never be
        blocked by a check designed to gate the *opposite* direction (I10
        is about escalation only; de-escalation is always allowed).
        """
        self._conn.execute(
            "UPDATE strategy_promotions SET promoted = 0, promoted_by = ?, promoted_ts = ? "
            "WHERE strategy_id = ?",
            (actor, now.isoformat(), strategy_id),
        )
        self._conn.commit()
        self._audit.write(
            ts_utc=now,
            event_type="strategy_demoted",
            actor=actor,
            payload={"strategy_id": strategy_id, "reason": reason},
        )
