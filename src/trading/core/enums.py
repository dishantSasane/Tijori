"""Enums shared across the whole system. See docs/specs/CONTRACTS.md."""

from __future__ import annotations

from enum import StrEnum


class MarketId(StrEnum):
    """One sleeve per value (docs/MARKETS.md)."""

    IN_EQUITY = "in_equity"
    US_EQUITY = "us_equity"
    CRYPTO = "crypto"
    MCX_COMMODITY = "mcx_commodity"
    NSE_CURRENCY = "nse_currency"
    IN_OPTIONS = "in_options"
    MEMECOIN = "memecoin"


class Mode(StrEnum):
    """Per-sleeve mode (AGENTS.md §4). Escalation requires an explicit human action."""

    PAPER = "paper"
    APPROVAL = "approval"
    AUTO = "auto"


class Timeframe(StrEnum):
    M1 = "1m"
    M5 = "5m"
    M15 = "15m"
    H1 = "1h"
    D1 = "1d"


class OrderSide(StrEnum):
    BUY = "buy"
    SELL = "sell"


class OrderStatus(StrEnum):
    """docs/RISK_SPEC.md §6 state machine."""

    CREATED = "created"
    RISK_APPROVED = "risk_approved"
    ROUTED = "routed"
    ACKNOWLEDGED = "acknowledged"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


#: Legal order-status transitions. Anything not listed here is illegal and must
#: raise + trigger fail-closed (docs/RISK_SPEC.md §6).
ORDER_STATUS_TRANSITIONS: dict[OrderStatus, frozenset[OrderStatus]] = {
    OrderStatus.CREATED: frozenset({OrderStatus.RISK_APPROVED, OrderStatus.REJECTED}),
    OrderStatus.RISK_APPROVED: frozenset({OrderStatus.ROUTED, OrderStatus.REJECTED}),
    OrderStatus.ROUTED: frozenset(
        {
            OrderStatus.ACKNOWLEDGED,
            OrderStatus.PARTIALLY_FILLED,
            OrderStatus.FILLED,
            OrderStatus.CANCELLED,
            OrderStatus.REJECTED,
            OrderStatus.EXPIRED,
        }
    ),
    OrderStatus.ACKNOWLEDGED: frozenset(
        {
            OrderStatus.PARTIALLY_FILLED,
            OrderStatus.FILLED,
            OrderStatus.CANCELLED,
            OrderStatus.EXPIRED,
        }
    ),
    OrderStatus.PARTIALLY_FILLED: frozenset(
        {OrderStatus.PARTIALLY_FILLED, OrderStatus.FILLED, OrderStatus.CANCELLED}
    ),
    OrderStatus.FILLED: frozenset(),
    OrderStatus.CANCELLED: frozenset(),
    OrderStatus.REJECTED: frozenset(),
    OrderStatus.EXPIRED: frozenset(),
}


class Route(StrEnum):
    """ModeGate.route() output (docs/RISK_SPEC.md §8)."""

    PAPER = "paper"
    LIVE = "live"
    NONE = "none"


class BrainLabel(StrEnum):
    """The Brain's output schema is tiny and can only reduce risk (ADR-0008)."""

    SUPPORT = "support"
    NEUTRAL = "neutral"
    VETO = "veto"


class OutcomeResult(StrEnum):
    TARGET_HIT = "target_hit"
    STOP_HIT = "stop_hit"
    TIMEOUT = "timeout"
    OPEN = "open"
    REJECTED_NOT_TRACKED = "rejected_not_tracked"


class LedgerSource(StrEnum):
    LIVE = "live"
    USER_PAPER = "user_paper"
    SHADOW = "shadow"


class ReasonCode(StrEnum):
    """Risk-decision reason codes. One per docs/RISK_SPEC.md §2 check (+ a few
    outcomes that aren't pre-trade checks). Extend by appending; never renumber
    or delete a value once it has shipped — audit history depends on it.
    """

    OK = "ok"
    KILL_SWITCH_ENGAGED = "kill_switch_engaged"
    MODE_DOES_NOT_PERMIT_ROUTE = "mode_does_not_permit_route"
    MARKET_CLOSED = "market_closed"
    DATA_STALE = "data_stale"
    SIGNAL_MISSING_STOP = "signal_missing_stop"
    SIGNAL_STOP_WRONG_SIDE = "signal_stop_wrong_side"
    SIGNAL_RISK_DISTANCE_OUT_OF_BOUNDS = "signal_risk_distance_out_of_bounds"
    PRICE_BAND_EXCEEDED = "price_band_exceeded"
    RISK_PER_TRADE_EXCEEDED = "risk_per_trade_exceeded"
    SLEEVE_ALLOCATION_EXCEEDED = "sleeve_allocation_exceeded"
    MAX_OPEN_POSITIONS_EXCEEDED = "max_open_positions_exceeded"
    DAILY_LOSS_LIMIT_BREACHED = "daily_loss_limit_breached"
    PORTFOLIO_DRAWDOWN_KILL = "portfolio_drawdown_kill"
    INSTANCE_PAUSED = "instance_paused"
    LIQUIDITY_CAP_EXCEEDED = "liquidity_cap_exceeded"
    DUPLICATE_SIGNAL = "duplicate_signal"
    CONCENTRATION_LIMIT_EXCEEDED = "concentration_limit_exceeded"
    BRAIN_VETO = "brain_veto"
    BRAIN_OUTPUT_INVALID = "brain_output_invalid"
    QUANTITY_ROUNDS_TO_ZERO = "quantity_rounds_to_zero"
    INTERNAL_ERROR_FAIL_CLOSED = "internal_error_fail_closed"
