from decimal import Decimal

from trading.strategies.activation import (
    ActivationCounter,
    RegimeState,
    StrategyEligibility,
    TrendState,
    VolatilityState,
    calculate_regime,
    record_activation,
    route_strategies,
)


def test_uptrend_and_normal_volatility_state() -> None:
    history = [Decimal("0.01")] * 251 + [Decimal("0.02")]
    state = calculate_regime(
        close=Decimal("110"),
        sma200=Decimal("100"),
        sma200_20_sessions_ago=Decimal("95"),
        atr14=Decimal("1"),
        close_history_atr_ratios=history,
    )
    assert state == RegimeState(TrendState.UP, VolatilityState.NORMAL)


def test_missing_regime_inputs_fail_closed_to_unknown() -> None:
    state = calculate_regime(
        close=None,
        sma200=Decimal("100"),
        sma200_20_sessions_ago=Decimal("95"),
        atr14=Decimal("1"),
        close_history_atr_ratios=[Decimal("0.01")] * 252,
    )
    assert state.trend is TrendState.UNKNOWN
    assert route_strategies(state, []).reason == "abstain:unknown_state"


def test_current_volatility_is_compared_with_only_supplied_prior_values() -> None:
    state = calculate_regime(
        close=Decimal("100"),
        sma200=Decimal("100"),
        sma200_20_sessions_ago=Decimal("100"),
        atr14=Decimal("3"),
        close_history_atr_ratios=[Decimal("0.01")] * 252,
    )
    assert state.trend is TrendState.SIDEWAYS
    assert state.volatility is VolatilityState.HIGH


def test_insufficient_percentile_history_is_unknown() -> None:
    state = calculate_regime(
        close=Decimal("100"),
        sma200=Decimal("100"),
        sma200_20_sessions_ago=Decimal("100"),
        atr14=Decimal("1"),
        close_history_atr_ratios=[Decimal("0.01")] * 251,
    )
    assert state.volatility is VolatilityState.UNKNOWN


def test_router_abstains_when_no_promoted_strategy_is_eligible() -> None:
    state = RegimeState(TrendState.UP, VolatilityState.NORMAL)
    candidate = StrategyEligibility("t1", "1", False, frozenset({state}))
    decision = route_strategies(state, [candidate])
    assert decision.reason == "abstain:no_eligible_strategy"
    assert decision.considered_strategy_versions == (("t1", "1"),)


def test_router_returns_overlap_instead_of_silent_tie_break() -> None:
    state = RegimeState(TrendState.UP, VolatilityState.NORMAL)
    strategies = [StrategyEligibility(name, "1", True, frozenset({state})) for name in ("t2", "t1")]
    decision = route_strategies(state, strategies)
    assert decision.reason == "overlap:multiple_eligible"
    assert decision.eligible_strategy_versions == (("t1", "1"), ("t2", "1"))


def test_activation_metrics_count_opportunities_and_conflicts() -> None:
    state = RegimeState(TrendState.UP, VolatilityState.NORMAL)
    decision = route_strategies(
        state,
        [StrategyEligibility(name, "1", True, frozenset({state})) for name in ("t2", "t1")],
    )
    counters: dict[tuple[str, str, str], ActivationCounter] = {}
    record_activation(
        counters,
        decision,
        catalog_strategy_versions=(("t1", "1"), ("t2", "1")),
        instrument_id="TEST",
        emitted_by_strategy_version_and_instrument={("t1", "1", "TEST"): 0},
    )
    assert counters[("t1", "1", "TEST")].opportunities == 1
    assert counters[("t1", "1", "TEST")].conflicts == 1
    assert counters[("t1", "1", "TEST")].emitted_signals == 0


def test_ineligible_candidate_contributes_to_opportunity_denominator() -> None:
    state = RegimeState(TrendState.UP, VolatilityState.NORMAL)
    candidate = StrategyEligibility(
        "t4", "1", True, frozenset({RegimeState(TrendState.SIDEWAYS, VolatilityState.NORMAL)})
    )
    decision = route_strategies(state, [candidate])
    counters: dict[tuple[str, str, str], ActivationCounter] = {}
    record_activation(
        counters,
        decision,
        catalog_strategy_versions=(("t4", "1"),),
        instrument_id="TEST",
        emitted_by_strategy_version_and_instrument={},
    )
    assert counters[("t4", "1", "TEST")].opportunities == 1
    assert counters[("t4", "1", "TEST")].eligible == 0


def test_invalid_volatility_history_returns_unknown() -> None:
    state = calculate_regime(
        close=Decimal("100"),
        sma200=Decimal("100"),
        sma200_20_sessions_ago=Decimal("100"),
        atr14=Decimal("1"),
        close_history_atr_ratios=[Decimal("-0.01")] * 252,
    )
    assert state.volatility is VolatilityState.UNKNOWN
