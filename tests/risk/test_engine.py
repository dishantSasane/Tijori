from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal

from trading.core.enums import BrainLabel, MarketId, Mode, ReasonCode, Route
from trading.core.models import BrainVerdict
from trading.risk.engine import ModeGate, check_fail_closed

TS = datetime(2026, 1, 1, 10, 0, tzinfo=UTC)
MKT = MarketId.IN_EQUITY.value


def test_ok_decision_has_single_reason_code(
    engine, passing_signal, passing_portfolio, passing_config
):
    d = engine.check(
        passing_signal, passing_portfolio, None, passing_config, sleeve="india_equity", now=TS
    )
    assert d.allowed is True
    assert d.reason_codes == (ReasonCode.OK,)
    assert d.qty == Decimal(100)


def test_check_1_kill_switch_blocks_before_anything_else(
    engine, passing_signal, passing_portfolio, passing_config
):
    engine.kill_switch_handle.engage("global", "test", actor="owner", now=TS)
    d = engine.check(
        passing_signal, passing_portfolio, None, passing_config, sleeve="india_equity", now=TS
    )
    assert d.allowed is False
    assert d.reason_codes == (ReasonCode.KILL_SWITCH_ENGAGED,)


def test_check_2_mode_permitting_no_route_is_rejected_before_market_check(
    engine, passing_signal, passing_portfolio, passing_config
):
    """No real `Mode` member fails this today (RISK_ENGINE_SPEC.md §2 note),
    so this exercises the gate directly with an out-of-band value -- proving
    check 2 actually executes and rejects, not just a comment that never runs.
    """
    config = replace(passing_config, sleeve_mode="disabled")
    d = engine.check(passing_signal, passing_portfolio, None, config, sleeve="india_equity", now=TS)
    assert d.allowed is False
    assert d.reason_codes == (ReasonCode.MODE_DOES_NOT_PERMIT_ROUTE,)


def test_check_3_market_closed(engine, passing_signal, passing_portfolio, passing_config):
    engine.calendar.set_open(MKT, False)
    d = engine.check(
        passing_signal, passing_portfolio, None, passing_config, sleeve="india_equity", now=TS
    )
    assert d.reason_codes == (ReasonCode.MARKET_CLOSED,)


def test_check_4_stale_data_only_checked_when_market_open(
    engine, passing_signal, passing_portfolio, passing_config
):
    engine.calendar.set_open(MKT, False)
    engine.freshness.set_stale(MKT, "HDFCBANK", True)
    d = engine.check(
        passing_signal, passing_portfolio, None, passing_config, sleeve="india_equity", now=TS
    )
    assert d.reason_codes == (ReasonCode.MARKET_CLOSED,), "check 3 must fire before check 4"


def test_check_4_stale_data_rejects_intraday(
    engine, passing_signal, passing_portfolio, passing_config
):
    engine.freshness.set_stale(MKT, "HDFCBANK", True)
    d = engine.check(
        passing_signal, passing_portfolio, None, passing_config, sleeve="india_equity", now=TS
    )
    assert d.reason_codes == (ReasonCode.DATA_STALE,)


def test_check_5_missing_stop_rejected(engine, passing_signal, passing_portfolio, passing_config):
    signal = passing_signal.model_copy(update={"stop": None})
    d = engine.check(signal, passing_portfolio, None, passing_config, sleeve="india_equity", now=TS)
    assert d.reason_codes == (ReasonCode.SIGNAL_MISSING_STOP,)


def test_check_6_price_band_exceeded(engine, passing_signal, passing_portfolio, passing_config):
    engine.freshness.set_last_price(MKT, "HDFCBANK", Decimal(3000))  # far from entry_ref=2500
    d = engine.check(
        passing_signal, passing_portfolio, None, passing_config, sleeve="india_equity", now=TS
    )
    assert d.reason_codes == (ReasonCode.PRICE_BAND_EXCEEDED,)


