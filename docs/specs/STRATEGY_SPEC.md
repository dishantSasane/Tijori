# STRATEGY SPEC

Status: P0 deliverable (BUILD_ORDER.md item 8). Turns `docs/STRATEGIES.md`'s
rules into exact pseudo-code plus named test vectors, resolving note 0003
Q5-Q6 (optional vs. mandatory target; bar timestamp/warm-up/Wilder-seed/
zero-denominator/same-bar-exit/final-bar-unfilled semantics). T1 and T4 get
full hand-calculated known-answer vectors, since BUILD_ORDER.md P1 names them
as "the first honest scorecard." T2/T3/T5/T6/F1 get exact pseudo-code; their
vectors are flagged as a follow-up, not invented under time pressure (an
approximate hand-calculation here would be worse than none — Terra/whoever
writes blind tests should derive them straight from this pseudo-code with a
spreadsheet, not trust a rushed arithmetic check).

## 1. Shared semantics (apply to every template; resolves Q6)

### 1.1 Bar timestamp and closed-bar convention

A `Candle`'s `ts_open_utc` is the bar's **open** time; the bar is "closed"
once a full `timeframe` duration has elapsed from it. `Signal.bar_ts_utc`
equals the closed bar's `ts_open_utc` — the same field, same convention, on
both contracts, so joining a signal back to the candle that produced it is a
plain equality, never an off-by-one subtraction.

A strategy function receives only candles whose close time has already
passed (`DataFeed.poll_closed_candles()` guarantees this, ADAPTERS.md §1) —
it is structurally impossible for a strategy to see a forming bar.

### 1.2 Warm-up

No template may emit a `Signal` until **every** indicator it reads has
produced a real (non-`None`) value. Minimum bars of history needed before an
indicator's first value exists:

