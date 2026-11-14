# P1 Nifty 50 scorecard — Upstox daily history

Run date: 2026-11-14  
Provider: Upstox historical candles  
Universe: `india_tier_a_p1_provisional`  
Instrument: `NIFTY 50`  
Data status: `upstox_unadjusted_provisional`  
Coverage: 2016-11-14 through 2026-11-12, 2,480 daily bars

The raw response, manifest, DuckDB/Parquet store, and JSON report are kept
locally under `data/p1/` and are intentionally not committed to git.

## Results

| Strategy | Signals | Completed trades | Wins | Losses | Win rate | Net P&L | Expectancy | Max drawdown | Profit factor |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| T1 Donchian | 300 | 48 | 18 | 30 | 37.5% | -253.2297 | -5.2756 | 6628.9873 | 0.9808 |
| T4 RSI(2) | 174 | 99 | 56 | 43 | 56.5657% | -3431.3586 | -34.6602 | 4376.8926 | 0.7081 |

Values include the configured brokerage of ₹20 per order and 5 bps slippage.
Both strategies passed exact primary/reference backtester equivalence. T1 has
one open position at the end of the data window; T4 has none. Unfilled signals
are excluded from completed-trade statistics according to the strategy spec.

## Decision

Neither strategy is kept as a P1 candidate from this run:

- T1 has negative expectancy and net P&L.
- T4 has negative expectancy, negative net P&L, and profit factor below 1.

This is not a final production rejection because the dataset is a single index
proxy, not the complete historical Nifty 50 + Next 50 membership, and the data
is not yet corporate-action-adjusted. It is enough to reject both defaults from
automatic promotion and to avoid paper promotion until a broader, properly
defined universe and the final out-of-sample protocol are run.

## Reproduction

```bash
set -a; . ./.env; set +a
./.venv/bin/python -m trading.data.cli collect \
  --manifest config/india_tier_a.example.yaml \
  --store data/p1/store \
  --archive data/p1/raw \
  --from-date 2016-11-13 \
  --to-date 2026-11-13 \
  --ingest-ts 2026-11-14T00:00:00Z

./.venv/bin/python -m trading.data.cli report \
  --store data/p1/store \
  --symbol 'NIFTY 50' \
  --universe-id india_tier_a_p1_provisional \
  --data-status upstox_unadjusted_provisional \
  --quantity 1 \
  --brokerage 20 \
  --slippage-bps 5 \
  --output data/p1/reports/nifty50-2016-2026.json
```
