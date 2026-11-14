# RISK SPEC

The risk engine is the most important module. It sits between every signal and every order, can veto anything, and defaults to **no**. Owner: Claude writes the spec (`docs/specs/` extends this); GPT-6.1 Sol implements; GPT-6 Astra reviews; blind tests are written by a different model from this spec. See `MODEL_ROLES.md`.

All numbers below are **proposed defaults**; the owner confirms them in `config/risk.yaml` before any live mode.

## 1. Responsibilities

1. Pre-trade checks on every `OrderRequest` (paper and live; paper uses the same checks so paper results mean something).
2. Position sizing from stop distance.
3. Portfolio-level limits across sleeves.
4. Circuit breakers and kill switches.
5. Mode gating: nothing becomes a real order unless the gates in `AGENTS.md` §4 hold.
6. Reconciliation and audit.
7. Position-reducing exits use `ExitRequest`, not entry `OrderRequest`.

## 2. Pre-trade checks (ALL must pass; first failure rejects with a reason code)

| # | Check | Notes |
|---|---|---|
| 1 | Kill switch off (global, sleeve, instance) | |
| 2 | Mode permits this route (paper/approval/auto) | |
| 3 | Market session open and symbol tradable | uses calendar |
| 4 | Data fresh: last bar/tick age <= `stale_data_seconds` | intraday only |
| 5 | Signal valid: has stop; stop on correct side; risk distance within sane bounds | no stop = reject |
| 6 | Price band: order price within `order_price_band_pct` of last price | fat finger |
| 7 | Risk per trade <= sleeve `risk_per_trade_pct` of sleeve equity | sizing |
| 8 | Sleeve allocation and max positions not exceeded | |
| 9 | Total open positions <= global max | |
| 10 | Daily loss limit not breached | no new entries after breach |
| 11 | Portfolio drawdown below kill threshold | |
| 12 | Instance not paused (consecutive losses / drift) | |
| 13 | Liquidity: order quantity <= max % of recent average volume (config per market) | penny/meme stricter |
| 14 | Duplicate/idempotency: same signal id never produces two orders | |
| 15 | Correlation/concentration: no more than X% of total risk in one symbol/sector/underlying | config; start simple |
| 16 | Brain verdict (if present) is schema-valid; a `veto` blocks; `size_multiplier` only reduces size (0..1) | Brain cannot increase risk |

## 3. Sizing

`qty = floor( equity_sleeve * risk_per_trade_pct / |entry_ref - stop| )`, then cap by: max position value %, liquidity cap, lot size/tick size rounding (round **down**), available margin/cash. If qty < 1 lot/share -> reject (no rounding up).

## 3A. Exit requests

An `ExitRequest` is position-reducing only and contains:

- `exit_id`: unique idempotency key; duplicate delivery never creates another order.
- `position_id`: required and resolved against broker truth.
- `side`: derived from the open position, never supplied by the caller.
- `reason_code`: enum (`STOP`, `TARGET`, `CONDITION`, `TIME`, `KILL`) plus
  free-text context that is never interpreted as logic.
- `quantity`: `0 < quantity <= open quantity`; a full exit uses the full open quantity.

Exits still require a valid matching position, broker reconciliation, positive
non-rounded quantity, an open session or explicitly allowed queued order,
paper-mode checks, and an audit row. The kill switch blocks new entries only;
protective exits remain allowed and may be triggered by the kill switch itself.
Risk-per-trade sizing, sleeve allocation, max-open-positions, and Brain verdict
checks are skipped. `STOP` and `KILL` exits cannot be vetoed by the Brain.
Invalid state fails closed and alerts the human.

## 4. Circuit breakers and kill switches

| Trigger | Action |
|---|---|
| Portfolio drawdown from peak >= `max_portfolio_drawdown_pct` | **Global kill**: no new entries; cancel open entry orders; keep/verify protective stops; alert owner. Resuming requires an explicit human action |
| Daily loss >= `max_daily_loss_pct` | No new entries until next session |
| Sleeve drawdown limit | Sleeve kill |
| Instance consecutive losses >= N or live drawdown beyond backtest worst case by a margin | Pause instance; alert |
| Stale feed / reconnect loop | Pause new entries in that sleeve; alert |
| Broker/exchange error burst, rate-limit, token expiry | Pause sleeve; alert |
| Reconciliation mismatch (our state vs broker) | Global or sleeve kill depending on scope; alert |
| Unexpected exception in risk/execution | Fail closed: halt new entries |
| Budget cap exceeded (LLM) | Brain off; rules-only continues |

A **manual kill switch** (dashboard + Telegram command) must work even if the Brain, scanner and dashboard are down. It is implemented in the engine/API layer with minimal dependencies.

## 5. Invariants (each must be a test; property-based where possible)

- I1: In `paper` mode, the real-broker adapter is never called.
- I2: An order is placed only if a `RiskDecision(allowed=True)` exists for that exact signal id and quantity.
- I3: Executed quantity never exceeds approved quantity.
- I4: Per-trade risk (qty x stop distance) never exceeds the configured % of sleeve equity (excluding gap risk, which is tracked separately).
- I5: Sum of open position values per sleeve never exceeds the sleeve cap.
- I6: With kill switch on, zero new entry orders are created, for any input sequence.
- I7: Duplicate delivery of the same signal/event never creates a second order (idempotency).
- I8: A Brain output outside the schema is ignored (treated as "no verdict") and cannot raise size.
- I9: Quantity is never rounded up; never negative; never zero-submitted.
- I10: Mode can only be escalated (paper -> approval -> auto) by an explicit human action recorded in the audit log; any automatic action may only de-escalate.
- I11: Every rejected/approved decision is written to the audit log with reason codes.
- I12: Position state after restart equals broker truth, or the engine refuses to start trading.
- I13: No code path reads future bars (verified in backtest with truncated-data tests).
- I14: An exit request never opens or increases a position, for any input; executed
  exit quantity is positive and never exceeds the matching open quantity.

## 6. State machine (order)

`created -> risk_approved -> routed -> (acknowledged) -> partially_filled -> filled | cancelled | rejected | expired`. Every transition is logged; illegal transitions raise and trigger fail-closed.

## 7. Gap and overnight risk

Stops cannot guarantee exit price. Track "gap risk" separately (overnight positions, illiquid names). Position limits for illiquid/penny/memecoin are tighter. Prefer broker-held protective orders where available; otherwise the engine checks at open and exits per policy.

## 8. Interfaces (to be fixed in `docs/specs/CONTRACTS.md`)

`RiskEngine.check(signal, portfolio_state, brain_verdict | None, config) -> RiskDecision{allowed, qty, reason_codes[], limits_snapshot}`; `KillSwitch.engage(scope, reason)`; `ModeGate.route(decision, sleeve_mode, human_action | None) -> Route{paper|live|none}`.

## 9. Required test inputs (from `docs/TESTING.md`)

Invariant/property tests for I1-I14; failure-injection (exceptions mid-check, partial fills, duplicate events); adversarial inputs (malformed Brain JSON, prompt-injection strings in `reason` fields, NaN/inf/negative prices, zero-width stops, huge quantities); mutation testing on this module. I14 must include property tests proving exits cannot increase position quantity.
