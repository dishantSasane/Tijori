# CANDLE BUILDER AND MARKET-SESSION SCHEDULER SPEC

Status: P3 deliverable (`docs/BUILD_ORDER.md`). Written ahead of implementation
so Codex isn't guessing at the live tick->candle path. `ADAPTERS.md` §1 pins
the `DataFeed` Protocol's shape (`poll_closed_candles()`, no forming-bar
accessor) and `TEST_SPEC_CANDLES.md` already pins the *test* vectors for the
builder's behaviour at the edges. Neither file says how the builder is
structured internally, how multiple timeframes relate, or how the scheduler
decides a market is open — that is this spec. It does not re-derive any rule
`TEST_SPEC_CANDLES.md` already fixed; where the two could conflict, that file
wins and this spec should be read as implementing it.

## 1. Why a separate spec

`ARCHITECTURE.md` §3 names "tick -> candle builder -> incremental indicators"
as the hot path and §4 sketches the ticks-are-not-persisted rule, but a
one-line architecture sketch is not enough for Codex to build the same
component twice without drift (live builder vs. whatever the backtester
reuses). This spec exists so there is exactly **one** candle-builder
algorithm, used by both the live adapter and the backtest/bhavcopy path
(`TEST_SPEC_CANDLES.md` §1.6 already requires the two origins to validate
identically) — the live/market-session concerns (what this spec adds) sit on
top of that shared algorithm, never fork it.

## 2. Candle builder structure

One `CandleBuilder` instance per `(market, symbol, timeframe)`. State:

```
bar_open_ts_utc: datetime | None   # None if no tick seen yet this bar
open, high, low, close: Decimal | None
volume: Decimal
tick_count: int
```

### 2.1 Bar assignment

A tick's bar is `floor_to_timeframe(tick.ts_utc, timeframe)` — computed in
**UTC**, never in market-local time (`TEST_SPEC_CANDLES.md` §1.1's known-
answer case is the test for this). The builder does not care what market-
local session it is; that is the scheduler's job (§4).

### 2.2 Close trigger: timer, not next-tick

The bar for `[bar_open, bar_open + timeframe)` closes at
`bar_open + timeframe`, driven by the clock, not by the arrival of the next
bar's first tick (`TEST_SPEC_CANDLES.md` §1.2). Concretely: the builder is
driven by a scheduler tick (§4.3) at least once per smallest configured
timeframe; on each drive, it checks `clock.now() >= bar_open + timeframe` for
every bar currently open and, if true, closes it (§2.3) before accepting any
new tick into the next bar. This means a market with literally zero ticks in
a window still produces a bar — never a gap that would break a fixed-length
lookback indicator downstream.

### 2.3 Closing a bar

1. If `tick_count == 0` for the window: synthesize a zero-volume bar carrying
   forward the previous closed bar's `close` as `open=high=low=close`,
   `volume=0` (`TEST_SPEC_CANDLES.md` §1.2). The very first bar of a symbol's
   session with zero ticks has no previous close to carry forward — skip
   emitting it rather than inventing a price; this is the one case where a
   bar is legitimately absent, and it is logged as `no_prior_close_zero_tick`
   so it is distinguishable from a bug.
2. Otherwise: emit `Candle(open, high, low, close, volume, ts_open_utc=
   bar_open, timeframe, source="tick_builder")` (`source` distinguishes from
   `"nse_bhavcopy"` per `TEST_SPEC_CANDLES.md` §1.6).
3. The emitted `Candle` is appended to that `(market, symbol, timeframe)`'s
   closed-bar buffer, which is what `poll_closed_candles()` reads from — the
   buffer only ever grows by append; nothing already in it is mutated
   (`Candle` is `frozen=True`, `CONTRACTS.md` §2, so this is partly enforced
   by the type system, partly by never writing code that would try).
4. The builder's in-progress state for the next window is reset to empty
   (`bar_open_ts_utc=None`, etc.) — a late tick for the window just closed is
   handled by §2.4, never by reopening this state.

### 2.4 Late / out-of-order ticks

- A tick within the **current open** window, but older than the latest tick
  already processed (network reorder): folded into O/H/L/V normally; `open`
  is defined as **the price of the chronologically-earliest tick by its own
  timestamp**, not "first tick processed" — this is the explicit choice
  `TEST_SPEC_CANDLES.md` §1.3 flagged as needing to be pinned down; pinned
  here.
- A tick whose bar has **already closed and been emitted**: dropped, never
  folds into the already-emitted `Candle` and never opens a stray new bar for
  a past window. Logged (`event_type="late_tick_dropped"`, `AGENTS.md` §6)
  with the bar it arrived too late for, so a systematically slow feed is
  visible in the audit log rather than silently eating data.

### 2.5 Multi-timeframe derivation

Only one timeframe is ever built directly from ticks: the smallest one
configured for a market (e.g. `1m`). Every larger timeframe used by a
strategy (`5m`, `15m`, `1D` intraday aggregation — distinct from the
bhavcopy-sourced daily bar in §2.3 point 2) is derived by aggregating closed
bars of the smaller timeframe, using the same closed-bars-only, timer-driven
close rule recursively — a `5m` builder consumes `1m` `Candle`s the same way
a `1m` builder consumes ticks, substituting "closed smaller bar" for "tick."
This keeps exactly one code path for "roll up closed inputs into a bigger
closed bar," reused at every level, instead of a special-cased aggregator.

## 3. Market-session scheduler

One scheduler per market (`MarketId`), driving every symbol's builders for
that market together, since they share a session calendar.

### 3.1 Session source of truth

