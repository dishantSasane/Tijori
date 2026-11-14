# CONTRACTS — `src/trading/core/`

Status: P0 deliverable. Implements AGENTS.md §6 (Pydantic v2, Decimal on order
paths, UTC timestamps, injected clock) for docs/ARCHITECTURE.md's `core` layer.
`core` depends on nothing else in the project.

## 1. Enums (`core/enums.py`)

`MarketId`, `Mode`, `Timeframe`, `OrderSide`, `OrderStatus`, `Route`,
`BrainLabel`, `OutcomeResult`, `LedgerSource`, `ReasonCode`, `ExitReason`.

`ORDER_STATUS_TRANSITIONS` is the order state machine from
`docs/RISK_SPEC.md` §6 as data, not scattered `if` statements:
`created -> risk_approved -> routed -> (acknowledged) -> partially_filled ->
filled | cancelled | rejected | expired`. `trading.adapters.broker.transition()`
is the only sanctioned way to change an `Order.status`; it raises
`IllegalOrderTransitionError` on anything not in the table (fail closed).

`ReasonCode` is the catalogue for `docs/RISK_SPEC.md` §2's 16 pre-trade
checks, numbered by name not by position. **Append-only**: a value already
shipped must never be renumbered or deleted, because audit history depends on
the string being stable.

## 2. Models (`core/models.py`)

All models inherit `Contract`: `frozen=True` (immutable — a decision, once
made, is a historical fact), `extra="forbid"` (typos fail loud, not silently),
and a validator rejecting any naive `datetime` field. This directly implements
AGENTS.md §6's "UTC internally" and "Decimal on order paths" rules at the type
level, so a bug that passes a float price or a local-time timestamp fails at
construction, not at 3am in production.

| Model | Key invariants enforced at construction |
|---|---|
| `Candle` | `low <= open/close <= high`; ts UTC-aware. Only closed bars exist in this type — there is no "forming candle" model, by design (AGENTS.md §4.5). |
| `Tick` | price/size > 0; never persisted long-term (adapters only). |
| `Signal` | stop, if present, is on the correct side of `entry_ref` for `side`. A **missing** stop is allowed here (it's a risk-engine rejection with `ReasonCode.SIGNAL_MISSING_STOP`, not a contract error — the rejection must be auditable, so the signal has to be constructible first). |
| `OrderRequest` | qty > 0; carries `idempotency_key` (invariant I7). |
| `ExitRequest` | unique `exit_id`; required `position_id`; quantity > 0; reason enum plus inert human text. Execution derives side from broker truth and enforces quantity <= open quantity (I14). |
| `Order` | `qty_filled <= qty` (invariant I3); `status` is only ever changed via `transition()`. |
| `Fill` | qty, price > 0; tagged with `LedgerSource` (live/user_paper/shadow). |
| `Position` | — |
| `RiskDecision` | `allowed=True` <=> `qty > 0` (invariant I9: never a zero-submitted "approval"); `allowed=False` <=> `qty == 0`; `reason_codes` non-empty always (invariant I11). |
| `BrainVerdict` | `size_multiplier` in `[0, 1]` — structurally cannot increase risk (ADR-0008, invariant I8). |
| `SignalOutcome` | — |
| `AuditEvent` | one row per order/risk-decision/mode-change/LLM-call (AGENTS.md §6). |

## 3. Clock (`core/clock.py`)

`Clock` Protocol with `.now() -> datetime` (UTC). `SystemClock` for process
entry points only; `FixedClock` for tests/backtests/replays — never call
`datetime.now()`/`utcnow()` inside `core`, `risk`, `execution`, `strategies`,
or `indicators` (AGENTS.md §6). This is what makes backtests and replay tests
reproducible: same inputs, same clock, same output.

## 4. Config (`core/config.py`)

`load_yaml(path)` loads `config/<name>.yaml`, falling back to
`config/<name>.example.yaml` if the real file doesn't exist yet (so the repo
runs out of the box), but raises `ConfigNotFoundError` if neither exists —
it never fabricates defaults silently.

`RiskGlobalConfig` strictly types the `global:` block of `risk.yaml` (the one
risk-critical, concretely-specified piece). Per-sleeve and per-market config
stay as plain dicts for now; typing them fully is part of the risk-engine and
market-profile implementation work, not a prerequisite for it — modeling
fields nobody has implemented a consumer for yet would be the "config for a
value that never changes" trap.

## 5. What is deliberately NOT here yet

- The risk engine's `check()`/`KillSwitch`/`ModeGate` implementations — only
  their inputs/outputs (`RiskDecision`, `Route`, `ReasonCode`) exist. The
  engine itself is `docs/specs/RISK_ENGINE_SPEC.md` + P2 code.
- Indicator/strategy/candle-builder code — P1 (Codex), built against `Candle`.
- A `NewsItem` contract for `NewsFeed` lives in `trading/adapters/news_feed.py`,
  not here, because it isn't on the BUILD_ORDER P0 contracts list and nothing
  outside the Brain/news adapters consumes it yet.
