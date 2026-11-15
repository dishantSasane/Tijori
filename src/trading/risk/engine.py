"""RiskEngine.check(): the pre-trade gate every signal must pass.

Implements docs/specs/RISK_ENGINE_SPEC.md §2 (check order, exact), §3
(sizing), §5 (Brain handling). First failure wins; `check()` never raises for
a *rejection* — it returns `RiskDecision(allowed=False, ...)`. It raises only
for truly unexpected inputs (NaN/Infinity, a check itself throwing), and the
caller must treat that as `ReasonCode.INTERNAL_ERROR_FAIL_CLOSED` (§1).
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation

from trading.adapters.llm_provider import default_absent_verdict
from trading.core.enums import BrainLabel, ReasonCode
from trading.core.models import BrainVerdict, RiskDecision, Signal
from trading.risk.config import PortfolioState, RiskConfig
from trading.risk.kill_switch import GLOBAL_SCOPE, KillSwitch, instance_scope, sleeve_scope


class InternalRiskError(RuntimeError):
    """Raised by check() only for genuinely unexpected input (§1). The caller
    must catch this and record ReasonCode.INTERNAL_ERROR_FAIL_CLOSED — the
    engine itself never swallows it into a normal rejection, so a bug here is
    always loud in the audit log, never a quiet "no".
    """


def _is_finite(value: Decimal) -> bool:
    try:
        return value.is_finite()
    except (InvalidOperation, AttributeError):
        return False


def _assert_finite_portfolio(state: PortfolioState) -> None:
    decimals = [
        state.sleeve.equity,
        state.sleeve.open_position_value,
        state.sleeve.daily_pnl_pct,
        state.portfolio_drawdown_pct,
        state.liquidity_cap_qty,
        *state.sleeve.symbol_risk_pct.values(),
    ]
    if state.last_tick_price is not None:
        decimals.append(state.last_tick_price)
    for value in decimals:
        if not _is_finite(value):
            raise InternalRiskError("NaN/Infinity in portfolio_state")


@dataclass(frozen=True)
class MarketSession:
    """Minimal calendar port: is this market open at `now`? Real calendars
    (exchange_calendars) are an adapter concern; tests supply a fake.
    """

    is_open: Callable[[Signal, datetime], bool]
    is_24x7: bool = False


@dataclass(frozen=True)
class DataFreshnessCheck:
    """Port over DataFeed.is_stale (ADAPTERS.md §1)."""

    is_stale: Callable[[Signal, datetime, int], bool]


class RiskEngine:
    def __init__(
        self,
        *,
        kill_switch: KillSwitch,
        market_session: MarketSession,
        freshness: DataFreshnessCheck,
    ) -> None:
        self._kill_switch = kill_switch
        self._market_session = market_session
        self._freshness = freshness

    def check(
        self,
        signal: Signal,
        portfolio_state: PortfolioState,
        brain_verdict: BrainVerdict | None,
        config: RiskConfig,
        *,
        now: datetime,
    ) -> RiskDecision:
        try:
            return self._check(signal, portfolio_state, brain_verdict, config, now=now)
        except InternalRiskError:
            return RiskDecision(
                signal_id=signal.id,
                allowed=False,
                qty=Decimal(0),
                reason_codes=(ReasonCode.INTERNAL_ERROR_FAIL_CLOSED,),
                created_ts=now,
            )

    def _reject(
        self,
        signal: Signal,
        now: datetime,
        *codes: ReasonCode,
        limits_snapshot: dict[str, object] | None = None,
    ) -> RiskDecision:
        return RiskDecision(
            signal_id=signal.id,
            allowed=False,
            qty=Decimal(0),
            reason_codes=tuple(codes),
            limits_snapshot=limits_snapshot or {},
            created_ts=now,
        )

    def _check(
        self,
        signal: Signal,
        state: PortfolioState,
        brain_verdict: BrainVerdict | None,
        config: RiskConfig,
        *,
        now: datetime,
    ) -> RiskDecision:
        _assert_finite_portfolio(state)

        # 1. Kill switch: global, sleeve, instance (in that order).
        strategy_sleeve = signal.market.value
        scopes = (
            GLOBAL_SCOPE,
            sleeve_scope(strategy_sleeve),
            instance_scope(signal.strategy_id, signal.market.value),
        )
        engaged_scope = self._kill_switch.any_engaged(scopes)
        if engaged_scope is not None:
            return self._reject(
                signal,
                now,
                ReasonCode.KILL_SWITCH_ENGAGED,
                limits_snapshot={"engaged_scope": engaged_scope},
            )

        # 2. Mode permits this route — "may this ever become an order at all".
        # Every mode (paper/approval/auto) permits *some* route; a reject here
        # is reserved for a sleeve explicitly disabled in config (not yet a
        # concept — flagged, not implemented, since no caller needs it: YAGNI).

        # 3. Market session open.
        if not self._market_session.is_24x7 and not self._market_session.is_open(signal, now):
            return self._reject(signal, now, ReasonCode.MARKET_CLOSED)

        # 4. Data freshness (session-aware; §6 — moot once check 3 already failed).
        if self._freshness.is_stale(signal, now, config.stale_data_seconds):
            return self._reject(signal, now, ReasonCode.DATA_STALE)

        # 5. Signal validity: stop present; risk distance in bounds.
        if signal.stop is None:
            return self._reject(signal, now, ReasonCode.SIGNAL_MISSING_STOP)
        risk_distance = abs(signal.entry_ref - signal.stop)
        max_distance = (
            signal.entry_ref * config.sleeve.max_risk_distance_pct_of_entry / Decimal(100)
        )
        if risk_distance <= 0 or risk_distance > max_distance:
            return self._reject(signal, now, ReasonCode.SIGNAL_RISK_DISTANCE_OUT_OF_BOUNDS)

        # 6. Price band (fat-finger/gap protection) — uses DataFeed.last_tick, not
        # the signal's own entry_ref, which may be stale by now.
        if state.last_tick_price is not None:
            band = signal.entry_ref * config.order_price_band_pct / Decimal(100)
            if abs(state.last_tick_price - signal.entry_ref) > band:
                return self._reject(signal, now, ReasonCode.PRICE_BAND_EXCEEDED)

        # ---- Sizing (§3) happens before check 7, which needs a quantity. ----
        qty = self._size(signal, state, config, risk_distance)

        # 7. Risk per trade (one full lot's worth already exceeds budget).
        risk_budget = state.sleeve.equity * config.sleeve.risk_per_trade_pct / Decimal(100)
        min_lot = config.sleeve.lot_size
        if min_lot * risk_distance > risk_budget:
            return self._reject(signal, now, ReasonCode.RISK_PER_TRADE_EXCEEDED)

        # 8. Sleeve allocation and max positions (sleeve-scoped).
        position_value = qty * signal.entry_ref
        max_sleeve_value = state.sleeve.equity * config.sleeve.sleeve_allocation_pct / Decimal(100)
        if state.sleeve.open_position_value + position_value > max_sleeve_value:
            return self._reject(signal, now, ReasonCode.SLEEVE_ALLOCATION_EXCEEDED)
        if state.sleeve.open_position_count >= config.sleeve.max_open_positions:
            return self._reject(
                signal,
                now,
                ReasonCode.MAX_OPEN_POSITIONS_EXCEEDED,
                limits_snapshot={"scope": "sleeve"},
            )

        # 9. Max open positions, global.
        if state.total_open_positions >= config.max_open_positions_total:
            return self._reject(
                signal,
                now,
                ReasonCode.MAX_OPEN_POSITIONS_EXCEEDED,
                limits_snapshot={"scope": "global"},
            )

        # 10. Daily loss limit.
        if state.sleeve.daily_pnl_pct <= -config.sleeve.max_daily_loss_pct:
            return self._reject(signal, now, ReasonCode.DAILY_LOSS_LIMIT_BREACHED)

        # 11. Portfolio drawdown kill — also engages the global kill switch (§8).
        if state.portfolio_drawdown_pct >= config.max_portfolio_drawdown_pct:
            self._kill_switch.engage(
                GLOBAL_SCOPE, "portfolio_drawdown_kill_threshold_breached", actor="system"
            )
            return self._reject(signal, now, ReasonCode.PORTFOLIO_DRAWDOWN_KILL)

        # 12. Instance not paused.
        if state.instance.paused:
            return self._reject(signal, now, ReasonCode.INSTANCE_PAUSED)

        # 12.5 (check 17 in RISK_SPEC.md's own numbering): no existing position
        # already occupies this symbol slot for the instance.
        if signal.symbol in state.instance.open_symbols:
            return self._reject(signal, now, ReasonCode.CONCURRENT_POSITION_EXISTS)

        # 13. Liquidity cap — applied again at sizing time (§3) but also gates here
        # if the minimum lot already exceeds it.
        if min_lot > state.liquidity_cap_qty:
            return self._reject(signal, now, ReasonCode.LIQUIDITY_CAP_EXCEEDED)

        # 14. Idempotency.
        if signal.id in state.decided_signal_ids:
            return self._reject(signal, now, ReasonCode.DUPLICATE_SIGNAL)

        # 15. Concentration/correlation (single-symbol, start simple).
        existing_symbol_risk = state.sleeve.symbol_risk_pct.get(signal.symbol, Decimal(0))
        new_symbol_risk_pct = (qty * risk_distance / state.sleeve.equity) * Decimal(100)
        if existing_symbol_risk + new_symbol_risk_pct > config.sleeve.concentration_limit_pct:
            return self._reject(signal, now, ReasonCode.CONCENTRATION_LIMIT_EXCEEDED)

        # 16. Brain verdict (§5) — can only veto or shrink, never reject alone
        # without also zeroing qty, never increase size.
        effective = (
            brain_verdict
            if brain_verdict is not None
            else default_absent_verdict(signal.id, now=now)
        )
        if effective.label == BrainLabel.VETO:
            return self._reject(signal, now, ReasonCode.BRAIN_VETO)
        qty = (qty * effective.size_multiplier).to_integral_value(rounding="ROUND_FLOOR")
        qty = (qty // min_lot) * min_lot if min_lot > 0 else qty

        if qty < min_lot or qty <= 0:
            return self._reject(signal, now, ReasonCode.QUANTITY_ROUNDS_TO_ZERO)

        return RiskDecision(
            signal_id=signal.id,
            allowed=True,
            qty=qty,
            reason_codes=(ReasonCode.OK,),
            created_ts=now,
        )

    @staticmethod
    def _size(
        signal: Signal, state: PortfolioState, config: RiskConfig, risk_distance: Decimal
    ) -> Decimal:
        """§3's algorithm. Floor at every step; never round up."""
        risk_budget = state.sleeve.equity * config.sleeve.risk_per_trade_pct / Decimal(100)
        raw_qty = _floor(risk_budget / risk_distance)
        max_value_qty = _floor(
            config.sleeve.max_position_value_pct
            * state.sleeve.equity
            / Decimal(100)
            / signal.entry_ref
        )
        qty = min(raw_qty, max_value_qty, _floor(state.liquidity_cap_qty))
        lot = config.sleeve.lot_size
        qty = _floor(qty / lot) * lot
        return max(qty, Decimal(0))


def _floor(value: Decimal) -> Decimal:
    if not value.is_finite():
        raise InternalRiskError("NaN/Infinity during sizing")
    return Decimal(math.floor(value))
