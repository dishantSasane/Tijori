# TEST SPEC — Candle Builder and Indicators

Status: P0 deliverable (BUILD_ORDER.md item 7, candles/indicators slice).
Covers the "ticks -> candles" layer and the incremental-vs-batch indicator
equivalence guarantee (ARCHITECTURE.md §4). Pairs with `TEST_SPEC_BACKTEST.md`
(fills) and `STRATEGY_SPEC.md` §1 (warm-up/Wilder-seed semantics, which this
spec's indicator tests also exercise).

## 1. Candle builder: ticks -> closed bars

1. **Bar boundary alignment:** for timeframe `5m`, a tick at `09:17:32` IST
   belongs to the bar whose `ts_open_utc` is the floor of that instant to the
   nearest 5-minute boundary **in UTC**, not in market-local time (AGENTS.md
   §6: UTC internally) — known-answer: `09:15:00` IST = `03:45:00` UTC on a
   non-DST date; a tick at `03:47:32` UTC belongs to the bar opening
   `03:45:00` UTC, closing (and becoming emittable) at `03:50:00` UTC.
2. **Bar closes exactly at boundary, not after the next tick arrives:** a
   builder that only closes a bar when it sees the *first tick of the next
   bar* has a latency bug (the closed bar isn't available until an arbitrary
   amount of time after it should be) — test with a scheduled/timer-driven
   close at `bar_open + timeframe`, independent of tick arrival, and a
   separate test proving a bar with **zero ticks** in its window still closes
   (as a zero-volume bar carrying forward the previous close as
   open/high/low/close — never silently skipped, since a missing bar would
   break every fixed-length lookback indicator downstream).
3. **Out-of-order / late tick within the current forming bar:** a tick
   timestamped *before* the latest tick already processed, but still within
   the current bar's window (network reorder, not a stale replay) — the
   builder must still fold it into O/H/L/V correctly (high/low are
   order-independent; the *open* is fixed at the window's first-seen tick
   only if ticks are expected in order — if genuine reordering within the
   window is possible, `open` should be defined as "price of the
   chronologically-earliest tick by its own timestamp," not "price of the
   first tick processed." Pick one explicitly in the implementation and test
   that exact rule; this spec flags that the two definitions diverge under
   reordering and must not be left ambiguous.
4. **Tick arrives for a bar that has already closed and been emitted (late/
   stale, e.g. a delayed retry):** must **not** reopen or mutate an already-
   emitted `Candle` (contracts are `frozen=True`, so this is partly enforced
   by the type system already) — the late tick is dropped and logged, never
   silently folded into a *new* bar's stats either.
5. **Only closed bars ever come out of `poll_closed_candles()`:** property
   test — for any sequence of ticks fed to `FakeDataFeed`/a real builder, no
   returned `Candle` has `ts_open_utc + timeframe > as_of` (the moment the
   poll happened). This is the test that makes ADAPTERS.md §1's "no forming-
   bar accessor" guarantee concrete instead of just a docstring claim.
6. **Daily (`D1`) bar from an end-of-day provider file (not built from
   ticks):** the bhavcopy/daily-bars path constructs a `Candle` directly from
   the provider's OHLCV row — test that this path produces a `Candle` that
   validates identically to a tick-built one (same contract, same
   invariants) and that `source` distinguishes the two origins for audit
   purposes (`"nse_bhavcopy"` vs. `"tick_builder"`, e.g.).

## 2. Indicator incremental == batch equivalence

For every indicator (`SMA`, `EMA`, `RSI`, `ATR`, `ADX`, `Bollinger`,
`Donchian`, `VWAP`): a single property-test harness, parametrized per
indicator —

```
given a random closed-bar series of length >= 3 * warmup(indicator):
    batch_values = batch_impl(full_series)
    incremental = IncrementalIndicator()
    incremental_values = [incremental.update(bar) for bar in full_series]
    assert incremental_values == batch_values   # bar-for-bar, Decimal-exact
```

"Decimal-exact" matters: if either implementation does an intermediate
`float` conversion, this test will eventually catch a rounding divergence
that a looser `pytest.approx` comparison would hide — AGENTS.md §6 bans
`float` on these paths for exactly this reason, so the equivalence test
should assert exact equality, not approximate.

7. **Each indicator's own known-answer case** (hand-calculable, small):
   - `SMA(3)` on closes `[1,2,3,4,5]` → `[None,None,2,3,4]` (first two bars
     have no value; §1.2 of STRATEGY_SPEC.md's warm-up table).
   - `EMA(3)` on the same series: seed at bar index 2 = `SMA(3) = 2`; bar 3:
     `alpha = 2/(3+1) = 0.5`; `EMA = 0.5*4 + 0.5*2 = 3`; bar 4:
     `EMA = 0.5*5 + 0.5*3 = 4`.
   - `ATR(2)` Wilder: already given in `STRATEGY_SPEC.md` §1.3 — reuse that
     exact vector here rather than inventing a second one.
   - `RSI(2)` Wilder on closes `[10, 11, 9, 10, 13]`: changes `[+1,-2,+1,+3]`;
     seed (`n=2`) `avg_gain = mean(1,0) = 0.5` (loss on bar 2 is `0`, gain is
     `1`... concretely: change[1]=+1 (gain=1,loss=0), change[2]=-2 (gain=0,
     loss=2) → seed `avg_gain=0.5`, `avg_loss=1.0` at index 2; index 3
     (change=+1, gain=1,loss=0): `avg_gain=(0.5*1+1)/2=0.75`,
     `avg_loss=(1.0*1+0)/2=0.5` → `RS=1.5`, `RSI=100-100/2.5=60`.
   - `Bollinger(3, k=2)` on closes `[1,2,3,4,5]` at index 4: `middle=SMA(3)=4`
     (closes 3,4,5), `stdev` of `[3,4,5]` (population, per the template's own
     convention — **must be stated explicitly in the implementation**:
     population vs. sample stdev give different bands, and the spec doesn't
     yet pick one; flagged as an open micro-decision for whoever implements
     this, default to population stdev unless STRATEGIES.md says otherwise
     — it doesn't, so this is genuinely open) `= 0.8165`; `upper = 4 +
     2*0.8165 = 5.633`, `lower = 4 - 2*0.8165 = 2.367`.
   - `Donchian H(3)` already covered by `STRATEGY_SPEC.md`'s T1 vector.
   - `VWAP`: not used by any Phase-1 template (STRATEGIES.md §4, "later") —
     no known-answer case needed yet; add one when a template uses it.

## 3. Look-ahead tests (invariant I13)

8. **Truncated-data test:** compute a strategy's signals on the full series
   `bars[0:N]`. Separately, compute signals on the truncated series
   `bars[0:k]` for every `k < N`. Assert: for every `k`, the signals produced
   on `bars[0:k]` are **identical** (same signals, same values) to the
   subsequence of full-series signals whose `bar_ts_utc <= bars[k-1].ts_open_utc`.
   Any difference means some computation depended on data that hadn't
   "happened yet" relative to that truncation point — this is the single
   most important test in the whole system, since a silent look-ahead bug
   produces backtest results that look great and are entirely fake.
9. **Indicator warm-up boundary under truncation:** combine with
   `STRATEGY_SPEC.md` §1.2's vector — truncating to exactly `warmup-1` bars
   must produce zero signals; truncating to `warmup` bars may (not must)
   produce one, depending on whether the entry condition happens to be true
   at that exact bar.
10. **Candle builder never emits a bar using a tick from after that bar's
    close:** a focused version of scenario 8, at the tick level rather than
    the signal level — feed the builder every tick, but ask it for
    `poll_closed_candles()` *before* feeding the tick that would close the
    current bar; assert that bar is absent from the result (not emitted
    early with partial data).
