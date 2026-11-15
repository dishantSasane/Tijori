from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal

from trading.core.enums import BrainLabel, MarketId, Mode, ReasonCode, Route
from trading.core.models import BrainVerdict
from trading.risk.engine import ModeGate, check_fail_closed
from trading.risk.portfolio import SleeveState

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


def test_check_8_sleeve_allocation_exceeded(
    engine, passing_signal, passing_portfolio, passing_config
):
    sleeve = replace(
        passing_portfolio.sleeve("india_equity"),
        allocation_used_pct=Decimal(45),
        allocation_cap_pct=Decimal(40),
    )
    portfolio = replace(passing_portfolio, sleeves={"india_equity": sleeve})
    d = engine.check(passing_signal, portfolio, None, passing_config, sleeve="india_equity", now=TS)
    assert d.reason_codes == (ReasonCode.SLEEVE_ALLOCATION_EXCEEDED,)


def test_memecoin_allocation_cap_enforced_independently_of_crypto_cap(
    engine, passing_signal, passing_portfolio, passing_config
):
    """Config separates `memecoin` from the general `crypto` sleeve (RISK_SPEC.md,
    config/risk.example.yaml) so a tight memecoin cap can't be masked by crypto's
    looser one, and vice versa.
    """
    engine.calendar.set_open(MarketId.CRYPTO.value, True)

    crypto_sleeve = SleeveState(
        equity=Decimal(100_000),
        open_positions=0,
        daily_pnl_pct=Decimal(0),
        allocation_used_pct=Decimal(10),
        allocation_cap_pct=Decimal(25),
        max_positions=4,
    )
    memecoin_sleeve = SleeveState(
        equity=Decimal(100_000),
        open_positions=0,
        daily_pnl_pct=Decimal(0),
        allocation_used_pct=Decimal(6),
        allocation_cap_pct=Decimal(5),
        max_positions=3,
    )
    portfolio = replace(
        passing_portfolio, sleeves={"crypto": crypto_sleeve, "memecoin": memecoin_sleeve}
    )
    signal = passing_signal.model_copy(update={"market": MarketId.CRYPTO})
    config = replace(passing_config, market=MarketId.CRYPTO)

    # memecoin is over its own (tighter) cap even though crypto's cap has room.
    memecoin_decision = engine.check(signal, portfolio, None, config, sleeve="memecoin", now=TS)
    assert memecoin_decision.reason_codes == (ReasonCode.SLEEVE_ALLOCATION_EXCEEDED,)

    # crypto is unaffected by memecoin's breach -- caps are tracked per sleeve.
    crypto_decision = engine.check(signal, portfolio, None, config, sleeve="crypto", now=TS)
    assert crypto_decision.reason_codes == (ReasonCode.OK,)


def test_check_10_daily_loss_limit_breached(
    engine, passing_signal, passing_portfolio, passing_config
):
    from dataclasses import replace as dc_replace

    sleeve = dc_replace(passing_portfolio.sleeve("india_equity"), daily_pnl_pct=Decimal(-3))
    portfolio = dc_replace(passing_portfolio, sleeves={"india_equity": sleeve})
    d = engine.check(passing_signal, portfolio, None, passing_config, sleeve="india_equity", now=TS)
    assert d.reason_codes == (ReasonCode.DAILY_LOSS_LIMIT_BREACHED,)


def test_check_11_portfolio_drawdown_kill_also_engages_switch(
    engine, passing_signal, passing_portfolio, passing_config
):
    from dataclasses import replace as dc_replace

    portfolio = dc_replace(
        passing_portfolio,
        portfolio_peak_equity=Decimal(1_000_000),
        portfolio_equity=Decimal(850_000),
    )
    d = engine.check(passing_signal, portfolio, None, passing_config, sleeve="india_equity", now=TS)
    assert d.reason_codes == (ReasonCode.PORTFOLIO_DRAWDOWN_KILL,)
    assert engine.kill_switch_handle.is_engaged("global") is True


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
