# P1 walk-forward scorecard — Upstox daily history

Run date: 2026-11-15  
Provider: Upstox historical candles  
Coverage: 2016-11-14 through 2026-11-12  
Costs: ₹20 brokerage per order and 5 bps slippage  
Data status: `upstox_unadjusted_provisional`

## Protocol

This report uses an expanding 756-bar (approximately three-year) training
window, a 252-bar (approximately one-year) test window, a one-bar embargo, and
a 252-bar step. Each member therefore has six chronological test windows.
Signals are restricted to each test window; the preceding candles are
available only as indicator warm-up history. The final bar of a test window
cannot fill a position because fills require the next bar's open.

The label for this run is `retrospective_walk_forward`, not final
out-of-sample. The same historical period was already used for the earlier
representative scorecard, so this report cannot claim a previously untouched
holdout. A test-window position still open at the window boundary is censored
and excluded under the explicit `censor_open_positions_at_test_end` policy;
this is not a continuous portfolio simulation. The current run recorded 18
censored T1 positions and 2 censored T4 positions across the six members.

Each JSON scorecard also records a deterministic 95% circular block-bootstrap
interval for per-instrument expectancy (block size 5 trades, 2,000 resamples).
Those intervals are descriptive uncertainty estimates; they are not an IID
p-value and are not combined across the correlated instruments.

The rules and default parameters were frozen before this run. No parameter
tuning was performed against these test windows. The six members are the
provisional representative sample from the main P1 scorecard, not the complete
historical Nifty 50 + Next 50 universe.

## Results

`Positive windows` counts test windows with positive net P&L. `Test-window P&L`
is the sum of completed trades across the six retrospective windows; open
positions are excluded.

| Symbol | Strategy | Test windows | Positive windows | Test-window trades | Test-window P&L | Test-window expectancy |
|---|---|---:|---:|---:|---:|---:|
| NIFTY 50 | T1 Donchian | 6 | 3 | 30 | -₹2,356.17 | -₹78.54 |
| NIFTY 50 | T4 RSI(2) | 6 | 4 | 71 | -₹455.99 | -₹6.42 |
| RELIANCE | T1 Donchian | 6 | 2 | 21 | -₹595.72 | -₹28.37 |
| RELIANCE | T4 RSI(2) | 6 | 0 | 56 | -₹2,561.18 | -₹45.74 |
| TCS | T1 Donchian | 6 | 2 | 23 | -₹606.74 | -₹26.38 |
| TCS | T4 RSI(2) | 6 | 0 | 48 | -₹2,455.36 | -₹51.15 |
| INFY | T1 Donchian | 6 | 2 | 29 | -₹906.08 | -₹31.24 |
| INFY | T4 RSI(2) | 6 | 0 | 43 | -₹2,088.92 | -₹48.58 |
| HDFCBANK | T1 Donchian | 6 | 0 | 27 | -₹1,468.51 | -₹54.39 |
| HDFCBANK | T4 RSI(2) | 6 | 0 | 51 | -₹2,002.18 | -₹39.26 |
| ICICIBANK | T1 Donchian | 6 | 0 | 36 | -₹2,021.23 | -₹56.15 |
| ICICIBANK | T4 RSI(2) | 6 | 0 | 55 | -₹1,924.20 | -₹34.99 |

All 72 window runs passed exact primary/reference backtester equivalence. No
strategy/member aggregate was profitable after the configured costs. This is
enough to reject the current T1 and T4 defaults as P1 promotion candidates,
while retaining them as frozen baselines. It is not evidence that every future
parameterization or strategy is invalid. A complete historical Tier A universe
and a genuinely untouched final holdout remain required before any positive
strategy could be promoted.

## Reproduction

```bash
./.venv/bin/python -m trading.data.cli walk-forward-report \
  --store data/p1/store \
  --symbol 'NIFTY 50' \
  --universe-id india_tier_a_p1_provisional \
  --data-status upstox_unadjusted_provisional \
  --quantity 1 \
  --brokerage 20 \
  --slippage-bps 5 \
  --train-bars 756 \
  --test-bars 252 \
  --step-bars 252 \
  --embargo-bars 1 \
  --output data/p1/reports/nifty50-walk-forward-2016-2026.json
```

