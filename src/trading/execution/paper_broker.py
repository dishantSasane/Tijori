"""PaperBroker: the real (cost/slippage-modelled) paper broker (P2).

docs/specs/PAPER_BROKER_SPEC.md. Never touches a real exchange (I1) — it has
no code path to a real adapter at all, which is stronger than "checks a
config flag." Fills happen on the first newly-closed candle after the
signal's own candle (§2), reusing `trading.backtest.fills` so paper and
backtest can never silently diverge (§3, §6 non-goals).

`FakePaperBroker` in `trading/adapters/broker.py` fills instantly at zero
cost and is explicitly NOT this spec (PAPER_BROKER_SPEC.md §1) — it exists
only for Protocol/state-machine contract tests.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import uuid4

from trading.backtest.fills import BacktestProfile, fill_at_next_open, stop_exit
from trading.backtest.fills import Position as FillPosition
from trading.core.clock import Clock
from trading.core.enums import LedgerSource, OrderSide, OrderStatus
from trading.core.models import Candle, Order, OrderRequest, RiskDecision, Signal
from trading.risk.kill_switch import GLOBAL_SCOPE, KillSwitch, sleeve_scope
from trading.storage.state_store import StateStore


class PaperBrokerHaltedError(RuntimeError):
    """Raised when a caller tries to submit a new entry while a kill switch
    (global or this sleeve) is engaged — fail closed, never silently ignore.
    """


@dataclass(frozen=True)
class PendingEntry:
    signal: Signal
    qty: Decimal
    side: OrderSide
    profile: BacktestProfile
    order_id: str


class PaperBroker:
    """One instance per process; state lives in `StateStore` (SQLite), so a
    fresh instance against the same file reconstructs it (I12's reduced form
    for paper trading, PAPER_BROKER_SPEC.md §4).
    """

    def __init__(self, store: StateStore, kill_switch: KillSwitch, *, clock: Clock) -> None:
        self._store = store
        self._kill_switch = kill_switch
        self._clock = clock

    def is_paper(self) -> bool:
        return True

    def submit_entry(
        self, signal: Signal, decision: RiskDecision, *, profile: BacktestProfile
    ) -> Order:
        """Accept a risk-approved signal as a pending entry. Never called with
        decision.allowed=False by a correct caller (I2) — defends anyway.
        """
        if not decision.allowed:
            raise ValueError("cannot submit entry for a rejected RiskDecision (I2)")
        scope_engaged = self._kill_switch.is_engaged(GLOBAL_SCOPE) or self._kill_switch.is_engaged(
            sleeve_scope(signal.market.value)
        )
        if scope_engaged:
            raise PaperBrokerHaltedError("kill switch engaged: no new entries (I6)")

        now = self._clock.now()
        order_id = decision.signal_id  # idempotency key == signal id (I7)
        request = OrderRequest(
            id=order_id,
            signal_id=signal.id,
            market=signal.market,
            symbol=signal.symbol,
            side=signal.side,
            qty=decision.qty,
            idempotency_key=signal.id,
            created_ts=now,
        )
        self._store.upsert_order(
            order_id,
            OrderStatus.RISK_APPROVED.value,
            request.model_dump(mode="json"),
            created_ts=now,
            updated_ts=now,
        )
        self._store.add_pending_fill(
            signal.id,
            {
                "order_id": order_id,
                "qty": str(decision.qty),
                "side": signal.side.value,
                "stop": str(signal.stop) if signal.stop else None,
                "entry_ref": str(signal.entry_ref),
                "market": signal.market.value,
                "symbol": signal.symbol,
                "sleeve": signal.market.value,
                "brokerage": str(profile.brokerage),
                "slippage_bps": str(profile.slippage_bps),
            },
            now,
            None,
        )
        self._store.write_audit(
            event_type="order_routed",
            actor="paper_broker",
            payload={"signal_id": signal.id, "order_id": order_id, "qty": str(decision.qty)},
            ts=now,
        )
        return Order(
            id=order_id,
            request_id=order_id,
            status=OrderStatus.RISK_APPROVED,
            qty=decision.qty,
            created_ts=now,
            updated_ts=now,
        )

    def cancel_pending_entries(self, sleeve_or_global: str, *, reason: str) -> list[str]:
        """Used by the kill-switch drill: cancel every still-pending entry order
        in scope. Protective stops (already-open positions) are untouched —
        this method never looks at `positions`.
        """
        now = self._clock.now()
        cancelled: list[str] = []
        for signal_id in list(self._store.pending_fill_ids()):
            self._store.pop_pending_fill(signal_id)
            self._store.upsert_order(
                signal_id, OrderStatus.CANCELLED.value, {}, created_ts=now, updated_ts=now
            )
            cancelled.append(signal_id)
        if cancelled:
            self._store.write_audit(
                event_type="orders_cancelled_kill_switch",
                actor="paper_broker",
                payload={"scope": sleeve_or_global, "reason": reason, "order_ids": cancelled},
                ts=now,
            )
        return cancelled

    def on_closed_candle(self, candle: Candle) -> None:
        """Advance the fill model one closed candle (§2, §2.4). Processes
        pending entries first (fill at this open), then checks existing
        positions for stop hits (gap-through-stop per RISK_SPEC.md §9).
        """
        import json

        now = self._clock.now()
        for signal_id in list(self._store.pending_fill_ids()):
            raw = self._store._conn.execute(  # noqa: SLF001 - intentional, no public getter needed yet
                "SELECT request_json FROM pending_fills WHERE signal_id=?", (signal_id,)
            ).fetchone()
            if raw is None:
                continue
            req = json.loads(raw[0])
            if req["market"] != candle.market.value or req["symbol"] != candle.symbol:
                continue
            side = req["side"]
            qty = Decimal(req["qty"])
            profile = BacktestProfile(
                brokerage=Decimal(req["brokerage"]), slippage_bps=Decimal(req["slippage_bps"])
            )
            fill = fill_at_next_open(candle.open, side=side, quantity=qty, profile=profile)
            self._store.pop_pending_fill(signal_id)
            self._store.upsert_order(
                req["order_id"], OrderStatus.FILLED.value, {}, created_ts=now, updated_ts=now
            )
            self._store.record_fill(
                str(uuid4()),
                req["order_id"],
                fill.quantity,
                fill.price,
                fill.fees,
                LedgerSource.USER_PAPER.value,
                now,
            )
            self._store.upsert_position(
                req["market"],
                req["symbol"],
                req["sleeve"],
                fill.quantity,
                fill.price,
                now,
                Decimal(req["stop"]) if req["stop"] else None,
            )

        for row in self._store.positions():
            if row["market"] != candle.market.value or row["symbol"] != candle.symbol:
                continue
            if row["stop_price"] is None:
                continue
            fp = FillPosition(
                quantity=Decimal(row["qty"]),
                entry_price=Decimal(row["avg_price"]),
                stop=Decimal(row["stop_price"]),
            )
            exit_fill = stop_exit(
                fp,
                open_price=candle.open,
                high=candle.high,
                low=candle.low,
                profile=BacktestProfile(),
            )
            if exit_fill is None:
                continue
            self._store.upsert_position(
                row["market"], row["symbol"], row["sleeve"], Decimal(0), Decimal(0), now, None
            )
            self._store.record_fill(
                str(uuid4()),
                f"{row['symbol']}-stop",
                exit_fill.quantity,
                exit_fill.price,
                exit_fill.fees,
                LedgerSource.USER_PAPER.value,
                now,
            )
            if exit_fill.gap_through_stop:
                approved_risk = fp.quantity * abs(fp.entry_price - fp.stop)
                realized_risk = fp.quantity * abs(exit_fill.price - fp.entry_price)
                self._store.write_audit(
                    event_type="gap_risk_realized",
                    actor="paper_broker",
                    payload={
                        "approved_risk": str(approved_risk),
                        "realized_risk": str(realized_risk),
                    },
                    ts=now,
                )