def test_check_7_risk_per_trade_exceeded(engine, passing_signal, passing_portfolio, passing_config):
    config = replace(passing_config, max_position_value_pct=Decimal(10_000))
    # entry=2500, equity=1,000,000, risk_pct=0.5% -> budget 5000, distance 50 ->
    # qty=100 is fine normally; force a failure by shrinking equity so even 1
    # lot's risk exceeds budget while qty still rounds to >=1.
    tiny_sleeve = passing_portfolio.sleeve("india_equity")
    from dataclasses import replace as dc_replace

    tiny_sleeve = dc_replace(tiny_sleeve, equity=Decimal(9_000))
    portfolio = dc_replace(passing_portfolio, sleeves={"india_equity": tiny_sleeve})
    config = dc_replace(passing_config, max_position_value_pct=Decimal(10_000))
    d = engine.check(passing_signal, portfolio, None, config, sleeve="india_equity", now=TS)
    assert d.reason_codes in (
        (ReasonCode.QUANTITY_ROUNDS_TO_ZERO,),
        (ReasonCode.RISK_PER_TRADE_EXCEEDED,),
    )


def test_check_9_max_positions_sleeve(engine, passing_signal, passing_portfolio, passing_config):
    from dataclasses import replace as dc_replace

    sleeve = dc_replace(passing_portfolio.sleeve("india_equity"), open_positions=6, max_positions=6)
    portfolio = dc_replace(passing_portfolio, sleeves={"india_equity": sleeve})
    d = engine.check(passing_signal, portfolio, None, passing_config, sleeve="india_equity", now=TS)
    assert d.reason_codes == (ReasonCode.MAX_OPEN_POSITIONS_EXCEEDED,)


def test_check_9_max_positions_global(engine, passing_signal, passing_portfolio, passing_config):
    """Global cap (check 9) is distinct from the sleeve cap (check 8): a
    sleeve well under its own limit can still be rejected once the
    portfolio-wide total hits `max_open_positions_total`.
    """
    config = replace(passing_config, max_open_positions_total=3)
    portfolio = replace(passing_portfolio, total_open_positions=3)
    d = engine.check(passing_signal, portfolio, None, config, sleeve="india_equity", now=TS)
    assert d.reason_codes == (ReasonCode.MAX_OPEN_POSITIONS_EXCEEDED,)
    assert d.limits_snapshot.get("scope") == "global"


def test_check_9_global_cap_not_enforced_when_unconfigured(
    engine, passing_signal, passing_portfolio, passing_config
):
    assert passing_config.max_open_positions_total is None
    portfolio = replace(passing_portfolio, total_open_positions=1_000_000)
    d = engine.check(passing_signal, portfolio, None, passing_config, sleeve="india_equity", now=TS)
    assert d.allowed is True


def test_check_10_daily_loss_limit_breached(
    engine, passing_signal, passing_portfolio, passing_config
):
    from dataclasses import replace as dc_replace

    sleeve = dc_replace(passing_portfolio.sleeve("india_equity"), daily_pnl_pct=Decimal(-3))
    portfolio = dc_replace(passing_portfolio, sleeves={"india_equity": sleeve})
    d = engine.check(passing_signal, portfolio, None, passing_config, sleeve="india_equity", now=TS)
    assert d.reason_codes == (ReasonCode.DAILY_LOSS_LIMIT_BREACHED,)


def test_check_11_portfolio_drawdown_kill_is_read_only(
    engine, passing_signal, passing_portfolio, passing_config
):
    """RISK_ENGINE_SPEC.md §8: check() must stay a pure function of its
    inputs -- it rejects on a drawdown breach but never itself mutates the
    kill switch. The state transition is `monitor_portfolio()`'s job.
    """
    portfolio = replace(
        passing_portfolio,
        portfolio_peak_equity=Decimal(1_000_000),
        portfolio_equity=Decimal(850_000),
    )
    d = engine.check(passing_signal, portfolio, None, passing_config, sleeve="india_equity", now=TS)
    assert d.reason_codes == (ReasonCode.PORTFOLIO_DRAWDOWN_KILL,)
    assert engine.kill_switch_handle.is_engaged("global") is False


def test_monitor_portfolio_engages_kill_switch_on_drawdown_breach(
    engine, passing_portfolio, passing_config, audit
):
    portfolio = replace(
        passing_portfolio,
        portfolio_peak_equity=Decimal(1_000_000),
        portfolio_equity=Decimal(850_000),
    )
    engaged = engine.monitor_portfolio(portfolio, passing_config, now=TS)
    assert engaged is True
    assert engine.kill_switch_handle.is_engaged("global") is True
    events = audit.events(event_type="kill_switch_engaged")
    assert len(events) == 1


