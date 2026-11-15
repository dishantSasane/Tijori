# P1 pre-registered candidate catalog

Status: frozen rule definitions for the P1 study, covering daily swing and
intraday families from the start. No candidate is claimed profitable. No
backtest/ranking may run until P1a data and split gates
are satisfied. This catalog is not permission to tune parameters after seeing
results.

## Scope and fixed assumptions

- Market: NSE cash equities, long-only; daily families use closed daily bars
  and next-session open fills; intraday families use closed 1-minute/5-minute
  bars and next-bar fills with the shared cost/slippage model.
- Per-trade comparison sizing: 1% of ₹1,00,000 placeholder capital as agreed
  in ADR-0026. This is a research comparison assumption, not an account config.
- Holding horizon: P1 tests daily swing and intraday from the start. Exact
  intraday holding/exit rules belong in the intraday catalog; the unresolved
  owner choice is which horizon to prioritize for promotion, not whether to
  collect intraday data.
- First-pass pilot universe: fixed RELIANCE, INFY, TCS, HDFCBANK and ICICIBANK.
  This bounded sample has survivorship and concentration bias; conclusions are
  pipeline validation/exploratory evidence for these five names only, not an
  India-wide strategy claim. The Top-50 point-in-time universe in
  `RESEARCH_UNIVERSE.md` remains a follow-up pending a permitted complete
  historical source.
- Variations: at most **3 frozen variants per family**, including the baseline.
  No Cartesian product across parameter axes. Every attempted run, including
  failed runs, counts toward the pre-registered family and experiment totals.
- Version: `p1-daily-v2`. Any rule, parameter, sizing, universe, cost or data
  change requires a new catalog version and is counted as a new research
  decision.

## Frozen candidates

| ID | Family | Variants (all others fixed) | Rule |
|---|---|---|---|
| `cash-v1` | Cash baseline | one | Hold cash; zero trades and zero gross market return. Costs are zero. |
| `buy-hold-v1` | Buy-and-hold comparator | one | Buy at first eligible next open; hold to final close; no universe rebalance; include declared costs. Report separately because this is not a strategy instance. |
| `t1-donchian-v1` | T1 breakout | `N=20,M=10,k=2`; `N=10,M=10,k=2`; `N=40,M=10,k=2` | Existing `STRATEGY_SPEC.md` T1 entry/exit, ATR(14) stop, closed-bar signal, next-open fill. No optional SMA filter. |
| `t2-trend-adx-v1` | MA + ADX trend | `F=20,S=50,A=25,k=2`; `F=10,S=50,A=25,k=2`; `F=20,S=100,A=25,k=2` | Existing T2 exact rule; EMA cross-up and ADX(14) threshold, ATR(14) stop. |
| `t4-rsi-pullback-v1` | T4 mean reversion | `r=10,k=2.5`; `r=5,k=2.5`; `r=15,k=2.5` | Existing T4 entry/exit and 5-bar time stop; ATR(14) stop; no added confirmation filter. |
| `t5-orb-v1` | Opening-range breakout | `m=1.0`; `m=1.5`; `m=2.0` | Exact 5-minute session/event ordering and costs are in `P1_INTRADAY_CANDIDATES.md`; only the target multiple changes. |
| `t6-bollinger-v1` | Mean reversion | `N=20,k=2`; `N=20,k=1.5`; `N=20,k=2.5` | Existing T6 entry/exit with ADX(14)<20, ATR(14) stop multiple 1.5 and 10-bar time stop. Here `k` is Bollinger width only. |

The daily ranking catalog contains cash, buy-and-hold, T1, T2, T4 and T6. The
separate intraday catalog contains three frozen T5 variants. Across both
timeframes there are 17 executable variants: 2 fixed baselines and 15 strategy
variants (12 daily, 3 intraday). The baselines are comparators, not tested
hypotheses. T5 is excluded from daily results. Each timeframe still requires
its own coverage and promotion analysis.

T3 cross-sectional momentum is deferred from this bounded pilot **before any
P1 result is inspected**. Its frozen `K=20`/top-`2K` rules are not meaningful
on a five-symbol universe: all symbols fit in the top 20 and none can fall
outside the top 40, so the cross-sectional rank has no selection effect. Do
not silently change K to fit the pilot; revisit T3 only in the wider-universe
follow-up with a newly frozen candidate catalog.
The self-designed regime-gated failed-breakout pullback (RPF) idea is **deferred
before any P1 result is inspected** and is not part of this P1 catalog or its
  15-trial family. If revisited later, its full rules must be specified and
versioned as a new catalog before that later study's data is inspected.

## Implementation gates

1. Tests derive expected signals from `STRATEGY_SPEC.md` and this table, not
   from observed performance.
2. A family is run on exactly the same authorized universe, date splits,
   calendar, candle adjustment version and cost model.
3. No candidate is dropped for poor results before it is recorded in the
   experiment registry. No new variants may be added to this catalog after
   result inspection; a new catalog version counts as new trials.
4. Metrics and multiple-testing treatment are defined in
   `P1_EVALUATION.md` before any result is inspected.

## Machine-readable hypothesis family

```yaml
catalog_version: p1-daily-v2
baseline_ids: [cash-v1, buy-hold-v1]
strategy_families:
  t1-donchian-v1: 3
  t2-trend-adx-v1: 3
  t4-rsi-pullback-v1: 3
  t6-bollinger-v1: 3
  t5-orb-v1: 3
hypothesis_count: 15
```

The statistical family is 15: 12 daily plus 3 intraday variants. The two fixed
baselines are excluded. T3 and RPF are deferred and have no entries in this
catalog.

## Stable executable candidate IDs

Every row in an experiment registry uses one of these immutable IDs. The
parameter tuples are duplicated in `trading.strategies.p1_catalog` and tested
against this list so a report cannot silently substitute another variant.

| Family | Candidate IDs (parameters follow the frozen table above) |
|---|---|
| T1 | `t1-donchian-n20-m10-k2-v1`, `t1-donchian-n10-m10-k2-v1`, `t1-donchian-n40-m10-k2-v1` |
| T2 | `t2-ema20-50-adx25-v1`, `t2-ema10-50-adx25-v1`, `t2-ema20-100-adx25-v1` |
| T4 | `t4-rsi2-10-atr25-v1`, `t4-rsi2-5-atr25-v1`, `t4-rsi2-15-atr25-v1` |
| T5 | `t5-orb-m1-v1`, `t5-orb-m15-v1`, `t5-orb-m2-v1` |
| T6 | `t6-bollinger20-2-v1`, `t6-bollinger20-15-v1`, `t6-bollinger20-25-v1` |
