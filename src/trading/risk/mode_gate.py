"""ModeGate.route(): docs/specs/RISK_ENGINE_SPEC.md §7.

A rejected RiskDecision never reaches any broker, paper or real — this is a
pure function, no side effects, no state (easy to test, AGENTS.md §4.1).
"""

from __future__ import annotations

from enum import StrEnum

from trading.core.enums import Mode, Route
from trading.core.models import RiskDecision


class HumanAction(StrEnum):
    APPROVE = "approve"
    PAPER_TEST = "paper_test"
    REJECT = "reject"


class ModeGate:
    @staticmethod
    def route(decision: RiskDecision, sleeve_mode: Mode, human_action: HumanAction | None) -> Route:
        if not decision.allowed:
            return Route.NONE
        if sleeve_mode is Mode.PAPER:
            return Route.PAPER
        if sleeve_mode is Mode.APPROVAL:
            if human_action is None:
                return Route.NONE
            if human_action is HumanAction.APPROVE:
                return Route.LIVE
            if human_action is HumanAction.PAPER_TEST:
                return Route.PAPER
            return Route.NONE  # REJECT
        return Route.LIVE  # Mode.AUTO

    @staticmethod
    def wants_shadow_fill(
        decision: RiskDecision,
        sleeve_mode: Mode,
        human_action: HumanAction | None,
        *,
        auto_paper_shadow: bool,
    ) -> bool:
        """§7: a human reject with shadow on still produces a SHADOW fill; a
        risk-engine rejection (decision.allowed=False) NEVER does, regardless
        of this setting — that distinction is the whole point of this helper.
        """
        if not decision.allowed:
            return False
        if not auto_paper_shadow:
            return False
        if sleeve_mode is Mode.APPROVAL and human_action is HumanAction.REJECT:
            return True
        return False