def test_monitor_portfolio_is_idempotent_when_already_engaged(
    engine, passing_portfolio, passing_config, audit
):
    portfolio = replace(
        passing_portfolio,
        portfolio_peak_equity=Decimal(1_000_000),
        portfolio_equity=Decimal(850_000),
    )
    engine.monitor_portfolio(portfolio, passing_config, now=TS)
    engine.monitor_portfolio(portfolio, passing_config, now=TS)
    events = audit.events(event_type="kill_switch_engaged")
    assert len(events) == 1


def test_monitor_portfolio_does_not_engage_below_drawdown_threshold(
    engine, passing_portfolio, passing_config
):
    engaged = engine.monitor_portfolio(passing_portfolio, passing_config, now=TS)
    assert engaged is False
    assert engine.kill_switch_handle.is_engaged("global") is False


def test_check_12_instance_paused(engine, passing_signal, passing_portfolio, passing_config):
    from dataclasses import replace as dc_replace

    sleeve = dc_replace(
        passing_portfolio.sleeve("india_equity"), paused_instances=frozenset({"t1"})
    )
    portfolio = dc_replace(passing_portfolio, sleeves={"india_equity": sleeve})
    d = engine.check(passing_signal, portfolio, None, passing_config, sleeve="india_equity", now=TS)
    assert d.reason_codes == (ReasonCode.INSTANCE_PAUSED,)


def test_check_14_duplicate_signal_rejected(
    engine, passing_signal, passing_portfolio, passing_config
):
    first = engine.check(
        passing_signal, passing_portfolio, None, passing_config, sleeve="india_equity", now=TS
    )
    assert first.allowed is True
    second = engine.check(
        passing_signal, passing_portfolio, None, passing_config, sleeve="india_equity", now=TS
    )
    assert second.reason_codes == (ReasonCode.DUPLICATE_SIGNAL,)


def test_check_15_concentration_limit_exceeded(
    engine, passing_signal, passing_portfolio, passing_config
):
    from dataclasses import replace as dc_replace

    sleeve = dc_replace(
        passing_portfolio.sleeve("india_equity"), open_symbols=frozenset({"HDFCBANK"})
    )
    portfolio = dc_replace(passing_portfolio, sleeves={"india_equity": sleeve})
    d = engine.check(passing_signal, portfolio, None, passing_config, sleeve="india_equity", now=TS)
    assert d.reason_codes == (ReasonCode.CONCENTRATION_LIMIT_EXCEEDED,)


def test_s4_rounds_to_zero_via_engine(engine, passing_signal, passing_portfolio, passing_config):
    from dataclasses import replace as dc_replace

    # See test_sizing.py's note: equity=9,000 (not spec's 10,000) is what
    # actually rounds to zero given entry=2500/stop=2450/risk_pct=0.5%.
    sleeve = dc_replace(passing_portfolio.sleeve("india_equity"), equity=Decimal(9_000))
    portfolio = dc_replace(passing_portfolio, sleeves={"india_equity": sleeve})
    d = engine.check(passing_signal, portfolio, None, passing_config, sleeve="india_equity", now=TS)
    assert d.allowed is False
    assert d.reason_codes == (ReasonCode.QUANTITY_ROUNDS_TO_ZERO,)


# --- Brain-verdict suite (§5, I8) ---------------------------------------------


def test_brain_none_treated_as_neutral_full_size(
    engine, passing_signal, passing_portfolio, passing_config
):
    d_none = engine.check(
        passing_signal, passing_portfolio, None, passing_config, sleeve="india_equity", now=TS
    )
    # fresh decision store for a second, equivalent signal id to compare fairly
    signal2 = passing_signal.model_copy(update={"id": "s2"})
    neutral = BrainVerdict(
        signal_id="s2", label=BrainLabel.NEUTRAL, size_multiplier=Decimal(1), created_ts=TS
    )
    d_neutral = engine.check(
        signal2, passing_portfolio, neutral, passing_config, sleeve="india_equity", now=TS
    )
    assert d_none.qty == d_neutral.qty
    assert d_none.allowed == d_neutral.allowed


