"""Pydantic v2 contracts shared across every module. See docs/specs/CONTRACTS.md.

Rules (AGENTS.md §6): money/price/quantity on order paths use `Decimal`, never
`float`. All timestamps are timezone-aware UTC; conversion to market-local
time happens only at the edges (dashboard, Telegram).
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from trading.core.enums import (
    BrainLabel,
    LedgerSource,
    MarketId,
    OrderSide,
    OrderStatus,
    OutcomeResult,
    ReasonCode,
    Timeframe,
)


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _new_id() -> str:
    return str(uuid4())


class Contract(BaseModel):
    """Base for all contracts: immutable, extra fields rejected."""

    model_config = ConfigDict(frozen=True, extra="forbid", validate_assignment=True)

    @field_validator("*", mode="before")
    @classmethod
    def _reject_naive_datetimes(cls, value: Any) -> Any:
        if isinstance(value, datetime) and value.tzinfo is None:
            raise ValueError("datetimes must be timezone-aware (UTC)")
        return value


class Candle(Contract):
    """A closed bar. Signals are generated only on closed candles (AGENTS.md §4.5)."""

    market: MarketId
    symbol: str
    timeframe: Timeframe
    ts_open_utc: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal = Field(ge=0)
    source: str
    ingest_ts: datetime = Field(default_factory=_utc_now)
    adj_factor: Decimal | None = None

    @model_validator(mode="after")
    def _check_ohlc(self) -> Candle:
        if self.high < self.low:
            raise ValueError("high < low")
        if not (self.low <= self.open <= self.high):
            raise ValueError("open outside [low, high]")
        if not (self.low <= self.close <= self.high):
            raise ValueError("close outside [low, high]")
        return self


class Tick(Contract):
    """Raw trade/quote tick. Never persisted long-term (rolling debug buffer only)."""

    market: MarketId
    symbol: str
    ts_utc: datetime
    price: Decimal = Field(gt=0)
    size: Decimal = Field(ge=0)


class Signal(Contract):
    """Output of a strategy on a closed bar. Entry/target/stop must all be present
    before this reaches the risk engine (a missing stop is rejected there, not here,
    so the reason code is auditable — see ReasonCode.SIGNAL_MISSING_STOP).
    """

    id: str = Field(default_factory=_new_id)
    market: MarketId
    symbol: str
    timeframe: Timeframe
    strategy_id: str
    strategy_version: str
    side: OrderSide
    entry_ref: Decimal = Field(gt=0)
    stop: Decimal | None = Field(default=None, gt=0)
    target: Decimal | None = Field(default=None, gt=0)
    bar_ts_utc: datetime
    created_ts: datetime = Field(default_factory=_utc_now)
    reason_codes: tuple[str, ...] = ()

    @model_validator(mode="after")
    def _check_stop_side(self) -> Signal:
        if self.stop is None:
            return self
        if self.side is OrderSide.BUY and self.stop >= self.entry_ref:
            raise ValueError("buy signal stop must be below entry_ref")
        if self.side is OrderSide.SELL and self.stop <= self.entry_ref:
            raise ValueError("sell signal stop must be above entry_ref")
        return self


class OrderRequest(Contract):
    """What the execution layer asks the risk engine to approve."""

    id: str = Field(default_factory=_new_id)
    signal_id: str
    market: MarketId
    symbol: str
    side: OrderSide
    qty: Decimal = Field(gt=0)
    limit_price: Decimal | None = Field(default=None, gt=0)
    stop_price: Decimal | None = Field(default=None, gt=0)
    idempotency_key: str
    created_ts: datetime = Field(default_factory=_utc_now)


class Order(Contract):
    """An order as tracked through its state machine (docs/RISK_SPEC.md §6)."""

    id: str = Field(default_factory=_new_id)
    request_id: str
    status: OrderStatus
    broker_order_id: str | None = None
    qty: Decimal = Field(gt=0)
    qty_filled: Decimal = Field(default=Decimal(0), ge=0)
    avg_fill_price: Decimal | None = Field(default=None, gt=0)
    created_ts: datetime = Field(default_factory=_utc_now)
    updated_ts: datetime = Field(default_factory=_utc_now)

    @model_validator(mode="after")
    def _check_fill_not_over_qty(self) -> Order:
        if self.qty_filled > self.qty:
            raise ValueError("qty_filled exceeds qty (invariant I3)")
        return self


class Fill(Contract):
    id: str = Field(default_factory=_new_id)
    order_id: str
    ts_utc: datetime
    qty: Decimal = Field(gt=0)
    price: Decimal = Field(gt=0)
    fees: Decimal = Field(default=Decimal(0), ge=0)
    ledger_source: LedgerSource


class Position(Contract):
    market: MarketId
    symbol: str
    sleeve: str
    qty: Decimal
    avg_price: Decimal = Field(ge=0)
    opened_ts: datetime
    stop_price: Decimal | None = Field(default=None, gt=0)


class RiskDecision(Contract):
    """RiskEngine.check() output. Every decision is written to the audit log
    with reason codes, approved or not (invariant I11).
    """

    signal_id: str
    allowed: bool
    qty: Decimal = Field(ge=0)
    reason_codes: tuple[ReasonCode, ...] = Field(min_length=1)
    limits_snapshot: dict[str, Any] = Field(default_factory=dict)
    created_ts: datetime = Field(default_factory=_utc_now)

    @model_validator(mode="after")
    def _check_consistency(self) -> RiskDecision:
        if self.allowed and self.qty <= 0:
            raise ValueError("an allowed decision must carry qty > 0 (invariant I9)")
        if not self.allowed and self.qty != 0:
            raise ValueError("a rejected decision must carry qty == 0")
        return self


class BrainVerdict(Contract):
    """The Brain's output: can only support, stay neutral, veto, or shrink size
    (ADR-0008). Never increases risk; invalid output is treated as absent (I8).
    """

    signal_id: str
    label: BrainLabel
    size_multiplier: Decimal = Field(ge=0, le=1)
    reasons: tuple[str, ...] = ()
    created_ts: datetime = Field(default_factory=_utc_now)


class SignalOutcome(Contract):
    signal_id: str
    result: OutcomeResult
    pct_after_costs: Decimal | None = None
    bars_held: int | None = Field(default=None, ge=0)
    closed_ts: datetime | None = None


class AuditEvent(Contract):
    """One row per order, risk decision, mode change, or LLM call (AGENTS.md §6)."""

    id: str = Field(default_factory=_new_id)
    ts_utc: datetime = Field(default_factory=_utc_now)
    event_type: str
    actor: str
    payload: dict[str, Any] = Field(default_factory=dict)
