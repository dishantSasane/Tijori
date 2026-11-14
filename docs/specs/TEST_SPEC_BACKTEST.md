# TEST SPEC — Backtester

Status: P0 deliverable (BUILD_ORDER.md item 7, backtester slice). Builds on
`STRATEGY_SPEC.md` §1 (fill timing, same-bar stop-first precedence,
final-bar-unfilled handling) and `RISK_ENGINE_SPEC.md` §9 (gap handling).
Extends `STRATEGY_SPEC.md`'s T1 known-answer vector through to an actual
fill, since BUILD_ORDER.md names T1 (+T4) as the first scorecard.

## 1. Fill mechanics (known-answer)

**Setup:** continuing `STRATEGY_SPEC.md` §2.1's T1 vector — signal at bar 4
close (`close=13`, `entry_ref=13`, `stop=9`). Market profile: `brokerage=20`
(flat, India-equity placeholder from `MARKETS.md`), `slippage_bps=5` (buy
fills 5 bps *worse* than the reference price — against the trader, per
AGENTS.md §4.5 "costs and slippage," never in the trader's favor by default).

**Bar 5 (the fill bar):** `open=13.2, high=13.5, low=13.0, close=13.3`.

```
fill_price = bar5.open * (1 + slippage_bps/10000)       # buy: worse = higher
           = 13.2 * 1.0005 = 13.2066
qty        = (from RiskDecision — not computed here, assume 100 for this vector)
cost       = brokerage = 20 (flat, India placeholder)
notional   = qty * fill_price = 1320.66
```

1. **Known-answer fill test:** assert `fill_price == Decimal("13.2066")`
   exactly (not `13.21` — no intermediate rounding until the final stored
   value, and *that* rounding, if any, must be to the market's tick size,
   specified separately per market profile, not an arbitrary 2dp).
2. **Entry at next-open, never at signal-bar close:** a backtester that fills
   at `13.0` (bar 4's close/entry_ref) instead of `13.2066` (bar 5's open +
   slippage) has a look-ahead bug — this is the single test that would catch
   someone "optimizing" the backtester to fill at the signal price for
   convenience, which silently deletes the no-look-ahead guarantee.

## 2. Stop-first precedence (known-answer)

**Setup:** position opened per §1 above (`entry=13.2066, stop=9, qty=100`,
no target for T1). Bar 6: `open=9.5, high=14, low=8, close=13`. This bar's
range touches both well above any plausible target *and* below the stop.

3. **Stop-first test:** per `STRATEGY_SPEC.md` §1.5, the exit is recorded as
   a stop-out at `stop=9` (not at the bar's high, not at close `13`), with
   `qty=100`, realized P&L `= 100*(9 - 13.2066) - 20 (exit brokerage) =
   -420.66 - 20 = -440.66`. The high of `14` on the same bar is **never**
   used to compute a better outcome — this is the test that would catch an
   implementation that scans a bar's full range for "the best possible exit"
   instead of applying the stated precedence rule.
4. **Stop hit at the fill bar itself (§1.5's "no grace period"):** separate
   vector — entry fills at bar 5 open `13.2066`; bar 5's own low is `13.0`
   (above the stop of `9`, so this specific vector doesn't stop out
   same-bar) — construct a **second** vector where bar 5's low is `8.5`
   (below stop) to prove a same-bar stop-out is detected and recorded, not
   deferred to bar 6 under an assumption that "the position needs at least
   one full bar before it can be stopped."

## 3. Gap handling (known-answer, from RISK_ENGINE_SPEC.md §9)

5. **Gap through stop:** reuse RISK_ENGINE_SPEC.md §9's exact vector —
   approved `qty=100`, `stop=2450` (`entry=2500`), next bar opens at `2400`.
   Fill at `2400` (with slippage/costs applied on top, per §1 above — the
   spec's §9 vector omits costs for simplicity; this test spec's version
   must include them to be a real backtester test, not just a risk-sizing
   one). Assert: (a) the position is immediately recorded as stopped out at
   the open price `2400` (not at the nominal stop `2450` — the stop is a
   broker-held instruction that triggers at `2450`, but if the market never
   traded there, the real/simulated fill is at the gapped price), (b) an
   audit event `gap_risk_realized` exists with `approved_risk=5000,
   realized_risk=10000` exactly as specified.
6. **Gap away but not through stop:** open at `2480` (above stop `2450`,
   below `entry=2500`) — ordinary unfavorable-but-bounded fill at `2480`,
   no `gap_risk_realized` event, stop remains live for a future bar.

## 4. Final-bar unfilled signal (known-answer, from STRATEGY_SPEC.md §1.6)

7. **Backtest exclusion:** a series of exactly 5 bars where bar 4 (the last
   one) produces a T1 entry signal (per §2.1's vector, which fires at bar
   index 4 of a 5-bar series — i.e. this is literally the same series with
   no bar 5 appended). Assert: zero trades in the scorecard, one logged
   "unfilled, data ended" entry, and the scorecard's `trades` count excludes
   it entirely (not counted as a loss via some default fill assumption).

## 5. Second reference backtester equivalence

8. **Cross-implementation agreement:** run both the primary (presumably
   vectorized, Polars/pandas) and the second, deliberately simple/slow
   reference backtester (ADR/BUILD_ORDER.md P1: "second reference
   backtester, slow, simple") over the same input series for T1 and T4.
   Assert **identical** trade lists: same entry bar, same fill price (exact
   `Decimal` equality, not approximate), same exit bar/reason, same P&L.
   Any divergence means one of the two has a bug — which one is wrong isn't
   decided by this test; a third, hand-traced vector (§1-§4 above) is the
   tie-breaker.
9. **Known-answer vectors (§1-§4) must pass identically on both
   implementations** — the known-answer cases aren't just acceptance tests
   for "a" backtester, they're the shared ground truth both implementations
   are measured against.

## 6. Costs and slippage as market-profile data, not hardcoded

10. **Market-profile-driven costs:** the same fill-mechanics test (§1) run
    with a different `config/markets.yaml` profile (e.g. US equities:
    `commission_per_order_usd=0`) must produce a different `cost` in the
    result purely from config, with zero code change — proving costs aren't
    hardcoded per market inside the backtester engine (ARCHITECTURE.md §1's
    "adding a market = adapters + profile, not editing core" rule extends to
    the backtester's cost model).

## 7. Walk-forward split (structural, no numeric vector yet)

11. **No leakage across the IS/OOS boundary:** given a date range split into
    in-sample `[start, split)` and out-of-sample `[split, end)` windows, a
    strategy parameter chosen using only in-sample performance must be
    applied unchanged to out-of-sample data — test that the backtester API
    makes it *structurally* awkward to compute a metric over `[start, end)`
    and then claim it as "out-of-sample" (e.g. the OOS runner only accepts a
    pre-fixed parameter set, never a metric-optimization callback over the
    full range). This is a harness-design test, not a numeric one; a
    concrete known-answer walk-forward vector is deferred (would need a
    longer series than is practical to hand-verify here) — flagged as a
    follow-up, same reasoning as `STRATEGY_SPEC.md` §3's T2/T3/T5/T6
    vectors.
12. **Embargo at the IS/OOS boundary (required, by construction):** because
    fills happen at the *next* bar's open, a signal on the last in-sample bar
    (`split - 1`) would fill on the first out-of-sample bar (`split`) and the
    resulting trade would belong to neither window honestly. Rule: the
    walk-forward splitter takes `embargo_bars` (config; default `1`, the
    exact lookahead of next-open fills) and

    - a signal is **in-sample** only if its signal bar index `s` satisfies
      `start <= s < split - embargo_bars` (so with the default, the last IS
      bar can never produce an IS trade);
    - a signal is **out-of-sample** only if `split <= s < end -
      embargo_bars`. Indicators for an OOS signal may read bars before
      `split` (that is history, not leakage); what they may not do is have
      their *parameters* tuned on bars `>= split` — that is §7.11's check;
    - a signal with `split - embargo_bars <= s < split` (or `end -
      embargo_bars <= s < end`) is recorded as **unfilled, embargo** —
      counted in **neither** window's trades, logged like §4's "unfilled,
      data ended" (distinct reason) so the signal count still reconciles.

    These are the only three outcomes. The splitter must hand each runner
    only its own bars (`bars[start:split]`, `bars[split:end]`); a fill can
    then never cross `split` because the fill bar does not exist in the
    runner's slice. The embargo is what makes the dropped signal visible and
    correctly labelled rather than relying on the §4 "data ended" path.

    Known-answer (pseudocode, extends §1's T1 vector): take the 6-bar series
    of §1 (`close = [10, 11, 9, 10, 13, 13.3]`, bar 5 as given) and set
    `start=0, split=5, end=6, embargo_bars=1`. T1 fires at bar 4 (`13 > 11`).

    ```
    is_result, oos_result = walk_forward(bars, start=0, split=5, end=6, embargo_bars=1)
    assert is_result.trades == []                    # bar 4 is inside the embargo
    assert oos_result.trades == []                   # bar 4 is not an OOS signal bar
    assert is_result.unfilled == [Unfilled(bar=4, reason="embargo")]
    assert oos_result.unfilled == []
    # The failure this catches: a splitter that runs the strategy over the full
    # series and then buckets trades by entry bar WOULD fill bar 4's signal at
    # bar 5's open (13.2066) and report one trade — in IS, OOS, or both.
    assert all(t.signal_bar != 4 for t in is_result.trades + oos_result.trades)
    ```

## 8. What this spec does NOT cover

- Candle-builder/indicator correctness — `TEST_SPEC_CANDLES.md`.
- Strategy entry/exit *rule* correctness (is RSI(2) actually below 10?) —
  `STRATEGY_SPEC.md` + its own future `TEST_SPEC_STRATEGIES.md`.
- Live execution/reconciliation (this is backtest-only; live fills go through
  a real `Broker` adapter, not this simulated path) — P2/P3.
