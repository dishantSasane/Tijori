from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from trading.core.enums import Mode, ReasonCode, Route
from trading.core.models import RiskDecision
from trading.risk.mode_gate import HumanAction, ModeGate

NOW = datetime(2026, 1, 5, 5, 0, tzinfo=UTC)


def _decision(allowed: bool) -> RiskDecision:
    if allowed:
        return RiskDecision(
            signal_id="s1",
            allowed=True,
            qty=Decimal(10),
            reason_codes=(ReasonCode.OK,),
            created_ts=NOW,
        )
    return RiskDecision(
        signal_id="s1",
        allowed=False,
        qty=Decimal(0),
        reason_codes=(ReasonCode.MARKET_CLOSED,),
        created_ts=NOW,
    )


@pytest.mark.parametrize("mode", [Mode.PAPER, Mode.APPROVAL, Mode.AUTO])
def test_route_none_on_rejected_decision_regardless_of_mode(mode):
    assert ModeGate.route(_decision(False), mode, None) == Route.NONE


def test_paper_mode_only_ever_returns_paper():
    assert ModeGate.route(_decision(True), Mode.PAPER, None) == Route.PAPER


def test_approval_mode_awaits_human():
    assert ModeGate.route(_decision(True), Mode.APPROVAL, None) == Route.NONE


def test_approval_mode_approve_routes_live():
    assert ModeGate.route(_decision(True), Mode.APPROVAL, HumanAction.APPROVE) == Route.LIVE


def test_approval_mode_paper_test_routes_paper():
    assert ModeGate.route(_decision(True), Mode.APPROVAL, HumanAction.PAPER_TEST) == Route.PAPER


def test_approval_mode_reject_routes_none():
    assert ModeGate.route(_decision(True), Mode.APPROVAL, HumanAction.REJECT) == Route.NONE


def test_auto_mode_always_live_when_allowed():
    assert ModeGate.route(_decision(True), Mode.AUTO, None) == Route.LIVE


def test_approval_reject_with_shadow_on_wants_shadow_fill():
    assert ModeGate.wants_shadow_fill(
        _decision(True), Mode.APPROVAL, HumanAction.REJECT, auto_paper_shadow=True
    )


def test_approval_reject_with_shadow_off_no_fill():
    assert not ModeGate.wants_shadow_fill(
        _decision(True), Mode.APPROVAL, HumanAction.REJECT, auto_paper_shadow=False
    )


def test_rejected_decision_never_produces_shadow_fill():
    assert not ModeGate.wants_shadow_fill(
        _decision(False), Mode.APPROVAL, HumanAction.REJECT, auto_paper_shadow=True
    )