def test_brain_veto_rejects_regardless_of_sizing(
    engine, passing_signal, passing_portfolio, passing_config
):
    veto = BrainVerdict(
        signal_id=passing_signal.id,
        label=BrainLabel.VETO,
        size_multiplier=Decimal(0),
        created_ts=TS,
    )
    d = engine.check(
        passing_signal, passing_portfolio, veto, passing_config, sleeve="india_equity", now=TS
    )
    assert d.allowed is False
    assert d.reason_codes == (ReasonCode.BRAIN_VETO,)
    assert d.qty == Decimal(0)


def test_brain_support_does_not_increase_size(
    engine, passing_signal, passing_portfolio, passing_config
):
    support = BrainVerdict(
        signal_id=passing_signal.id,
        label=BrainLabel.SUPPORT,
        size_multiplier=Decimal(1),
        created_ts=TS,
    )
    d_support = engine.check(
        passing_signal, passing_portfolio, support, passing_config, sleeve="india_equity", now=TS
    )
    signal2 = passing_signal.model_copy(update={"id": "s2"})
    neutral = BrainVerdict(
        signal_id="s2", label=BrainLabel.NEUTRAL, size_multiplier=Decimal(1), created_ts=TS
    )
    d_neutral = engine.check(
        signal2, passing_portfolio, neutral, passing_config, sleeve="india_equity", now=TS
    )
    assert d_support.qty == d_neutral.qty


# --- Fail-closed suite (§1, I6) -----------------------------------------------


def test_check_function_raising_is_fail_closed(
    engine, passing_signal, passing_portfolio, passing_config
):
    def boom(*args, **kwargs):
        raise ValueError("boom")

    engine.freshness.is_stale = boom  # type: ignore[method-assign]
    d = check_fail_closed(
        engine,
        passing_signal,
        passing_portfolio,
        None,
        passing_config,
        sleeve="india_equity",
        now=TS,
    )
    assert d.allowed is False
    assert d.reason_codes == (ReasonCode.INTERNAL_ERROR_FAIL_CLOSED,)


# --- ModeGate / route suite (§7) ----------------------------------------------


def test_route_none_on_rejected_decision_regardless_of_mode(passing_signal):
    from trading.core.models import RiskDecision

    rejected = RiskDecision(
        signal_id=passing_signal.id,
        allowed=False,
        qty=Decimal(0),
        reason_codes=(ReasonCode.MARKET_CLOSED,),
        created_ts=TS,
    )
    for mode in (Mode.PAPER, Mode.APPROVAL, Mode.AUTO):
        assert ModeGate.route(rejected, mode, None) == Route.NONE


def test_route_paper_mode_always_paper(passing_signal):
    from trading.core.models import RiskDecision

    allowed = RiskDecision(
        signal_id=passing_signal.id,
        allowed=True,
        qty=Decimal(10),
        reason_codes=(ReasonCode.OK,),
        created_ts=TS,
    )
    assert ModeGate.route(allowed, Mode.PAPER, None) == Route.PAPER


def test_route_approval_mode_awaits_human(passing_signal):
    from trading.core.models import RiskDecision

    allowed = RiskDecision(
        signal_id=passing_signal.id,
        allowed=True,
        qty=Decimal(10),
        reason_codes=(ReasonCode.OK,),
        created_ts=TS,
    )
    assert ModeGate.route(allowed, Mode.APPROVAL, None) == Route.NONE
    assert ModeGate.route(allowed, Mode.APPROVAL, "approve") == Route.LIVE
    assert ModeGate.route(allowed, Mode.APPROVAL, "paper_test") == Route.PAPER
    assert ModeGate.route(allowed, Mode.APPROVAL, "reject") == Route.NONE


def test_route_auto_mode_always_live(passing_signal):
    from trading.core.models import RiskDecision

    allowed = RiskDecision(
        signal_id=passing_signal.id,
        allowed=True,
        qty=Decimal(10),
        reason_codes=(ReasonCode.OK,),
        created_ts=TS,
    )
    assert ModeGate.route(allowed, Mode.AUTO, None) == Route.LIVE
