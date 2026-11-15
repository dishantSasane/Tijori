# PAPER BROKER SPEC

Status: P2 deliverable (`docs/BUILD_ORDER.md`). Written ahead of P2 implementation
so Codex builds against a fixed contract, same discipline as `RISK_ENGINE_SPEC.md`
did for P1/P2. Extends `docs/specs/ADAPTERS.md` §2 (`Broker` Protocol) and
`docs/RISK_SPEC.md`. `FakePaperBroker` (`trading/adapters/broker.py`) fills
instantly at zero cost for Protocol/state-machine tests only — it is explicitly
not this spec, and must not be mistaken for it or reused as paper-trading
evidence.

## 1. Why a separate spec

The backtester's fill model (`TEST_SPEC_BACKTEST.md`) runs on a stored, already-closed
candle array: "next bar" is just an index lookup. The paper broker runs **live**,
against `DataFeed.poll_closed_candles()` (`ADAPTERS.md` §1), which deliberately
exposes no "current forming bar" accessor. The two engines must agree on *outcome*
for the same signal and candle sequence (same discipline as the backtester vs.
reference backtester equivalence gate), but the live paper broker additionally has
to define: what happens between polls, how state survives a process restart, and
how a rejected/shadow signal is scored without ever becoming a real order.

## 2. Fill model (paper and shadow; same rules)

1. A signal forms on a closed candle `C[t]`. No fill is possible yet — the paper
   broker (like the backtester) never fills on the signal's own candle.
2. The paper broker polls `DataFeed.poll_closed_candles()`. The **first newly
   closed candle after `C[t]`**, call it `C[t+1]`, is the fill candle. If the feed
   is stale past `stale_data_seconds` (`RISK_SPEC.md` check #4) before `C[t+1]`
   arrives, the order is not filled and expires per §2.1's timeout rule — it is
   never synthesized or backfilled from a later candle.
3. **Market/signal entry**: fills at `C[t+1].open`, slippage-adjusted against the
   trader: `execution_price = open * (1 - slippage_bps/10000)` for a buy,
   `open * (1 + slippage_bps/10000)` for a sell — identical sign convention to
   `trading/backtest/fills.py`. Fees: `profile.brokerage` flat per order plus any
   percentage charges in `config/markets.yaml` `costs`.
4. **Stop/target exits**: evaluated against every closed candle from `C[t+1]`
   onward, same stop-first-on-the-fill-bar precedence as the backtester
   (`TEST_SPEC_BACKTEST.md`). A gap through the stop fills at that candle's open,
   not the stop price, and emits `gap_risk_realized` exactly as specified in
   `RISK_SPEC.md` §7 — this is the one invariant that must never diverge between
   backtest and live, since it is the actual money-losing edge case.
5. **Condition exits** (T1/T2/T4/T6 style, no fixed target): re-evaluated once per
   newly closed candle, matching `STRATEGY_SPEC.md` §1.7.

### 2.1 Timeout / expiry

A signal not yet filled when its market session ends expires unfilled
(`STRATEGY_SPEC.md` §1.6) — it is removed from the pending-fill table (§4) with
reason code `SESSION_ENDED_UNFILLED` and audited. It is never carried over to
the next session silently.

## 3. Costs and slippage — source of truth

`config/markets.yaml` `<market>.costs` is the single source for both the
backtester and the paper broker. If the two ever read different cost fields,
that is a bug, not a feature — paper results are only meaningful if they used
the same cost assumptions a live order would.

## 4. State persistence (SQLite) — backs invariant I12

I12: "Position state after restart equals broker truth, or the engine refuses to
start trading." For the paper broker, the paper broker's own ledger *is* "broker
truth" (there is no external paper-broker API to reconcile against), so I12
reduces to: **on restart, in-memory state is reconstructed from SQLite, and
reconstruction must be exact or the engine halts new entries and alerts**.

Minimum tables (field names indicative, types per `docs/specs/CONTRACTS.md`):

| Table | Key columns | Purpose |
|---|---|---|
| `orders` | `id` (PK), `status`, `request_json`, `created_ts`, `updated_ts` | One row per `Order`; `status` only ever changes via `transition()` (`ADAPTERS.md` §2) — the SQLite write and the in-memory transition happen in the same unit of work, never one without the other |
| `fills` | `id` (PK), `order_id` (FK), `qty`, `price`, `fees`, `ledger_source`, `ts_utc` | Append-only; a `Fill` row is never updated or deleted, only inserted |
| `positions` | `(market, symbol, sleeve)` (PK), `qty`, `avg_price`, `opened_ts`, `stop_price` | Current open positions only; closed positions are derived from `fills`, not stored redundantly |
| `pending_fills` | `signal_id` (PK), `request_json`, `formed_ts`, `expires_session_id` | Orders accepted by risk but not yet filled (waiting for `C[t+1]`) — this table is what makes §2.1 expiry possible to implement without an in-memory-only timer that a restart would lose |
| `mode_state` | `scope` (PK: global/sleeve id), `mode`, `changed_by`, `changed_ts` | Backs I10 — every row is written only on an explicit human action, never inferred |
| `kill_switch_state` | `scope` (PK), `engaged`, `reason`, `engaged_ts`, `released_ts` | Backs I6; checked before every `place_order` call, read fresh each time, never cached across the check |
| `audit_log` | `id` (PK), `ts_utc`, `event_type`, `actor`, `payload_json` | One `AuditEvent` row per order/risk-decision/mode-change/LLM-call (AGENTS.md §6); this table is append-only and is the thing a restart replays to rebuild `positions`/`orders` if those tables were ever found inconsistent with it |

**Restart procedure**: load `orders`/`fills`/`positions`/`mode_state`/`kill_switch_state`
directly (fast path). Then replay `audit_log` since the last known-good checkpoint
and assert it produces the same `positions` — if it doesn't, fail closed (halt new
entries, alert) rather than trust either source silently. This dual-read is the
concrete test for I12, not a nice-to-have.

