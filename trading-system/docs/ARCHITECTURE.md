# ARCHITECTURE

Status: design v1.0. The foundation sprint (P0) turns this into `docs/specs/CONTRACTS.md` and `docs/specs/ADAPTERS.md` plus code in `src/trading/core/`.

## 1. Layers

| Layer | Responsibility | Module (proposed) |
|---|---|---|
| **Eyes** | Pull data (live ticks via WebSocket, historical candles, daily files, news). Build candles. One adapter per source, one common output format. | `trading.data`, `trading.adapters.*` |
| **Calculator** | Incremental indicators, strategy templates, daily scanner -> `Signal` objects | `trading.indicators`, `trading.strategies`, `trading.scanner` |
| **Brain** | Optional LLM context on formed signals; news triage | `trading.brain` |
| **Hands** | Risk engine, mode gate, order router, paper broker, real broker adapters, reconciliation | `trading.risk`, `trading.execution`, `trading.brokers` |
| **Voice** | Telegram, internal API, dashboard, usage/cost, ledgers | `trading.voice`, `trading.api`, `dashboard/` |
| **Backtest** | Same candle/indicator/strategy code, simulated broker with costs/slippage | `trading.backtest` |
| **Core** | Pydantic contracts, enums, clock, calendars, config | `trading.core` |

Dependency rule: `core` depends on nothing in the project; `indicators`/`strategies` depend only on `core`; adapters depend on `core`; `execution`/`risk` depend on `core`; nothing imports `voice` except entry points.

## 2. Hot path vs slow path

| Path | Contents | Latency target |
|---|---|---|
| Hot | tick -> candle builder -> incremental indicators -> strategy check -> risk check -> order | milliseconds to low seconds; plain Python + `asyncio` is enough |
| Slow | Brain calls, news triage, daily scanner, retraining, reports | seconds to minutes, scheduled or event-driven; results written to state and read by hot path |

The LLM is never awaited inside the hot path. If Brain output is missing when a signal fires, the signal proceeds on rules only (configurable), or waits a short bounded time, then proceeds.

## 3. Time and sessions

- Everything stored in **UTC**. Market-local times derived with calendars (`exchange_calendars` or equivalent) incl. holidays and early closes.
- A **market scheduler** switches each sleeve's live feed/engine on/off by session: India 09:15-15:30 IST; US regular 09:30-16:00 ET (= 19:00-01:30 IST during US daylight time, 20:00-02:30 IST in standard time); crypto 24/7 with a configured daily cutoff; MCX approx 09:00-23:30/23:55 IST (per-instrument; verify). When a market is closed its live engine sleeps and its **post-market routine** runs: save candles, recompute daily indicators, run the daily scanner, outcome tracking, daily report.
- Positions held overnight are still tracked; protective stops live at the broker where supported, else the engine checks at the open.
- The clock is injected (`trading.core.clock`) so tests and replays are deterministic.

## 4. Candles and indicators

- Ticks are **never persisted long term**. The candle builder updates the current bar per `(market, symbol, timeframe)`; when a bar closes it is validated, persisted, and published to subscribers; ticks are dropped (rolling buffer default 3 days, for debugging).
- Candle schema: `market, symbol, timeframe, ts_open_utc, open, high, low, close, volume, source, ingest_ts` (daily adds `adj_factor`).
- Indicators are **incremental** (EMA, RSI, ATR, ADX, Bollinger, VWAP, Donchian...) with a bounded rolling window held in memory; each also has a pure batch implementation used by the backtester. A unit test proves incremental == batch on the same data. This is the "one code path" guarantee.
- Signals are generated **only on closed bars**. Fills simulated at next bar open (+ costs/slippage). If stop and target are both inside one bar, assume the stop hit first.

## 5. Tiers and the scanner

- Tier A (≈100 names per stock market) = live stream.
- Tier B (whole market) = daily file -> store -> scanner scores (momentum, trend, volume surge, nearness to 52-week high...) -> shortlist table (`state`) -> promoted to live watch next session and shown on the Stocks page.
- Universe filter is config: price floor, minimum average traded value, series/instrument type, surveillance-list exclusion switch. Penny stocks are in/out by config; they get pessimistic paper fills.

## 6. Storage

```
data/                      (git-ignored)
  candles/{market}/{timeframe}/{symbol}.parquet   # or date-partitioned; DuckDB queries it
  daily_files/{market}/YYYY-MM-DD.*               # bhavcopy etc., raw as downloaded (keep)
  corporate_actions/{market}/...
  ticks/{market}/YYYY-MM-DD/                      # rolling buffer, auto-deleted
state/trading.db           (SQLite, WAL)          # orders, fills, positions, signals, outcomes,
                                                  # risk_events, mode_changes, llm_calls, audit
```

Retention: raw downloaded candles/files kept; derived caches/backtest outputs regenerable and deletable. Back up `data/` (compressed) to free cloud storage.

## 7. Processes

```
engine      one process per sleeve (or one multiplexed): scheduler + feeds + candle builder + strategies + risk + execution
scanner     scheduled job after close (per market)
brain       worker with budget guard, called via queue; separate from engine
api         FastAPI: read state, post decisions (approve/paper/reject), toggle modes, kill switch
dashboard   Streamlit reading from api
notifier    Telegram bot (alerts + inline buttons) via api
```

The dashboard and Telegram are **windows**; the engine runs without them.

## 8. Order flow

```
Signal -> (Brain verdict optional) -> RiskEngine.check(signal, portfolio_state) -> RiskDecision
  allowed? no -> log + (alert if notable) -> stop
  yes -> ModeGate:
     sleeve=paper    -> PaperBroker (simulated fill w/ costs)
     sleeve=approval -> alert with buttons; Approve -> real broker adapter; Paper test -> PaperBroker; Reject -> outcome tracker only
     sleeve=auto     -> real broker adapter (within limits); shadow paper copy if auto_paper_shadow
  all paths -> OutcomeTracker follows signal to target/stop/timeout for stats
```

Orders carry idempotency keys; the order router reconciles with broker state on start and periodically; mismatch -> fail closed.

## 9. Ledgers

- `live_ledger` (real broker fills), `paper_ledger` (simulated). Every row tagged `source` in {`live`, `user_paper`, `shadow`}.
- `signal_outcomes`: per signal, whether target/stop/timeout hit, % after costs, bars held. Powers "similar setups" stats and "rejected trades would have..." views.

## 10. Config

`config/*.yaml` (git-ignored, with committed `*.example.yaml` templates): `markets`, `risk`, `strategies` (registry), `tax`. Environment secrets in `.env`.

## 11. Observability

Structured JSON logs; audit table for every order, risk decision, mode change, LLM call. Health checks for each connection (feed, broker token expiry, API errors) shown on the Usage/Accounts page. Alerts on kill switch, stale data, reconciliation mismatch, budget cap hit.

## 12. Extending to a new market

1. Add a market profile in `config/markets.yaml`.
2. Implement `DataFeed` and `Broker` adapters behind the shared Protocols (`docs/specs/ADAPTERS.md`).
3. Add paper-fill assumptions (costs/slippage).
4. Create strategy *instances* (template + profile) at status `idea`.
5. Run the pipeline in `STRATEGIES.md`. No shortcuts.
