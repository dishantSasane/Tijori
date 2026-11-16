"""Brain A/B in paper (docs/BUILD_ORDER.md P6, docs/BRAIN_AND_COSTS.md §1
rule 7: value can only be judged in forward paper, never backtest, because
an LLM may have seen historical events in training).

This runs the SAME signal through `RiskEngine.check()` twice -- once with
whatever verdict the Brain actually returned, once forced to the "Brain
absent" baseline -- and logs both decisions side by side via the existing
audit log. It changes no routing: the real paper order always comes from
the Brain-on decision when Brain is enabled (that's just normal operation);
this harness exists purely to also record what would have happened with
Brain off, so the two paths can be compared later from the audit log. No
new table, no new state machine -- `audit_log` already has everything
needed (ponytail: YAGNI on a dedicated A/B store).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from trading.core.models import BrainVerdict, RiskDecision, Signal
from trading.risk.audit import AuditLog
from trading.risk.decision_store import DecisionStore
from trading.risk.engine import RiskEngine, default_absent_verdict
from trading.risk.portfolio import PortfolioState, RiskConfig
from trading.storage.state_db import connect

AB_EVENT = "brain_ab_comparison"


@dataclass(frozen=True)
class ABResult:
    brain_on: RiskDecision
    brain_off: RiskDecision


def run_ab(
    engine: RiskEngine,
    signal: Signal,
    portfolio: PortfolioState,
    config: RiskConfig,
    *,
    brain_verdict: BrainVerdict | None,
    sleeve: str,
    now: datetime,
    audit: AuditLog,
) -> ABResult:
    """`brain_verdict` is whatever the Brain actually returned (or None) for
    this signal under the live config. The "off" arm always uses the
    explicit neutral/full-size baseline, matching exactly what the risk
    engine already does when Brain is disabled -- so this harness can never
    diverge from real Brain-off behaviour.

    Both arms must evaluate check 14's duplicate-signal guard (RED_TEAM.md
    scenario 10) independently, so the off-arm runs against a throwaway
    `DecisionStore` rather than `engine`'s own one -- otherwise recording the
    on-arm's decision for `signal.id` would make the off-arm see it as a
    duplicate of itself, which is a harness artifact, not a real duplicate
    signal. Kill switch/calendar/freshness are still the real, shared ones,
    since those must agree across both arms.
    """
    on_decision = engine.check(signal, portfolio, brain_verdict, config, sleeve=sleeve, now=now)

    shadow_engine = RiskEngine(
        kill_switch=engine._kill_switch,  # noqa: SLF001 - intentional: share real kill-switch state
        decision_store=DecisionStore(connect(":memory:")),
        calendar=engine._calendar,  # noqa: SLF001
        freshness=engine._freshness,  # noqa: SLF001
    )
    off_decision = shadow_engine.check(
        signal,
        portfolio,
        default_absent_verdict(signal.id, now=now),
        config,
        sleeve=sleeve,
        now=now,
    )
    audit.write(
        ts_utc=now,
        event_type=AB_EVENT,
        actor="brain_ab_harness",
        payload={
            "signal_id": signal.id,
            "brain_on": {
                "allowed": on_decision.allowed,
                "qty": str(on_decision.qty),
                "reason_codes": [c.value for c in on_decision.reason_codes],
            },
            "brain_off": {
                "allowed": off_decision.allowed,
                "qty": str(off_decision.qty),
                "reason_codes": [c.value for c in off_decision.reason_codes],
            },
        },
    )
    return ABResult(brain_on=on_decision, brain_off=off_decision)
