# P1 representative Tier A scorecards — Upstox daily history

Run date: 2026-11-15  
Provider: Upstox historical candles  
Coverage: 2016-11-14 through 2026-11-12  
Costs: ₹20 brokerage per order and 5 bps slippage  
Data status: `upstox_unadjusted_provisional`

This run covers the Nifty 50 index plus five representative large-cap equities:
RELIANCE, TCS, INFY, HDFCBANK, and ICICIBANK. It is a representative Tier A
sample, not the complete historical Nifty 50 + Next 50 membership. Raw data and
JSON reports are kept locally under `data/p1/` and are not committed.

## Results

| Symbol | Strategy | Trades | Wins | Losses | Win rate | Net P&L | Expectancy | Max drawdown | Profit factor |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| NIFTY 50 | T1 Donchian | 48 | 18 | 30 | 37.50% | -253.23 | -5.28 | 6628.99 | 0.9808 |
| NIFTY 50 | T4 RSI(2) | 99 | 56 | 43 | 56.57% | -3431.36 | -34.66 | 4376.89 | 0.7081 |
| RELIANCE | T1 Donchian | 38 | 12 | 26 | 31.58% | -1058.71 | -27.86 | 1058.71 | 0.4160 |
| RELIANCE | T4 RSI(2) | 84 | 3 | 81 | 3.57% | -3823.84 | -45.52 | 3823.84 | 0.0110 |
| TCS | T1 Donchian | 41 | 16 | 25 | 39.02% | -833.44 | -20.33 | 1280.53 | 0.6842 |
| TCS | T4 RSI(2) | 73 | 19 | 54 | 26.03% | -3263.65 | -44.71 | 3275.75 | 0.1946 |
| INFY | T1 Donchian | 45 | 9 | 36 | 20.00% | -1707.68 | -37.95 | 1745.11 | 0.3750 |
| INFY | T4 RSI(2) | 63 | 5 | 58 | 7.94% | -2856.71 | -45.34 | 2856.71 | 0.0416 |
| HDFCBANK | T1 Donchian | 43 | 5 | 38 | 11.63% | -1818.25 | -42.28 | 1911.68 | 0.1248 |
| HDFCBANK | T4 RSI(2) | 77 | 1 | 76 | 1.30% | -2979.82 | -38.70 | 2979.82 | 0.0047 |
| ICICIBANK | T1 Donchian | 53 | 6 | 47 | 11.32% | -2587.21 | -48.82 | 2618.84 | 0.0810 |
| ICICIBANK | T4 RSI(2) | 83 | 2 | 81 | 2.41% | -3057.21 | -36.83 | 3057.21 | 0.0135 |

All ten runs passed exact primary/reference backtester equivalence.

## Decision

Keep neither T1 nor T4 as a P1 promotion candidate. Every tested symbol and
both strategies had negative net P&L and negative expectancy after costs. T4's
win rate was often low enough to explain its poor result; where its win rate was
higher, its losses and costs still produced negative expectancy.

This is a strong rejection of the current default implementations for this
provisional sample, not proof that every possible parameterization or future
strategy is invalid. Do not tune parameters against this same out-of-sample
result. The next research decision requires the complete historical universe,
corporate-action treatment, and the pre-registered walk-forward protocol.

## Reproduction

```bash
set -a; . ./.env; set +a
./.venv/bin/python -m trading.data.cli collect \
  --manifest config/india_tier_a.example.yaml \
  --store data/p1/store \
  --archive data/p1/raw \
  --from-date 2016-11-13 \
  --to-date 2026-11-13 \
  --ingest-ts 2026-11-15T00:00:00Z
```
