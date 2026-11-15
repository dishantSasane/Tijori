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
- Universe: the point-in-time Top 50 from `RESEARCH_UNIVERSE.md`; this is
  unusable until its source rights, schema and coverage gates are cleared.
- Variations: at most **3 frozen variants per family**, including the baseline.
  No Cartesian product across parameter axes. Every attempted run, including
  failed runs, counts toward the pre-registered family and experiment totals.
- Version: `p1-daily-v1`. Any rule, parameter, sizing, universe, cost or data
  change requires a new catalog version and is counted as a new research
  decision.

## Frozen candidates

| ID | Family | Variants (all others fixed) | Rule |
|---|---|---|---|
| `cash-v1` | Cash baseline | one | Hold cash; zero trades and zero gross market return. Costs are zero. |
| `buy-hold-v1` | Buy-and-hold comparator | one | Buy at first eligible next open; hold to final close; no universe rebalance; include declared costs. Report separately because this is not a strategy instance. |
| `t1-donchian-v1` | T1 breakout | `N=20,M=10,k=2`; `N=10,M=10,k=2`; `N=40,M=10,k=2` | Existing `STRATEGY_SPEC.md` T1 entry/exit, ATR(14) stop, closed-bar signal, next-open fill. No optional SMA filter. |
| `t2-trend-adx-v1` | MA + ADX trend | `F=20,S=50,A=25,k=2`; `F=10,S=50,A=25,k=2`; `F=20,S=100,A=25,k=2` | Existing T2 exact rule; EMA cross-up and ADX(14) threshold, ATR(14) stop. |
| `t3-momentum-v1` | Cross-sectional momentum | `(L=126,S=21,K=20,R=21)`; `(L=63,S=21,K=20,R=21)`; `(L=252,S=21,K=20,R=21)` | Existing T3 rule; price above SMA(200), equal weight, exit below top `2K`, same universe and monthly/daily rebalance semantics frozen by its implementation contract. No inverse-volatility variant. |
| `t4-rsi-pullback-v1` | T4 mean reversion | `r=10,k=2.5`; `r=5,k=2.5`; `r=15,k=2.5` | Existing T4 entry/exit and 5-bar time stop; ATR(14) stop; no added confirmation filter. |
| `t5-orb-v1` | Opening-range breakout | intraday catalog required | P1 includes intraday research from the start. Freeze exact ORB variants, closed-bar event order, session handling, 1m/5m source selection and costs in an intraday catalog before any ranking. The daily-only catalog below excludes ORB because it is a different timeframe family, not because intraday is deferred. |
| `t6-bollinger-v1` | Mean reversion | `N=20,k=2`; `N=20,k=1.5`; `N=20,k=2.5` | Existing T6 entry/exit with ADX(14)<20, ATR(14) stop multiple 1.5 and 10-bar time stop. Here `k` is Bollinger width only. |
| `rpf-pullback-v1` | Regime-gated failed-breakout pullback | one fixed hypothesis | The exact hypothesis in `BUILD_ORDER.md`; its complete event order, filters and stop must be expanded into a versioned executable spec before any run. Until then it is **not executable and not in the ranking set**. |

The daily ranking catalog contains 7 executable entries (cash, buy-and-hold, T1,
T2, T3, T4, T6) with 17 executable variants: 2 fixed baselines and 15
strategy variants. The two baselines are reference comparators, not tested
hypotheses.
The intraday catalog is a required parallel P1 deliverable; it must be frozen
before intraday results are generated. T5 is excluded from the daily sample.
The original self-designed RPF idea remains a separate
pre-registered hypothesis that must be made fully mechanical before it can
enter the family count; it cannot be silently added after observing rankings.

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
catalog_version: p1-daily-v1
baseline_ids: [cash-v1, buy-hold-v1]
strategy_families:
  t1-donchian-v1: 3
  t2-trend-adx-v1: 3
  t3-momentum-v1: 3
  t4-rsi-pullback-v1: 3
  t6-bollinger-v1: 3
  rpf-pullback-v1: 0
  t5-orb-v1: 0
hypothesis_count: 15
```

RPF is not yet executable (zero included variants). The statistical family is
15. The two fixed
baselines are excluded. Any future RPF variants require a new catalog version
and updated family count before data is viewed.
