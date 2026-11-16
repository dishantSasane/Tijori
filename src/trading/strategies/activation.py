"""Deterministic regime-state calculation and strategy eligibility routing."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Decimal, localcontext
from enum import StrEnum


class TrendState(StrEnum):
    UP = "up"
    DOWN = "down"
    SIDEWAYS = "sideways"
    UNKNOWN = "unknown"


class VolatilityState(StrEnum):
    NORMAL = "normal"
    HIGH = "high"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class RegimeState:
    trend: TrendState
    volatility: VolatilityState


@dataclass(frozen=True)
class StrategyEligibility:
    strategy_id: str
    version: str
    promoted: bool
    allowed_states: frozenset[RegimeState]


@dataclass(frozen=True)
class ActivationDecision:
    state: RegimeState
    considered_strategy_versions: tuple[tuple[str, str], ...]
    eligible_strategy_versions: tuple[tuple[str, str], ...]
    reason: str


@dataclass
class ActivationCounter:
    opportunities: int = 0
    eligible: int = 0
    abstentions: int = 0
    conflicts: int = 0
    emitted_signals: int = 0


def _nearest_rank(values: list[Decimal], quantile: Decimal) -> Decimal:
    ordered = sorted(values)
    numerator, denominator = quantile.as_integer_ratio()
    rank = (len(ordered) * numerator + denominator - 1) // denominator
    return ordered[max(1, rank) - 1]


def calculate_regime(
    *,
    close: Decimal | None,
    sma200: Decimal | None,
    sma200_20_sessions_ago: Decimal | None,
    atr14: Decimal | None,
    close_history_atr_ratios: list[Decimal] | tuple[Decimal, ...],
) -> RegimeState:
    """Calculate state from closed-bar features and strictly prior history."""
    current_values = (close, sma200, sma200_20_sessions_ago)
    if (
        any(value is None or not value.is_finite() for value in current_values)
        or close is None
        or sma200 is None
        or sma200_20_sessions_ago is None
        or close <= 0
    ):
        trend = TrendState.UNKNOWN
    elif close > sma200 and sma200 > sma200_20_sessions_ago:
        trend = TrendState.UP
    elif close < sma200 and sma200 < sma200_20_sessions_ago:
        trend = TrendState.DOWN
    else:
        trend = TrendState.SIDEWAYS

    if (
        atr14 is None
        or close is None
        or not atr14.is_finite()
        or not close.is_finite()
        or close <= 0
        or len(close_history_atr_ratios) < 252
    ):
        volatility = VolatilityState.UNKNOWN
    else:
        if atr14 < 0 or any(not item.is_finite() or item < 0 for item in close_history_atr_ratios):
            return RegimeState(trend, VolatilityState.UNKNOWN)
        threshold = _nearest_rank(list(close_history_atr_ratios[-252:]), Decimal("0.8"))
        values = (atr14, close, threshold)
        precision = max(len(value.as_tuple().digits) for value in values) + 12
        with localcontext() as context:
            context.prec = max(50, precision)
            context.rounding = ROUND_HALF_EVEN
            ratio = atr14 / close
        if not ratio.is_finite():
            volatility = VolatilityState.UNKNOWN
        else:
            volatility = VolatilityState.NORMAL if ratio <= threshold else VolatilityState.HIGH
    return RegimeState(trend=trend, volatility=volatility)


def route_strategies(
    state: RegimeState, strategies: list[StrategyEligibility] | tuple[StrategyEligibility, ...]
) -> ActivationDecision:
    """Return eligible promoted strategies or an explicit abstention/conflict."""
    strategy_keys = [(strategy.strategy_id, strategy.version) for strategy in strategies]
    if len(strategy_keys) != len(set(strategy_keys)):
        raise ValueError("duplicate strategy version declaration")
    considered = tuple(sorted(strategy_keys))
    if state.trend is TrendState.UNKNOWN or state.volatility is VolatilityState.UNKNOWN:
        return ActivationDecision(state, considered, (), "abstain:unknown_state")
    eligible = tuple(
        sorted(
            (strategy.strategy_id, strategy.version)
            for strategy in strategies
            if strategy.promoted and state in strategy.allowed_states
        )
    )
    if not eligible:
        return ActivationDecision(state, considered, (), "abstain:no_eligible_strategy")
    if len(eligible) > 1:
        return ActivationDecision(state, considered, eligible, "overlap:multiple_eligible")
    return ActivationDecision(state, considered, eligible, "eligible")


def record_activation(
    counters: dict[tuple[str, str, str], ActivationCounter],
    decision: ActivationDecision,
    *,
    catalog_strategy_versions: tuple[tuple[str, str], ...],
    instrument_id: str,
    emitted_by_strategy_version_and_instrument: dict[tuple[str, str, str], int],
) -> None:
    if len(catalog_strategy_versions) != len(set(catalog_strategy_versions)):
        raise ValueError("catalog strategy versions must be unique")
    if any(count < 0 for count in emitted_by_strategy_version_and_instrument.values()):
        raise ValueError("signals_emitted must be non-negative")
    eligible_keys = set(decision.eligible_strategy_versions)
    catalog_keys = set(catalog_strategy_versions)
    if not eligible_keys.issubset(catalog_keys):
        raise ValueError("eligible strategy version is absent from the catalog")
    if not set(emitted_by_strategy_version_and_instrument).issubset(
        {(strategy_id, version, instrument_id) for strategy_id, version in eligible_keys}
    ):
        raise ValueError("emitted signals must identify an eligible catalog version and instrument")
    for strategy_id, version in catalog_strategy_versions:
        key = (strategy_id, version)
        counter_key = (strategy_id, version, instrument_id)
        counter = counters.setdefault(counter_key, ActivationCounter())
        counter.opportunities += 1
        if key in eligible_keys:
            counter.eligible += 1
        else:
            counter.abstentions += 1
        if key in eligible_keys and decision.reason.startswith("overlap:"):
            counter.conflicts += 1
        if key in eligible_keys:
            counter.emitted_signals += emitted_by_strategy_version_and_instrument.get(
                (*key, instrument_id), 0
            )
