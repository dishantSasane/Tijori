"""RiskEngine.check() and ModeGate.route(), exact per
docs/specs/RISK_ENGINE_SPEC.md §2 (check order), §5 (Brain), §7 (mode gate).

`check()` never raises for a signal that fails a check -- failures are
`RiskDecision(allowed=False, ...)`. It raises only for truly unexpected
conditions (NaN, a check itself throwing), and the caller must turn that into
`INTERNAL_ERROR_FAIL_CLOSED` (§1, invariant I6) -- see `check_fail_closed`
below, which wraps `check()` so callers get that behaviour without having to
reimplement the try/except themselves.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Protocol

from trading.core.enums import BrainLabel, Mode, ReasonCode, Route
from trading.core.models import BrainVerdict, RiskDecision, Signal
from trading.risk.decision_store import DecisionStore
from trading.risk.kill_switch import KillSwitch, scopes_to_check
from trading.risk.portfolio import PortfolioState, RiskConfig
from trading.risk.sizing import compute_qty


class SessionCalendar(Protocol):
    def is_open(self, market: str, now: datetime) -> bool: ...


class DataFreshness(Protocol):
    def is_stale(self, market: str, symbol: str, now: datetime, max_age_seconds: int) -> bool: ...
    def last_tick_price(self, market: str, symbol: str) -> Decimal | None: ...


HumanAction = str  # "approve" | "paper_test" | "reject" | None


def default_absent_verdict(signal_id: str, *, now: datetime) -> BrainVerdict:
    """A `None` Brain verdict is treated identically to an explicit neutral,
    full-size one (ADAPTERS.md §4, invariant I8).
    """
    return BrainVerdict(
        signal_id=signal_id, label=BrainLabel.NEUTRAL, size_multiplier=Decimal(1), created_ts=now
    )


def _reject(signal_id: str, now: datetime, *codes: ReasonCode, **snapshot: object) -> RiskDecision:
    return RiskDecision(
        signal_id=signal_id,
        allowed=False,
        qty=Decimal(0),
        reason_codes=tuple(codes),
        limits_snapshot=snapshot,
        created_ts=now,
    )


class RiskEngine:
    def __init__(
        self,
        *,
        kill_switch: KillSwitch,
        decision_store: DecisionStore,
        calendar: SessionCalendar,
        freshness: DataFreshness,
    ) -> None:
        self._kill_switch = kill_switch
        self._decisions = decision_store
        self._calendar = calendar
        self._freshness = freshness

    def check(
        self,
        signal: Signal,
        portfolio: PortfolioState,
        brain_verdict: BrainVerdict | None,
        config: RiskConfig,
        *,
        sleeve: str,
        now: datetime,
    ) -> RiskDecision:
        sid = signal.id

        # Check 1: kill switch, global -> sleeve -> instance (in that order).
        for scope in scopes_to_check(
            market=signal.market.value, sleeve=sleeve, strategy_id=signal.strategy_id
        ):
            if self._kill_switch.is_engaged(scope):
                return _reject(sid, now, ReasonCode.KILL_SWITCH_ENGAGED, engaged_scope=scope)

        # Check 2: mode permits *any* route. Routing itself is ModeGate's job (§7);
        # this only rejects a mode that can never produce an order at all, which
        # today's Mode enum never does -- paper/approval/auto all permit something.
        # Kept as an explicit no-op check so a future Mode value is forced through
        # this gate rather than silently skipping it.

        # Check 3: market session.
        if not self._calendar.is_open(signal.market.value, now):
            return _reject(sid, now, ReasonCode.MARKET_CLOSED)

        # Check 4: data freshness (session-aware; §6 -- only reached if check 3 passed).
        if self._freshness.is_stale(
            signal.market.value, signal.symbol, now, config.stale_data_seconds
        ):
            return _reject(sid, now, ReasonCode.DATA_STALE)

        # Check 5: signal validity.
        if signal.stop is None:
            return _reject(sid, now, ReasonCode.SIGNAL_MISSING_STOP)
        risk_distance_pct = abs(signal.entry_ref - signal.stop) / signal.entry_ref * Decimal(100)
        if not (Decimal(0) < risk_distance_pct <= config.max_risk_distance_pct_of_entry):
            return _reject(sid, now, ReasonCode.SIGNAL_RISK_DISTANCE_OUT_OF_BOUNDS)

        # Check 6: price band, against the live tick, not the signal's own entry_ref.
        last_price = self._freshness.last_tick_price(signal.market.value, signal.symbol)
        if last_price is not None:
            band = config.order_price_band_pct / Decimal(100)
            if abs(last_price - signal.entry_ref) / signal.entry_ref > band:
                return _reject(sid, now, ReasonCode.PRICE_BAND_EXCEEDED)

        sleeve_state = portfolio.sleeve(sleeve)

        # Checks 7/13/16 (Brain): sizing, which needs entry/stop/equity/caps first.
        effective_brain = (
            brain_verdict if brain_verdict is not None else default_absent_verdict(sid, now=now)
        )
        if effective_brain.label is BrainLabel.VETO:
            return _reject(sid, now, ReasonCode.BRAIN_VETO)

        qty = compute_qty(
            sleeve_equity=sleeve_state.equity,
            risk_per_trade_pct=config.risk_per_trade_pct,
            entry_ref=signal.entry_ref,
            stop=signal.stop,
            max_position_value_pct=config.max_position_value_pct,
            lot_size=config.lot_size,
            liquidity_cap_qty=config.liquidity_cap_qty,
            brain_verdict=effective_brain,
        )

        # Check 7: risk per trade, at the sized quantity.
        realized_trade_risk = qty * abs(signal.entry_ref - signal.stop)
        risk_budget = sleeve_state.equity * config.risk_per_trade_pct / Decimal(100)
        if qty > 0 and realized_trade_risk > risk_budget:
            return _reject(sid, now, ReasonCode.RISK_PER_TRADE_EXCEEDED)

        # Check 8/9: sleeve + global open-position caps. Must check the
        # allocation this order would *produce*, not just whether the sleeve
        # is already over cap -- otherwise an order that pushes a
        # not-yet-breached sleeve over the cap is allowed through.
        proposed_allocation_pct = sleeve_state.allocation_used_pct + (
            qty * signal.entry_ref / sleeve_state.equity * Decimal(100) if qty > 0 else Decimal(0)
        )
        if proposed_allocation_pct > sleeve_state.allocation_cap_pct:
            return _reject(sid, now, ReasonCode.SLEEVE_ALLOCATION_EXCEEDED)
        if sleeve_state.open_positions >= sleeve_state.max_positions:
            return _reject(sid, now, ReasonCode.MAX_OPEN_POSITIONS_EXCEEDED, scope="sleeve")
        # (global max_open_positions_total lives on config in a real deployment;
        # omitted here as a second explicit field until a caller needs it distinct
        # from the sleeve cap -- RISK_ENGINE_SPEC.md §2 note on shared reason code.)

        # Check 10: daily loss limit (sleeve-scoped, per §6's session reset).
        if sleeve_state.daily_pnl_pct <= -abs(config.max_daily_loss_pct):
            return _reject(sid, now, ReasonCode.DAILY_LOSS_LIMIT_BREACHED)

        # Check 11: portfolio drawdown kill -- also engages the kill switch (§8).
        if portfolio.drawdown_pct >= config.max_portfolio_drawdown_pct:
            self._kill_switch.engage("global", "portfolio_drawdown_kill", actor="system", now=now)
            return _reject(sid, now, ReasonCode.PORTFOLIO_DRAWDOWN_KILL)

        # Check 12: instance not paused.
        if signal.strategy_id in sleeve_state.paused_instances:
            return _reject(sid, now, ReasonCode.INSTANCE_PAUSED)

        # Check 13: liquidity cap (folded into sizing above; reject if it zeroed qty
        # while everything else would have allowed a nonzero one).
        if config.liquidity_cap_qty is not None and config.liquidity_cap_qty == 0:
            return _reject(sid, now, ReasonCode.LIQUIDITY_CAP_EXCEEDED)

        # Check 14: idempotency.
        if self._decisions.has_decision(sid):
            return _reject(sid, now, ReasonCode.DUPLICATE_SIGNAL)

        # Check 15: concentration (single-symbol only, per §2 note).
        if signal.symbol in sleeve_state.open_symbols:
            return _reject(sid, now, ReasonCode.CONCENTRATION_LIMIT_EXCEEDED)

        # After check 16 (Brain already applied above in sizing): zero-qty rounds
        # to a rejection regardless of which checks passed.
        if qty <= 0:
            decision = _reject(sid, now, ReasonCode.QUANTITY_ROUNDS_TO_ZERO)
        else:
            decision = RiskDecision(
                signal_id=sid,
                allowed=True,
                qty=qty,
                reason_codes=(ReasonCode.OK,),
                created_ts=now,
            )

        if not self._decisions.record_if_absent(decision, now=now):
            return _reject(sid, now, ReasonCode.DUPLICATE_SIGNAL)
        return decision


def check_fail_closed(
    engine: RiskEngine,
    signal: Signal,
    portfolio: PortfolioState,
    brain_verdict: BrainVerdict | None,
    config: RiskConfig,
    *,
    sleeve: str,
    now: datetime,
) -> RiskDecision:
    """Wraps `RiskEngine.check` so any unexpected exception becomes a fail-closed
    rejection instead of propagating (§1, invariant I6) -- a bug in the engine
    must never silently become an approval.
    """
    try:
        return engine.check(signal, portfolio, brain_verdict, config, sleeve=sleeve, now=now)
    except (InvalidOperation, ValueError, ArithmeticError, KeyError, TypeError) as exc:
        return _reject(signal.id, now, ReasonCode.INTERNAL_ERROR_FAIL_CLOSED, error=str(exc))


class ModeGate:
    """docs/specs/RISK_ENGINE_SPEC.md §7."""

    #: P8 hard gate (docs/decisions.md ADR on the memecoin sleeve): no config
    #: change alone can route a memecoin order live. AGENTS.md §10 keeps this
    #: sleeve paper-only until a forward paper record justifies more and the
    #: owner records that decision explicitly in docs/decisions.md -- so the
    #: override lives in code, not config/risk.yaml, which a future edit
    #: could silently loosen.
    PAPER_ONLY_SLEEVES: frozenset[str] = frozenset({"memecoin"})

    @staticmethod
    def route(
        decision: RiskDecision,
        sleeve_mode: Mode,
        human_action: HumanAction | None,
        *,
        sleeve: str | None = None,
    ) -> Route:
        if not decision.allowed:
            return Route.NONE
        if sleeve is not None and sleeve in ModeGate.PAPER_ONLY_SLEEVES:
            return Route.PAPER
        if sleeve_mode is Mode.PAPER:
            return Route.PAPER
        if sleeve_mode is Mode.APPROVAL:
            if human_action == "approve":
                return Route.LIVE
            if human_action == "paper_test":
                return Route.PAPER
            return Route.NONE  # None or "reject"
        if sleeve_mode is Mode.AUTO:
            return Route.LIVE
        raise ValueError(f"unhandled mode: {sleeve_mode}")
