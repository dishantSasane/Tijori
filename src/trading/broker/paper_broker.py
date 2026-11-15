"""Live paper broker: docs/specs/PAPER_BROKER_SPEC.md.

Reuses `trading.backtest.fills` for the fill/slippage/stop math (§3 -- paper
and backtest must never silently diverge on costs). This module adds what
the backtester doesn't need: waiting for the next *live* closed candle
instead of indexing into a stored array, SQLite persistence (§4, I12),
session-end expiry (§2.1), and shadow/rejected outcome tracking (§5).

Single open position per `(market, symbol, sleeve)`, same convention as
`trading.backtest.runner`.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from trading.backtest.fills import BacktestProfile, fill_at_next_open, stop_exit
from trading.backtest.fills import Position as FillPosition
from trading.core.enums import ExitReason, LedgerSource, MarketId, OrderSide, OutcomeResult
from trading.core.models import ExitRequest, Position, Signal
from trading.risk.audit import AuditLog


@dataclass(frozen=True)
class PendingSignal:
    signal_id: str
    market: str
    symbol: str
    sleeve: str
    side: OrderSide
    qty: Decimal
    entry_ref: Decimal
    stop: Decimal
    target: Decimal | None
    formed_ts: datetime
    ledger_source: LedgerSource


@dataclass(frozen=True)
class OpenPosition:
    market: str
    symbol: str
    sleeve: str
    signal_id: str
    qty: Decimal
    avg_price: Decimal
    opened_ts: datetime
    stop_price: Decimal
    target_price: Decimal | None
    entry_ref: Decimal
    approved_risk: Decimal
    ledger_source: LedgerSource

    @property
    def position_id(self) -> str:
        """Stable, broker-truth-derived identity for `ExitRequest.position_id`
        -- never a fresh UUID per call, so the same open position always
        resolves to the same id across restarts (matches how it's keyed in
        the `positions` table).
        """
        return f"{self.market}:{self.symbol}:{self.sleeve}"


class PaperBroker:
    def __init__(
        self, conn: sqlite3.Connection, audit: AuditLog, *, profile: BacktestProfile
    ) -> None:
        self._conn = conn
        self._audit = audit
        self._profile = profile

    # -- accepting a risk-approved (or shadow) signal -------------------------

    def accept(
        self,
        signal: Signal,
        *,
        qty: Decimal,
        sleeve: str,
        ledger_source: LedgerSource,
        now: datetime,
    ) -> None:
        """A signal formed on `signal.bar_ts_utc`; no fill is possible yet
        (§2 step 1) -- it only enters `pending_fills`, waiting for the next
        closed candle for this symbol.
        """
        if signal.stop is None:
            raise ValueError("a signal reaching the paper broker must carry a stop")
        pending = PendingSignal(
            signal_id=signal.id,
            market=signal.market.value,
            symbol=signal.symbol,
            sleeve=sleeve,
            side=signal.side,
            qty=qty,
            entry_ref=signal.entry_ref,
            stop=signal.stop,
            target=signal.target,
            formed_ts=signal.bar_ts_utc,
            ledger_source=ledger_source,
        )
        self._conn.execute(
            "INSERT INTO pending_fills (signal_id, request_json, formed_ts, expires_session_id) "
            "VALUES (?, ?, ?, NULL)",
            (
                pending.signal_id,
                json.dumps(_pending_to_dict(pending)),
                pending.formed_ts.isoformat(),
            ),
        )
        self._conn.commit()
        self._audit.write(
            ts_utc=now,
            event_type="signal_accepted_pending_fill",
            actor="system",
            payload={"signal_id": signal.id, "ledger_source": ledger_source.value},
        )

    # -- restart reconstruction (§4) ------------------------------------------

    def pending_signals(self) -> list[PendingSignal]:
        rows = self._conn.execute("SELECT request_json FROM pending_fills").fetchall()
        return [_pending_from_dict(json.loads(r[0])) for r in rows]

    def open_positions(self) -> list[OpenPosition]:
        rows = self._conn.execute(
            "SELECT market, symbol, sleeve, signal_id, qty, avg_price, opened_ts, stop_price, "
            "target_price, entry_ref, approved_risk, ledger_source FROM positions"
        ).fetchall()
        return [
            OpenPosition(
                market=r[0],
                symbol=r[1],
                sleeve=r[2],
                signal_id=r[3],
                qty=Decimal(r[4]),
                avg_price=Decimal(r[5]),
                opened_ts=datetime.fromisoformat(r[6]),
                stop_price=Decimal(r[7]),
                target_price=Decimal(r[8]) if r[8] else None,
                entry_ref=Decimal(r[9]),
                approved_risk=Decimal(r[10]),
                ledger_source=LedgerSource(r[11]),
            )
            for r in rows
        ]

    # -- driving fills off newly closed candles (§2) --------------------------

    def on_candle(
        self,
        *,
        market: str,
        symbol: str,
        ts_open_utc: datetime,
        open_: Decimal,
        high: Decimal,
        low: Decimal,
        now: datetime,
    ) -> None:
        self._try_fill_entries(market, symbol, ts_open_utc, open_, now)
        self._try_exit_open_position(market, symbol, ts_open_utc, open_, high, low, now)

    def _try_fill_entries(
        self, market: str, symbol: str, ts_open_utc: datetime, open_: Decimal, now: datetime
    ) -> None:
        # `positions`' primary key is (market, symbol, sleeve) -- a second
        # pending entry for a sleeve that already holds (or just filled) this
        # (market, symbol) would otherwise crash on that constraint. Track
        # occupied sleeves locally and reject duplicates atomically instead.
        occupied_sleeves = {
            pos.sleeve
            for pos in self.open_positions()
            if pos.market == market and pos.symbol == symbol
        }
        for pending in self.pending_signals():
            if pending.market != market or pending.symbol != symbol:
                continue
            if ts_open_utc <= pending.formed_ts:
                continue  # this candle is not strictly after the signal's own bar yet
            if pending.sleeve in occupied_sleeves:
                self._audit.write(
                    ts_utc=now,
                    event_type="entry_rejected_duplicate_sleeve_position",
                    actor="system",
                    payload={
                        "signal_id": pending.signal_id,
                        "market": market,
                        "symbol": symbol,
                        "sleeve": pending.sleeve,
                    },
                )
                continue
            occupied_sleeves.add(pending.sleeve)
            fill = fill_at_next_open(
                open_, side=pending.side.value, quantity=pending.qty, profile=self._profile
            )
            approved_risk = pending.qty * abs(pending.entry_ref - pending.stop)
            self._conn.execute(
                "INSERT INTO positions (market, symbol, sleeve, signal_id, qty, avg_price, "
                "opened_ts, "
                "stop_price, target_price, entry_ref, approved_risk, ledger_source) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    market,
                    symbol,
                    pending.sleeve,
                    pending.signal_id,
                    str(fill.quantity),
                    str(fill.price),
                    ts_open_utc.isoformat(),
                    str(pending.stop),
                    str(pending.target) if pending.target else None,
                    str(pending.entry_ref),
                    str(approved_risk),
                    pending.ledger_source.value,
                ),
            )
            self._conn.execute(
                "DELETE FROM pending_fills WHERE signal_id = ?", (pending.signal_id,)
            )
            self._conn.execute(
                "INSERT INTO fills (id, order_id, qty, price, fees, ledger_source, ts_utc) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    f"{pending.signal_id}:entry",
                    pending.signal_id,
                    str(fill.quantity),
                    str(fill.price),
                    str(fill.fees),
                    pending.ledger_source.value,
                    now.isoformat(),
                ),
            )
            self._conn.commit()
            self._audit.write(
                ts_utc=now,
                event_type="entry_filled",
                actor="system",
                payload={
                    "signal_id": pending.signal_id,
                    "market": market,
                    "symbol": symbol,
                    "sleeve": pending.sleeve,
                    "qty": str(fill.quantity),
                    "price": str(fill.price),
                },
            )

    def _try_exit_open_position(
        self,
        market: str,
        symbol: str,
        ts_open_utc: datetime,
        open_: Decimal,
        high: Decimal,
        low: Decimal,
        now: datetime,
    ) -> None:
        for pos in self.open_positions():
            if pos.market != market or pos.symbol != symbol:
                continue
            fp = FillPosition(quantity=pos.qty, entry_price=pos.avg_price, stop=pos.stop_price)
            exit_fill = stop_exit(fp, open_price=open_, high=high, low=low, profile=self._profile)
            if exit_fill is not None:
                self._close_position(
                    pos,
                    exit_fill.price,
                    exit_fill.fees,
                    OutcomeResult.STOP_HIT,
                    ExitReason.STOP,
                    ts_open_utc,
                    now,
                )
                if exit_fill.gap_through_stop:
                    realized_risk = pos.qty * abs(exit_fill.price - pos.entry_ref)
                    self._audit.write(
                        ts_utc=now,
                        event_type="gap_risk_realized",
                        actor="system",
                        payload={
                            "approved_risk": str(pos.approved_risk),
                            "realized_risk": str(realized_risk),
                        },
                    )
                continue
            # Target check against the candle's high (PAPER_BROKER_SPEC.md §2.4:
            # stop/target exits evaluated against every closed candle, same
            # stop-first-on-the-fill-bar precedence as the backtester). Stop
            # precedence is structural: stop_exit() above already fires and
            # `continue`s on any stop touch this candle, so target is only
            # ever checked when the candle did NOT touch the stop.
            if pos.target_price is not None and high >= pos.target_price:
                fill_price = open_ if open_ >= pos.target_price else pos.target_price
                self._close_position(
                    pos,
                    fill_price,
                    self._profile.exit_fee,
                    OutcomeResult.TARGET_HIT,
                    ExitReason.TARGET,
                    ts_open_utc,
                    now,
                )

    def build_exit_request(
        self, pos: OpenPosition, reason: ExitReason, bar_ts_utc: datetime, now: datetime
    ) -> ExitRequest:
        """The canonical, I14-enforced exit path (docs/specs/RISK_ENGINE_SPEC.md
        §11 I14; `CONTRACTS.md`'s `ExitRequest`) -- the same path live/
        approval-mode exits use, not a paper-only shortcut. `exit_id` is
        derived (never caller-supplied), so a duplicate exit for the same
        position/reason/bar is always idempotent (I7) before it ever reaches
        SQL.
        """
        return ExitRequest(
            position_id=pos.position_id,
            quantity=pos.qty,
            reason_code=reason,
            bar_ts_utc=bar_ts_utc,
            created_ts=now,
        )

    def _close_position(
        self,
        pos: OpenPosition,
        price: Decimal,
        fees: Decimal,
        result: OutcomeResult,
        reason: ExitReason,
        bar_ts_utc: datetime,
        now: datetime,
    ) -> None:
        exit_request = self.build_exit_request(pos, reason, bar_ts_utc, now)

        # Idempotency (I7): a duplicate exit_id for the same position/reason/
        # bar is a no-op, never a second fill -- checked via the same
        # atomic INSERT-if-absent pattern as DecisionStore (risk/decision_store.py).
        cur = self._conn.execute(
            "INSERT INTO exit_requests (exit_id, position_id, reason_code, quantity, applied_ts) "
            "SELECT ?, ?, ?, ?, ? WHERE NOT EXISTS "
            "(SELECT 1 FROM exit_requests WHERE exit_id = ?)",
            (
                exit_request.exit_id,
                exit_request.position_id,
                reason.value,
                str(exit_request.quantity),
                now.isoformat(),
                exit_request.exit_id,
            ),
        )
        if cur.rowcount == 0:
            self._conn.commit()
            self._audit.write(
                ts_utc=now,
                event_type="exit_already_applied",
                actor="system",
                payload={"exit_id": exit_request.exit_id, "position_id": pos.position_id},
            )
            return

        # I14 enforcement: apply_to_position raises if the request would
        # increase the position or exceed its open quantity -- this is the
        # same validation `ExitRequest.apply_to_position` runs for a live or
        # approval-mode exit, not a paper-only shortcut. A full close drives
        # the remaining quantity to exactly zero, never negative.
        broker_truth_position = Position(
            market=MarketId(pos.market),
            symbol=pos.symbol,
            sleeve=pos.sleeve,
            qty=pos.qty,
            avg_price=pos.avg_price,
            opened_ts=pos.opened_ts,
            stop_price=pos.stop_price,
        )
        remaining = exit_request.apply_to_position(broker_truth_position)
        if remaining.qty != 0:
            raise ValueError(
                "PaperBroker only supports full-position closes; a partial "
                f"ExitRequest left qty={remaining.qty} (invariant I14 held, "
                "but this broker's position model doesn't support partials yet)"
            )

        self._conn.execute(
            "DELETE FROM positions WHERE market = ? AND symbol = ? AND sleeve = ?",
            (pos.market, pos.symbol, pos.sleeve),
        )
        self._conn.execute(
            "INSERT INTO fills (id, order_id, qty, price, fees, ledger_source, ts_utc) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                exit_request.exit_id,
                pos.signal_id,
                str(pos.qty),
                str(price),
                str(fees),
                pos.ledger_source.value,
                now.isoformat(),
            ),
        )
        pct = (price - pos.entry_ref) / pos.entry_ref * Decimal(100)
        self._record_outcome(pos.signal_id, result, pct, now, pos.ledger_source)
        self._conn.commit()
        self._audit.write(
            ts_utc=now,
            event_type="position_closed",
            actor="system",
            payload={
                "signal_id": pos.signal_id,
                "exit_id": exit_request.exit_id,
                "market": pos.market,
                "symbol": pos.symbol,
                "sleeve": pos.sleeve,
                "result": result.value,
                "price": str(price),
            },
        )

    # -- timeout / expiry (§2.1) ----------------------------------------------

    def expire_session(self, *, market: str, now: datetime) -> list[str]:
        """Any `pending_fills` row for `market` not yet filled when the
        session ends expires unfilled -- removed, audited, never carried to
        the next session silently.
        """
        expired = [p for p in self.pending_signals() if p.market == market]
        for pending in expired:
            self._conn.execute(
                "DELETE FROM pending_fills WHERE signal_id = ?", (pending.signal_id,)
            )
            # Preserve the signal's own ledger_source -- a pending signal
            # accepted as a normal paper record must never be written as a
            # shadow result just because it expired unfilled.
            self._record_outcome(
                pending.signal_id,
                OutcomeResult.SESSION_ENDED_UNFILLED,
                None,
                now,
                pending.ledger_source,
            )
            self._audit.write(
                ts_utc=now,
                event_type="session_ended_unfilled",
                actor="system",
                payload={"signal_id": pending.signal_id},
            )
        self._conn.commit()
        return [p.signal_id for p in expired]

    # -- shadow/rejected outcome tracker (§5) ---------------------------------

    def _record_outcome(
        self,
        signal_id: str,
        result: OutcomeResult,
        pct: Decimal | None,
        now: datetime,
        ledger_source: LedgerSource,
    ) -> None:
        self._conn.execute(
            "INSERT INTO signal_outcomes (signal_id, result, pct_after_costs, bars_held, "
            "closed_ts, ledger_source) "
            "VALUES (?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(signal_id) DO UPDATE SET result=excluded.result, "
            "pct_after_costs=excluded.pct_after_costs, "
            "closed_ts=excluded.closed_ts",
            (
                signal_id,
                result.value,
                str(pct) if pct is not None else None,
                None,
                now.isoformat(),
                ledger_source.value,
            ),
        )
        self._conn.commit()

    @property
    def audit(self) -> AuditLog:
        return self._audit

    def outcome(self, signal_id: str) -> OutcomeResult | None:
        row = self._conn.execute(
            "SELECT result FROM signal_outcomes WHERE signal_id = ?", (signal_id,)
        ).fetchone()
        return OutcomeResult(row[0]) if row else None

    def outcome_ledger_source(self, signal_id: str) -> LedgerSource | None:
        row = self._conn.execute(
            "SELECT ledger_source FROM signal_outcomes WHERE signal_id = ?", (signal_id,)
        ).fetchone()
        return LedgerSource(row[0]) if row else None

    # -- kill-switch integration: cancel pending entries, keep stops live ----

    def cancel_all_pending_entries(self, *, reason: str, now: datetime) -> list[str]:
        """Step 3 of the kill-switch drill: cancel pending *entry* orders.
        Protective stops on already-open positions are untouched -- they are
        not entries and remain live (RISK_SPEC.md §4's carve-out).
        """
        cancelled = [p.signal_id for p in self.pending_signals()]
        for signal_id in cancelled:
            self._conn.execute("DELETE FROM pending_fills WHERE signal_id = ?", (signal_id,))
            self._audit.write(
                ts_utc=now,
                event_type="pending_entry_cancelled",
                actor="system",
                payload={"signal_id": signal_id, "reason": reason},
            )
        self._conn.commit()
        return cancelled


def _pending_to_dict(p: PendingSignal) -> dict[str, str | None]:
    return {
        "signal_id": p.signal_id,
        "market": p.market,
        "symbol": p.symbol,
        "sleeve": p.sleeve,
        "side": p.side.value,
        "qty": str(p.qty),
        "entry_ref": str(p.entry_ref),
        "stop": str(p.stop),
        "target": str(p.target) if p.target is not None else None,
        "formed_ts": p.formed_ts.isoformat(),
        "ledger_source": p.ledger_source.value,
    }


def _pending_from_dict(d: dict[str, Any]) -> PendingSignal:
    return PendingSignal(
        signal_id=d["signal_id"],
        market=d["market"],
        symbol=d["symbol"],
        sleeve=d["sleeve"],
        side=OrderSide(d["side"]),
        qty=Decimal(d["qty"]),
        entry_ref=Decimal(d["entry_ref"]),
        stop=Decimal(d["stop"]),
        target=Decimal(d["target"]) if d["target"] is not None else None,
        formed_ts=datetime.fromisoformat(d["formed_ts"]),
        ledger_source=LedgerSource(d["ledger_source"]),
    )