| Indicator | Warm-up (bars) | First valid value is computed from |
|---|---|---|
| `SMA(n)` | `n` | simple mean of the first `n` closes |
| `EMA(n)` | `n` | seeded with `SMA(n)` of the first `n` closes, then EMA recursion from bar `n+1` onward |
| `RSI(n)` (Wilder) | `n + 1` | needs `n` bar-to-bar changes, which needs `n+1` closes |
| `ATR(n)` (Wilder) | `n + 1` | same reasoning: `n` true-range values need `n+1` bars |
| `ADX(n)` | `2n` (approx.) | ADX is itself a Wilder-smoothed average of `DX`, which needs a warmed-up `+DI`/`-DI` pair (each itself needing `n+1` bars) before it has `n` values to average — a strategy using `ADX(14)` has no signal before bar 28 of history, not bar 15 |
| `Donchian H(n)/L(n)` | `n` | uses the **previous** `n` bars, excluding the current one (STRATEGIES.md §3's `H(n)` definition) — so the earliest bar it can be evaluated on is bar `n+1` |

A template combining indicators (e.g. T2's `EMA(50)` + `ADX(14)`) warms up at
`max()` of its indicators' warm-ups, computed independently, never summed.

**Test vector (warm-up):** feed a strategy using `SMA(200)` exactly 199
closed daily bars → it must emit zero signals, regardless of what the prices
do. Feed it 200 bars → `SMA(200)` has its first value on bar 200 and the
strategy may now evaluate (not necessarily *fire* — the entry condition
still has to be true).

### 1.3 Wilder seeding and recursion (RSI, ATR, ADX)

All three use the **same** seed-then-recurse pattern — implement it once,
shared, not three times:

```
seed  = simple_average(first n values)
next  = (prev_avg * (n - 1) + new_value) / n        # Wilder smoothing, NOT a plain EMA alpha
```

`ATR(n)`: `true_range[i] = max(high[i]-low[i], |high[i]-close[i-1]|,
|low[i]-close[i-1]|)`; seed = `SMA(true_range, n)` over bars `1..n`; then
Wilder-recurse. `RSI(n)`: seed `avg_gain`/`avg_loss` as the simple mean of
gains/losses over the first `n` changes; then Wilder-recurse each; `RS =
avg_gain / avg_loss`; `RSI = 100 - 100/(1+RS)`.

**Known-answer vector (Wilder ATR(2), tiny so it's hand-checkable):** closes
`[10, 12, 11, 13]`, highs `[10, 13, 12, 14]`, lows `[9, 11, 10, 12]` (bar 0 has
no prior close, so no true range yet):
- `TR[1] = max(13-11, |13-10|, |11-10|) = max(2,3,1) = 3`
- `TR[2] = max(12-10, |12-12|, |10-12|) = max(2,0,2) = 2`
- seed `ATR(2)` at bar 2 = `mean(TR[1], TR[2]) = 2.5`
- `TR[3] = max(14-12, |14-11|, |12-11|) = max(2,3,1) = 3`
- `ATR(2)` at bar 3 = `(2.5*(2-1) + 3)/2 = 2.75`

### 1.4 Zero-denominator and degenerate-input rules

- `RSI`: if `avg_loss == 0` and `avg_gain > 0` → `RSI = 100` (not a division
  error). If both are `0` (flat price for the whole window) → `RSI = 50`
  (neutral, by convention — neither up nor down).
- `ATR == 0` (a market frozen at one price for `n+1` bars, e.g. a halted
  stock): any template computing a stop as `entry - k*ATR` would produce
  `stop == entry`, which `Signal`'s own validator already rejects (stop must
  be strictly on the correct side, CONTRACTS.md §2) — so this degenerates to
  "no signal," not a zero-width-stop bug. Templates must not substitute a
  fallback ATR value to force a signal through; a strategy that can't size
  its stop simply doesn't fire that bar.
- `ADX` denominator (`+DI + -DI == 0`): only possible if both smoothed
  directional movements are zero, i.e. price hasn't moved in `n` bars — same
  flat-market case as above; by convention `DX = 0` in that case (no trend
  either way), which flows into `ADX` normally (no special-case needed
  downstream since `0` is a valid input to Wilder smoothing).

### 1.5 Same-bar exit precedence

Already stated in STRATEGIES.md §2.2 for the entry's fill bar: if a bar's
high and low would trigger both the stop and the target (or an exit
condition), **the stop is assumed hit first.** This spec adds: the rule
applies starting from the **entry fill bar itself** — a position can be
stopped out on the very bar it was filled, if that bar's range reaches the
stop. There is no "one free bar" grace period.

### 1.6 Final-bar unfilled signal

A signal generated on the **last available closed bar** (end of a finite
backtest window, or the live system's most-recently-closed bar with no next
bar yet) has **no fill**, because fills happen at the next bar's open
(AGENTS.md §4.5) and that bar doesn't exist yet. Handling:

- **Backtest:** such a signal is excluded from the scorecard entirely — not
  counted as a loss, not counted as a win, not synthesized with an assumed
  fill price. It is logged (so a human reviewing results knows data ran out
  mid-signal), but contributes zero trades.
- **Live:** the signal is held as `pending` (not yet an `OrderRequest`) until
  the next bar closes and supplies a real open price, then proceeds through
  risk as normal. If the market closes for the day before the next bar
  exists (end-of-session on a lower timeframe, e.g. last 5-min bar of the
  Indian session), the signal expires unfilled rather than carrying over to
  the next session's open — carrying over would silently change what
  "entry_ref" meant relative to when the strategy actually evaluated it.

### 1.7 Optional vs. mandatory target (resolves Q5)

`Signal.target` is, and stays, **optional** on the contract
(`CONTRACTS.md` §2) — this spec does not change that. Per template:

| Template | Has a `target`? | Exit mechanism when no target |
|---|---|---|
| T1 Donchian | No | Exit condition (`close < L(M)`) or stop |
| T2 MA+ADX | No | Exit condition (`EMA(F) < EMA(S)`) or stop |
| T3 Momentum | No | Rebalance/drop-out-of-top-`2K` (see §2.3) |
| T4 RSI(2) pullback | No | Exit condition (`close > SMA(5)` or `RSI(2)>70`) or time stop or hard stop |
| T5 ORB | **Yes, mandatory** | Target is the template's primary exit; stop and square-off time are the fallback |
| T6 Bollinger reversion | No | Exit condition (`close >= middleBand`) or stop or time stop |

**Condition-based exits are a known open gap, not solved here:** T1/T2/T4/T6
exit by re-evaluating a rule on each new closed bar for every *already-open*
position of that instance, which is a different mechanism from the intrabar
stop/target check in §1.5 (it only ever evaluates at bar close, never
intrabar). This spec does not yet define: (a) what object type an
exit-by-condition produces (today's contracts have no `ExitSignal` — see
CONTRACTS.md §5's YAGNI stance, which this spec is now pushing against), or
(b) whether an exit order must pass the risk engine's full pre-trade check
list (RISK_ENGINE_SPEC.md §2 is written for *new* risk, i.e. entries — an
exit should almost certainly skip checks like "risk per trade" and "max
positions," since it's reducing risk, not adding it, but RISK_ENGINE_SPEC.md
doesn't say so explicitly yet). **Recommendation for whoever implements
P2/execution:** add a minimal `ExitRequest` contract (symbol, qty, reason)
and a reduced exit-only check list (kill-switch-aware but not
sizing/allocation-aware) to `RISK_ENGINE_SPEC.md` before implementing T1/T2/
T4/T6's exits — do not guess this silently in code. Flagging as `needs-human`-
adjacent in the final handoff, not deciding it here.

## 2. Templates (exact pseudo-code)

### 2.1 T1 — Donchian breakout

```
H(N) = max(high[i-N : i])          # previous N bars, excludes bar i (current)
L(M) = min(low[i-M : i])

entry: close[i] > H(N)             # N default 20
stop:  entry_ref - k * ATR(14)     # k default 2
exit:  close[i] < L(M)             # M default 10, OR stop hit (checked per §1.5)
filter (optional): close[i] > SMA(200)
```

**Known-answer vector T1** (`N=3`, `M=2`, `k=2`, no SMA filter, ATR seeded
elsewhere as `2.0` for this vector so the arithmetic stays simple):
closes `[10, 11, 9, 10, 13]`, so at bar index 4 (0-based), `H(3) =
max(close[1..3]) = max(11, 9, 10) = 11`. `close[4] = 13 > 11` → entry signal
at bar 4's close. `entry_ref = 13` (the close that triggered it — the
template reads its own trigger price as the reference, not the next bar's
open, which is a separate, later concept: the *fill* price). `stop = 13 - 2*2.0
= 9`. Fill happens at bar 5's open (not given in this vector — this vector
only proves entry/stop computation, not the fill, which is TEST_SPEC_BACKTEST's
job).

### 2.2 T2 — MA trend + ADX

```
cross_up: EMA(F)[i-1] <= EMA(S)[i-1] and EMA(F)[i] > EMA(S)[i]   # F=20, S=50 default
entry:    cross_up and ADX(14)[i] > A                             # A default 25
stop:     entry_ref - k * ATR(14)                                 # k=2
exit:     EMA(F)[i] < EMA(S)[i]  OR  stop hit
```

The crossover check requires **both** the previous and current bar's EMA
values — so T2's effective warm-up is `max(EMA(S), ADX(14)) + 1` bars (one
extra bar beyond §1.2's table, to have a "previous" EMA pair to compare).

### 2.3 T3 — Cross-sectional momentum

```
score[symbol] = (close[t-S] / close[t-S-L]) - 1      # return over L days, skipping most recent S days
                                                       # L default 126, S default 21
universe = apply_liquidity_filters(all_symbols)
eligible = [s in universe if close[s] > SMA(200)[s]]
selected = top_K(eligible, by=score, K=20)
weight   = 1/len(selected)                            # equal weight default; inverse-vol is a named variant, not default

rebalance: every R trading days (default 21)
exit:      symbol drops out of top 2K  OR  stop (if the instance config sets one)
```

T3 has no bar-level `stop`/`target` on the signal in the usual sense — "stop"
here, if configured, is a portfolio-level per-position risk cap applied at
rebalance time, not an intrabar trigger. This is already slightly
inconsistent with STRATEGIES.md §3's "or stop" phrasing for T3, which this
spec resolves by treating T3's stop as **optional and rebalance-frequency
only** (never checked intrabar) — the opposite of every other template.
Flagging this explicitly so an implementer doesn't accidentally wire T3
through the same intrabar stop-check path as T1/T2/T4/T6.

### 2.4 T4 — RSI(2) pullback

```
entry: close[i] > SMA(200)[i]  and  RSI(2)[i] < r        # r default 10
stop:  entry_ref - k * ATR(14)                             # k=2.5
exit:  close[i] > SMA(5)[i]  OR  RSI(2)[i] > 70  OR  bars_held >= 5  OR  stop hit
```

**Known-answer vector T4** (`r=10`, isolating just the RSI/SMA(200) entry
condition — not a full 200-bar series, since that's impractical to hand-
verify; this vector assumes `SMA(200)` and `RSI(2)` are given, not derived,
to test the entry *rule*, not the indicators themselves — indicator
correctness is §1.3's job): given `close[i] = 105`, `SMA(200)[i] = 100`
(so `close > SMA(200)` holds) and `RSI(2)[i] = 8` (`< 10`) → entry fires.
Flip `RSI(2)[i]` to `12` → no entry, all else equal — this is the test that
proves the `AND` is implemented as an `AND`, not an `OR` (an easy transcription
bug when porting prose rules to code).

### 2.5 T5 — Opening range breakout

```
range_high, range_low = high/low of first R minutes after open   # R default 15, on closed 5-min bars
cutoff = 11:30 local market time                                  # default; configurable
entry:  first close > range_high * (1 + b)   and   now <= cutoff  # b default 0.05%
stop:   range_low                                                 # variant: range midpoint
target: entry_ref + m * (range_high - range_low)                  # m default 1.5 — MANDATORY (§1.7)
exit:   target hit  OR  stop hit  OR  square_off_time reached (flat, no re-entry)
max:    one trade per symbol per day
```

The "first close above range_high*(1+b) before cutoff" condition means T5
can only ever fire once per symbol per day by construction (after the first
qualifying close, the opening range itself doesn't change, but the "max one
trade" rule still needs enforcing explicitly in code, because nothing stops
a second, later breakout of the *same* range from also satisfying the
entry condition if the first trade already stopped out intraday).

### 2.6 T6 — Bollinger mean reversion

```
entry: close[i] < lowerBand(N, k)[i]  and  ADX(14)[i] < 20     # N=20, k=2 default
stop:  entry_ref - 1.5 * ATR(14)
exit:  close[i] >= middleBand(N)[i]  OR  bars_held >= 10  OR  stop hit
```

### 2.7 F1 — Candlestick confirmation filter (never standalone)

```
body  = abs(close - open)
range = high - low
upper = high - max(open, close)
lower = min(open, close) - low

hammer:            lower >= 2*body  and  upper <= 0.3*body  and  body in upper third of range
                   and preceding_downtrend (e.g. close < SMA(20) over recent bars)
bullish_engulfing: prev.bearish  and  curr.bullish  and  curr.body fully covers prev.body
doji:              body <= 0.1*range                           # context only, never a standalone signal
morning_star:      bearish, then small-body gapping/closing lower,
                   then bullish closing above first candle's midpoint
```

F1 is applied as an **additional required condition** on a host template's
entry (e.g. "T4 entry only if a hammer or bullish engulfing printed on the
entry bar") — it never generates a `Signal` by itself, and whether it helps
at all is a backtest question (STRATEGIES.md §3), not assumed here.

**Degenerate input:** `range == 0` (a bar with `high == low`, i.e. no trading
occurred — a halted/illiquid symbol) makes `upper`/`lower`/`body` all zero,
so `hammer`'s `lower >= 2*body` becomes `0 >= 0` (true) but `body in upper
third of range` is undefined for a zero-height range. Rule: **a zero-range
bar never satisfies any F1 pattern** — check `range > 0` first and
short-circuit to "no pattern" if not, rather than letting a `0/0`-shaped
comparison silently pass.

## 3. What this spec does NOT do (explicitly out of scope)

- Full hand-calculated known-answer vectors for T2/T3/T5/T6/F1 — the pseudo-
  code above is exact enough to derive them from, but doing so by hand here
  risked a transcription error worse than no vector; whoever writes
  `TEST_SPEC_STRATEGIES.md` should generate these from a spreadsheet or a
  reference implementation, not copy an unverified one from this doc.
- The `ExitRequest`/exit-risk-check gap in §1.7 — flagged, not resolved.
- Parameter sweep ranges beyond the defaults already in STRATEGIES.md §3 —
  unchanged from that document.