## 5. Outcome tracker (shadow and rejected signals)

Every signal that is **not** approved into a real/paper order — rejected by the
risk engine, or rejected by the human in `approval` mode — is still run through
the identical fill model in §2, tagged `ledger_source=shadow`
(`CONTRACTS.md` `Fill.ledger_source`), producing a `SignalOutcome`:

```
SignalOutcome(signal_id, result, pct_after_costs, bars_held, closed_ts)
```

- `result` is an `OutcomeResult` enum value (e.g. `TARGET_HIT`, `STOP_HIT`,
  `TIME_EXIT`, `SESSION_ENDED_UNFILLED` — same vocabulary as §2.1).
- `pct_after_costs` always includes the same cost model as §3 — a shadow outcome
  that ignores costs would overstate "you should have taken this" and is
  explicitly disallowed (this is what `RISK_ENGINE_SPEC.md` §7 calls out:
  `decision.allowed=False` never produces a fill of any *real* kind, but shadow
  scoring is exactly this tracked-but-never-ordered path and must stay
  cost-honest to be useful).
- This feeds the alert card's "Yours: you rejected 7 of 10; 5 of those 7 would
  have worked" line (`PAGES.md` §2) and the Paper ledger's rejected-signal
  outcomes — both read `SignalOutcome` rows, never recompute them ad hoc.
- A risk-engine rejection (`decision.allowed=False`) is still shadow-scored —
  shadow tracking is orthogonal to why a signal didn't become a real order, and
  exists precisely to answer "was the risk engine's caution justified?" over
  time, not just to second-guess human rejections.

## 6. Kill-switch drill (P2 exit criterion: "kill-switch drill executed in paper")

A concrete, repeatable procedure, not a one-off manual check:

1. Start the paper broker with at least one open position and one pending signal.
2. Engage the kill switch (manual: dashboard/Telegram command; automatic: force a
   configured trigger, e.g. simulate `max_daily_loss_pct` breach via a fixture).
3. Assert: zero new entry orders are accepted for any subsequent signal (I6);
   existing open entry orders are cancelled; existing protective stops remain
   live and can still fire (`RISK_SPEC.md` §4 — "protective exits remain
   allowed and may be triggered by the kill switch itself").
4. Assert: the engagement is in `kill_switch_state` and `audit_log` before step 3's
   assertions are checked — a kill switch that works in memory but isn't
   persisted doesn't survive the next restart, which defeats the point.
5. Release the kill switch via an explicit human action; assert new entries resume
   and the release is itself audited (I10 — escalation only by explicit human
   action).
6. Repeat with the process restarted between steps 2 and 3, to prove the kill
   engagement survives restart (ties §4's restart procedure to this drill).

This is the literal test vector set for `TEST_SPEC_RISK.md`'s mutation/property
coverage of the paper broker; a PR implementing P2 is not done until an
automated test executes all six steps, not just steps 1-3.

## 7. Non-goals

- This spec does not cover real broker adapters (Kite Connect, Alpaca, CCXT) —
  those are separate `Broker` Protocol implementations, P3+.
- It does not define the Telegram approve/reject wiring's message format — that's
  `PAGES.md` §2 (already written) plus the API in `PAGES.md` §3.
- It does not re-derive the fill/cost formulas — those are pinned in
  `trading/backtest/fills.py` and must be reused (imported), not reimplemented,
  so paper and backtest can never silently diverge.
