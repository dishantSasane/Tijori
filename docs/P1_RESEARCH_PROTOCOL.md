# P1 India research protocol

This is the working protocol for the first Upstox-backed India backtests. It
keeps research decisions explicit so a profitable-looking result cannot quietly
change the rules that produced it.

## Dataset window

- Target at least 10 calendar years of daily candles ending on the latest
  complete trading day available from Upstox.
- Accept a shorter window only when Upstox actually limits the endpoint; five
  years is the minimum useful fallback. Record the returned coverage in the
  run manifest.
- Keep at least 200 prior trading bars before evaluating T4, because its trend
  filter is SMA(200). Warm-up bars are history, not eligible signal bars.
- Keep raw Upstox responses and request manifests. The P1 example universe is
  provisional and must not be described as survivorship-free until historical
  membership, delistings, and corporate actions are resolved.

## Time-ordered evaluation

Use chronological partitions, never random splits:

1. In-sample: freeze the rules and any parameter choice.
2. Validation: check robustness and small parameter perturbations.
3. Final out-of-sample: run once after the rules are frozen.
4. Walk-forward: repeat the process over successive historical windows with an
   embargo at each boundary because fills occur on the next bar's open.

The final out-of-sample period must not be used to tune a strategy.

## Strategy scope

P1 tests only the two strategies named in the build order:

- T1 Donchian breakout.
- T4 RSI(2) pullback.

Use their documented default rules first. Do not run a large parameter sweep.
T2, T3, T5, and T6 are later work after this data and validation path proves
reliable.

## Keep/reject decision

P1 does not promote a strategy to live trading. A strategy is only a research
candidate when all of these hold:

- data provenance and candle validation pass;
- look-ahead and warm-up tests pass;
- primary and independent reference backtesters agree exactly;
- net results include fees and slippage;
- performance survives multiple walk-forward windows and modest parameter
  perturbations;
- drawdown and trade count are acceptable for the risk budget;
- final out-of-sample results remain credible.

Candidates then move to weeks of paper trading. A strategy change creates a new
immutable version. No single profitable scorecard is sufficient evidence.

## Commands

Collect candles from the explicit manifest (the token is read from the
`UPSTOX_ACCESS_TOKEN` environment variable and is never printed):

```bash
./.venv/bin/python -m trading.data.cli collect \
  --manifest config/india_tier_a.example.yaml \
  --store data/p1/store \
  --archive data/p1/raw \
  --from-date 2016-01-01 \
  --to-date 2026-11-13 \
  --ingest-ts 2026-11-14T00:00:00Z
```

After collection, run both strategies and write the research-only report:

```bash
./.venv/bin/python -m trading.data.cli report \
  --store data/p1/store \
  --symbol 'NIFTY 50' \
  --universe-id india_tier_a_p1_provisional \
  --data-status provisional_unadjusted \
  --quantity 1 \
  --brokerage 20 \
  --slippage-bps 5 \
  --output data/p1/reports/nifty50.json
```