Session open/close/holidays come from `exchange_calendars` (or the project's
chosen equivalent, per `AGENTS.md` §6) keyed by the market's exchange
calendar code — never a hand-maintained holiday list in this repo, which
would silently drift from reality. `ARCHITECTURE.md` §3's approximate hours
table (India 09:15-15:30 IST, US 09:30-16:00 ET, crypto 24/7 with a
configured daily cutoff, MCX ~09:00-23:30/23:55 IST) is the fallback only for
markets `exchange_calendars` doesn't cover (crypto, MCX) — those use a
config-driven session window in `config/markets.yaml` instead, with no
holiday calendar (crypto) or the exchange's own published calendar (MCX, once
confirmed — flagged `needs-human` if no free machine-readable MCX calendar
exists; do not hand-encode MCX holidays as a guess).

### 3.2 Session state machine (per market)

```
CLOSED -> PRE_OPEN -> OPEN -> POST_CLOSE -> CLOSED
```

- `CLOSED -> PRE_OPEN`: at the pre-market batch-approval time
  (`TELEGRAM_ALERT_SPEC.md` §3), if today is a trading day for this market's
  calendar. On a holiday, the market stays `CLOSED` all day — no
  `PRE_OPEN`/`OPEN` transition fires, and the post-market routine (§3.4) is
  skipped since there is nothing to summarize.
- `PRE_OPEN -> OPEN`: at the calendar's session-open instant. The scheduler
  starts driving candle builders for every subscribed symbol in this market
  only from this transition onward — no live engine work happens before
  `OPEN`, so `PRE_OPEN` is purely the Telegram-batch window, not a trading
  window.
- `OPEN -> POST_CLOSE`: at the calendar's session-close instant. Any signal
  still `PENDING` (`TELEGRAM_ALERT_SPEC.md` §2) expires here
  (`SESSION_ENDED_UNFILLED`, `PAPER_BROKER_SPEC.md` §2.1) — this transition
  is what actually fires that timeout, not a separate timer.
- `POST_CLOSE -> CLOSED`: once the post-market routine (§3.4) completes.
  Live builders stop being driven; any in-progress (not-yet-closed) bar at
  the moment of close is closed early using whatever ticks it got, flagged
  `partial_session_close=True` on that one `Candle` so downstream indicator
  code can treat it as a known short bar rather than mistaking it for a
  full-length one. `ADAPTERS.md` §1's `is_stale` returns `True` for this
  market for the entire `CLOSED` period (per that file's own fail-closed
  default), which is also what makes risk check #3 (`MARKET_CLOSED`) and
  check #4 (`DATA_STALE`) agree instead of racing each other.

### 3.3 Driving builders while `OPEN`

The scheduler's drive loop runs at a fixed cadence no coarser than the
smallest configured timeframe (e.g. every 5-10 seconds for a `1m` base
timeframe) and, each tick of the loop, for every `(symbol, timeframe)` pair
calls the builder's close check (§2.2). This loop is the only thing that
calls `clock.now()` in this subsystem — builders themselves take `now` as a
parameter, never read the clock directly, keeping them deterministic and
testable with `FixedClock` exactly like every other core component
(`AGENTS.md` §6).

### 3.4 Post-market routine

Triggered once, exactly at `OPEN -> POST_CLOSE`, and must complete (or fail
loudly) before the market reaches `CLOSED`:

1. Persist the session's closed candles (already done incrementally by §2.3,
   this step is the durability checkpoint/flush, not first-write).
2. Recompute any daily-only indicators that need a confirmed final daily bar
   rather than an intraday approximation.
3. Run the daily scanner (`BUILD_ORDER.md` P4 — a no-op until P4 ships; this
   step exists in the state machine now so P4 doesn't need to touch the
   scheduler).
4. Run outcome tracking for the session's shadow/rejected signals
   (`PAPER_BROKER_SPEC.md` §5) — every signal from this session should have a
   terminal `SignalOutcome` by the time this step finishes, since nothing
   from a closed session should still be "pending" scoring tomorrow.
5. Emit the daily report (`BUILD_ORDER.md` P3's exit criterion references
   "logs and daily reports" — format not yet specced; out of scope here,
   flagged for a future `DAILY_REPORT_SPEC.md` if one proves necessary).

If any step raises, the routine logs the failure, the market still moves to
`CLOSED` at end of day (it must not get stuck `POST_CLOSE` forever blocking
tomorrow's `PRE_OPEN`), but a `post_market_routine_failed` `AuditEvent` is
written and the dashboard/Telegram surfaces it — this is a fail-closed-ish
case where "closed" is still safe (no new entries happen while `CLOSED`
anyway) but the owner must be told a report or outcome batch may be missing,
never silently.

### 3.5 Multiple markets, one process or several

`ARCHITECTURE.md` §7 allows "one process per sleeve (or one multiplexed)."
This spec doesn't mandate either — each market's scheduler instance is
independent and holds no shared mutable state with another market's, so the
choice is purely a deployment detail, not something this spec needs to pin
down. Timezone handling is already covered (`AGENTS.md` §6, UTC internally)
so running several schedulers in one process never requires per-market
thread-local timezone hacks.

## 4. Non-goals

- Does not re-derive indicator math or warm-up rules — `STRATEGY_SPEC.md`,
  `TEST_SPEC_CANDLES.md` §2.
- Does not define the free live-data source/adapter itself (which feed,
  rate limits, reconnect behaviour) — that is `DATA_SOURCES.md`'s job per
  market, this spec only consumes whatever `DataFeed.subscribe` hands it.
- Does not define the daily report's content/format (§3.4 point 5) or the
  P4 scanner's logic (§3.4 point 3) — placeholders only, so the scheduler's
  shape doesn't need to change when those are specced later.
- Does not cover MCX's exact session calendar until confirmed free and
  machine-readable (§3.1) — an owner decision, not a guess to make here.
