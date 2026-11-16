from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal

from trading.brain.ab_harness import AB_EVENT, run_ab
from trading.core.enums import BrainLabel
from trading.core.models import BrainVerdict

TS = datetime(2026, 1, 1, 10, 0, tzinfo=UTC)


def test_brain_veto_blocks_on_but_off_arm_still_approves(
    engine, audit, passing_signal, passing_portfolio, passing_config
):
    veto = BrainVerdict(
        signal_id=passing_signal.id,
        label=BrainLabel.VETO,
        size_multiplier=Decimal(1),
        created_ts=TS,
    )
    result = run_ab(
        engine,
        passing_signal,
        passing_portfolio,
        passing_config,
        brain_verdict=veto,
        sleeve="india_equity",
        now=TS,
        audit=audit,
    )
    assert result.brain_on.allowed is False
    assert result.brain_off.allowed is True


def test_ab_comparison_is_logged_to_audit(
    engine, audit, passing_signal, passing_portfolio, passing_config
):
    run_ab(
        engine,
        passing_signal,
        passing_portfolio,
        passing_config,
        brain_verdict=None,
        sleeve="india_equity",
        now=TS,
        audit=audit,
    )
    rows = audit.events(event_type=AB_EVENT)
    assert len(rows) == 1
    payload = json.loads(rows[0]["payload_json"])
    assert payload["signal_id"] == passing_signal.id
    assert payload["brain_on"]["allowed"] is True
    assert payload["brain_off"]["allowed"] is True
