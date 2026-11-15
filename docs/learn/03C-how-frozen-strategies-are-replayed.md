# 03C — How frozen strategy rules are replayed

## What this is

A strategy turns closed candles into entry signals. A backtester then simulates
orders using a declared fill rule, costs, stops, exits, and session boundaries.
The P1 catalog fixes 15 strategy variants before results are inspected.

## Why it exists

If a rule or parameter changes between runs, the comparison is no longer fair.
Stable candidate IDs and shared execution rules make each result traceable to
one exact hypothesis. This does not make a strategy profitable; it makes the
experiment reproducible.

## Tiny example

T1's frozen variant `t1-donchian-n20-m10-k2-v1` enters only when a closed daily
bar closes above the prior 20-bar high. Its protective stop is two ATR below
the signal close. If the signal fires at today's close, the simulated buy is
at the next session's open plus the declared slippage and fees. Equal-to-high
does not count as a breakout.

T5 uses the first three complete 5-minute bars to set the opening range. It
checks later closed bars for a close above the range plus a 0.05% buffer, then
fills at the next bar's open. If one later bar touches both stop and target,
the simulation assumes the stop happened first, which is the conservative
choice when bar data cannot reveal the order of intrabar prices.

## How to run it in this repo

```bash
.venv/bin/python -m pytest tests/strategies/test_phase1.py tests/strategies/test_daily_exit_condition.py tests/strategies/test_p1_catalog.py tests/backtest/test_orb.py -q
```

Daily candidates are selected by stable IDs in
`trading.strategies.p1_catalog`; `generate_p1_daily_signals` computes the
required indicators and emits entries. `run_long_only` applies next-open fills
and protective stops. `make_daily_exit_condition` supplies candidate-specific
closed-bar exits. `run_p1_t5_candidate` routes a frozen T5 ID through the
single-session intraday replay. Real-data runs remain blocked until the P1a
source, coverage, action, and split gates are satisfied.

## Common mistakes

- Looking at a bar's high to decide a close-based entry. The high may have
  happened before the close and does not prove the close crossed the level.
- Filling at the signal close when the rule says next open.
- Letting parameters drift after seeing historical results.
- Treating a 60% win rate as proof of profit. Average win/loss, costs, and risk
  still determine the result.
- Counting truncated intraday sessions or open positions as completed trades.

## Check yourself

1. Why does a close equal to the Donchian high fail the strict breakout rule?
2. If a signal is emitted at today's close, which price is used for the fill?
3. Why does the T5 runner assume a stop when both stop and target fall inside
   the same five-minute bar?

## Words used in this lesson

- **Candidate**: one fully specified strategy hypothesis with fixed parameters.
- **Slippage**: the difference between the observed price and the simulated
  execution price, modeled here as an adverse cost.
- **Look-ahead bias**: using information from a later candle to make an earlier
  decision.
