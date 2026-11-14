# TEST SPEC — Strategies

Status: P0 deliverable (BUILD_ORDER.md item 7, strategies slice — the last
remaining piece). Builds on `STRATEGY_SPEC.md`'s exact pseudo-code. T1/T4
already have full hand-calculated known-answer vectors there; this spec
gives the **test case list** for every template (what must be tested, not
invented numbers) — T2/T3/T5/T6/F1's actual numeric vectors are explicitly
deferred to whoever implements them, with a spreadsheet or reference
calculation, not hand-derived here under time pressure (same reasoning
`STRATEGY_SPEC.md` §3 already gives).

## 1. Shared test shape (every template)

Every template gets, at minimum:

1. **Entry fires exactly on the boundary condition, not one bar early or
   late.** Construct a series where the condition becomes true at bar `k`
   and assert: no signal at any bar `< k`, exactly one signal at bar `k`
   (not a signal every bar thereafter while the condition stays true, unless
   the template explicitly allows re-entry — most don't, since a position is
   already open).
2. **AND vs. OR logic is actually AND/OR, not accidentally swapped.** For
   any template combining two conditions with `AND` (e.g. T4's
   `close>SMA(200) AND RSI(2)<r`), construct one case where only the first
   holds, one where only the second holds, and one where both hold — only
   the last fires. This is `STRATEGY_SPEC.md` §2.4's T4 vector generalized
   to every multi-condition template (T2, T6).
3. **Warm-up is respected per `STRATEGY_SPEC.md` §1.2** — one bar before the
   template's full warm-up, zero signals possible regardless of price
   action; this is a parametrized test reused across all six templates
   (same harness, different indicator warm-up counts).
4. **The stop computation uses `ATR(14)` at the signal bar, not a stale or
   future value** — construct a series where `ATR(14)` changes materially
   between the signal bar and the next bar, and assert the stop was fixed
   using the signal bar's `ATR(14)`, never recomputed at fill time (a stop
   that silently moves between signal and fill would be its own look-ahead-
   adjacent bug, even though AGENTS.md's no-look-ahead rule is usually
   stated about entries).
5. **Zero-range / degenerate-input cases don't crash or silently misfire**
   (ties to `STRATEGY_SPEC.md` §1.4's zero-denominator rules) — one test per
   template feeding a flat-price run long enough to hit the
   `ATR==0`/`RSI==50` degenerate cases, asserting no signal fires (§1.4: a
   zero-width stop is impossible by construction, so the template simply
   can't produce a valid signal that bar).

## 2. Per-template test list (no invented numeric vectors beyond
`STRATEGY_SPEC.md`'s own T1/T4)

- **T1 Donchian:** boundary test at `close == H(N)` exactly (must NOT fire —
  the rule is strictly `>`, equality is not a breakout); the optional
  `close > SMA(200)` filter actually gates entries when enabled (construct a
  case that would fire without the filter and doesn't with it); exit fires
  on `close < L(M)` independently of whether the stop would also have fired
  that bar (to isolate the exit-condition path from the stop path before
  testing their interaction via `STRATEGY_SPEC.md` §1.5's precedence rule).
- **T2 MA+ADX:** the crossover must be a **transition** (`EMA(F)<=EMA(S)`
  at `i-1`, `EMA(F)>EMA(S)` at `i`), not just "currently above" — construct
  a series where `EMA(F)>EMA(S)` for several bars in a row and assert only
  the first bar of that run is a signal, not every bar; `ADX(14)>A` gates
  independently (a crossover with low ADX must not fire — shared-shape test
  #2 above, applied here).
- **T3 Momentum:** score computation `(close[t-S]/close[t-S-L])-1` on a known
  short series (this one vector IS simple enough to hand-check: if
  `close[t-S]=110` and `close[t-S-L]=100`, score `=0.10`); top-`K` selection
  is actually a rank, not a threshold (two universes of different sizes
  with the same relative ordering should select the same relative
  membership); drop-out-of-top-`2K` exit fires based on the **current**
  rebalance's ranking, not a stale one from before the most recent
  rebalance.
- **T4 RSI(2) pullback:** `STRATEGY_SPEC.md` §2.4's vector covers the entry
  AND-logic; additionally test the **three independent exit triggers**
  (`close>SMA(5)`, `RSI(2)>70`, `bars_held>=5`) fire in isolation — a case
  where only one is true should exit, proving they're combined with `OR`,
  not `AND` (the opposite transcription bug from the entry's `AND`).
- **T5 ORB:** the opening range is fixed once computed and never recomputed
  intraday (construct a case where a later 5-minute bar has a wider
  high/low than the opening range and assert the breakout level didn't
  move); "first close above range_high*(1+b)" fires on the **first**
  qualifying bar even if an earlier bar's *intrabar* high also exceeded the
  level but its close didn't (the rule is close-based, not intrabar-based,
  unlike the stop/target checks which ARE intrabar — this distinction is
  easy to blur and deserves its own test); the one-trade-per-symbol-per-day
  cap actually blocks a second breakout of the same range after an early
  stop-out (`STRATEGY_SPEC.md` §2.5's note).
- **T6 Bollinger reversion:** `close < lowerBand` strictly (equality doesn't
  fire, same reasoning as T1); the `ADX(14)<20` filter actually excludes
  trending regimes (construct a case where price is below the lower band
  but ADX is high — must not fire); exit triggers (`middleBand`,
  `bars_held>=10`, stop) combine with `OR` — same pattern as T4.
- **F1 Candlestick confirmation:** each of hammer/engulfing/doji/morning-star
  tested against a hand-built OHLC sequence matching its definition exactly
  and a "near miss" that fails exactly one of the sub-conditions (e.g. a
  hammer-shaped candle with `upper = 0.4*body`, just over the `0.3*body`
  threshold) — proving the thresholds are real boundaries, not vestigial;
  the zero-range degenerate case from `STRATEGY_SPEC.md` §2.7 ("a zero-range
  bar never satisfies any pattern") gets its own explicit test, since it's
  the one case that could otherwise pass a naive `0 >= 0` comparison by
  accident.

## 3. Instance-registry and lifecycle tests (`STRATEGIES.md` §6, §8)

- A strategy instance's `status` can only move forward through
  `idea -> coded -> in_sample -> out_of_sample -> robust -> paper ->
  approval -> auto -> retired` (or be retired from anywhere) — test this as
  a state-machine table, the same pattern `TEST_SPEC_RISK.md` §6 uses for
  `Order`.
- A **live** instance's parameters are immutable — changing any `params`
  value must require creating a new version (new instance id or version
  field), never an in-place edit of a `status: auto` row in
  `config/strategies.yaml`. Test: attempting to load a registry where a
  live instance's params changed between two loads (without a version bump)
  is flagged as a config error, not silently accepted.

## 4. What this spec does NOT do

- Provide numeric known-answer vectors for T2/T3/T5/T6/F1 beyond the tiny
  T3 score example in §2 — `STRATEGY_SPEC.md` §3 already explains why: a
  rushed hand-calculation risks being wrong in a way that's worse than no
  vector at all. Whoever implements each template should derive its vector
  from a spreadsheet or a trusted reference calculation and add it here (or
  to its own test file) at that time.
- The Tier B scanner's own backtest methodology (`STRATEGIES.md` §10's
  "replay history day by day, measure forward 5-10 day outcomes") — that's
  P4 work, not yet specified in test form.
