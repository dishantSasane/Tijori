"""Covers docs/RISK_SPEC.md §2A's promotion gate."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from trading.risk.audit import AuditLog
from trading.risk.promotion import (
    HoldoutResult,
    PaperTrackRecord,
    PromotionConfig,
    PromotionNotEligibleError,
    PromotionStore,
    evaluate,
)
from trading.storage.state_db import connect

T0 = datetime(2026, 1, 1, tzinfo=UTC)


def _config(min_days: int = 30, tolerance_pct: str = "20") -> PromotionConfig:
    return PromotionConfig(min_paper_period_days=min_days, tolerance_pct=Decimal(tolerance_pct))


def test_eligible_when_holdout_passed_period_met_and_within_tolerance() -> None:
    holdout = HoldoutResult(passed=True, rejection_rule_triggered=False)
    track = PaperTrackRecord(days_running=45, live_result_pct=Decimal(11))
    result = evaluate(holdout, track, backtest_expected_pct=Decimal(10), config=_config())
    assert result.eligible is True
    assert result.reasons == ()


def test_not_eligible_when_holdout_not_passed() -> None:
    holdout = HoldoutResult(passed=False, rejection_rule_triggered=False)
    track = PaperTrackRecord(days_running=45, live_result_pct=Decimal(11))
    result = evaluate(holdout, track, backtest_expected_pct=Decimal(10), config=_config())
    assert result.eligible is False
    assert "holdout_not_passed_or_rejection_rule_triggered" in result.reasons


def test_not_eligible_when_paper_period_too_short() -> None:
    holdout = HoldoutResult(passed=True, rejection_rule_triggered=False)
    track = PaperTrackRecord(days_running=10, live_result_pct=Decimal(10))
    result = evaluate(
        holdout, track, backtest_expected_pct=Decimal(10), config=_config(min_days=30)
    )
    assert result.eligible is False
    assert any("paper_period_too_short" in r for r in result.reasons)


def test_not_eligible_when_live_result_outside_tolerance() -> None:
    holdout = HoldoutResult(passed=True, rejection_rule_triggered=False)
    # backtest expects 10%, live delivered 3% -- 70% relative drift, way outside a 20% tolerance.
    track = PaperTrackRecord(days_running=45, live_result_pct=Decimal(3))
    result = evaluate(
        holdout, track, backtest_expected_pct=Decimal(10), config=_config(tolerance_pct="20")
    )
    assert result.eligible is False
    assert any("live_result_outside_tolerance" in r for r in result.reasons)


def test_tolerance_is_configurable_not_hardcoded() -> None:
    holdout = HoldoutResult(passed=True, rejection_rule_triggered=False)
    track = PaperTrackRecord(days_running=45, live_result_pct=Decimal(3))
    # The exact same drift that fails a 20% tolerance passes a looser 80% one
    # -- the number comes from config, not a constant in this module.
    loose = evaluate(
        holdout, track, backtest_expected_pct=Decimal(10), config=_config(tolerance_pct="80")
    )
    assert loose.eligible is True


def test_min_period_is_configurable_not_hardcoded() -> None:
    holdout = HoldoutResult(passed=True, rejection_rule_triggered=False)
    track = PaperTrackRecord(days_running=10, live_result_pct=Decimal(10))
    short_requirement = evaluate(
        holdout, track, backtest_expected_pct=Decimal(10), config=_config(min_days=5)
    )
    assert short_requirement.eligible is True


def test_zero_backtest_expectation_is_flagged_not_silently_passed() -> None:
    holdout = HoldoutResult(passed=True, rejection_rule_triggered=False)
    track = PaperTrackRecord(days_running=45, live_result_pct=Decimal(0))
    result = evaluate(holdout, track, backtest_expected_pct=Decimal(0), config=_config())
    assert result.eligible is False
    assert any("zero" in r for r in result.reasons)


def test_holdout_result_cannot_pass_and_trigger_rejection_rule() -> None:
    with pytest.raises(ValueError):
        HoldoutResult(passed=True, rejection_rule_triggered=True)


def test_promote_requires_eligible_result() -> None:
    conn = connect(":memory:")
    audit = AuditLog(conn)
    store = PromotionStore(conn, audit)
    holdout = HoldoutResult(passed=False, rejection_rule_triggered=False)
    track = PaperTrackRecord(days_running=45, live_result_pct=Decimal(10))
    ineligible = evaluate(holdout, track, backtest_expected_pct=Decimal(10), config=_config())
    with pytest.raises(PromotionNotEligibleError):
        store.promote("t1", ineligible, actor="owner", now=T0)
    assert store.is_promoted("t1") is False


def test_promote_sets_flag_and_writes_human_actor_audit_event() -> None:
    conn = connect(":memory:")
    audit = AuditLog(conn)
    store = PromotionStore(conn, audit)
    holdout = HoldoutResult(passed=True, rejection_rule_triggered=False)
    track = PaperTrackRecord(days_running=45, live_result_pct=Decimal(10))
    eligible = evaluate(holdout, track, backtest_expected_pct=Decimal(10), config=_config())

    store.promote("t1", eligible, actor="owner", now=T0)
    assert store.is_promoted("t1") is True
    events = audit.events(event_type="strategy_promoted")
    assert len(events) == 1
    assert events[0]["actor"] == "owner"


def test_demote_is_never_gated_by_eligibility() -> None:
    conn = connect(":memory:")
    audit = AuditLog(conn)
    store = PromotionStore(conn, audit)
    holdout = HoldoutResult(passed=True, rejection_rule_triggered=False)
    track = PaperTrackRecord(days_running=45, live_result_pct=Decimal(10))
    eligible = evaluate(holdout, track, backtest_expected_pct=Decimal(10), config=_config())
    store.promote("t1", eligible, actor="owner", now=T0)
    assert store.is_promoted("t1") is True

    store.demote("t1", actor="owner", reason="live drifted outside tolerance", now=T0)
    assert store.is_promoted("t1") is False
    demote_events = audit.events(event_type="strategy_demoted")
    assert len(demote_events) == 1
    assert demote_events[0]["actor"] == "owner"
