# Strategies and the first honest scorecard

## What this is

A strategy is a precise rule that turns closed market candles into a possible
entry signal. A backtest replays those signals over historical candles. In this
repo, the primary backtester and a slower reference backtester must agree before
we calculate a scorecard.

## Why it exists

Small timing mistakes can make a strategy look profitable when it could not
have traded that way. Signals use a closed bar, fills happen at the next bar's
open, and stop-losses take precedence when a bar touches both a stop and a
target. The reference runner is an independent check against accidental bugs.

## Tiny example

If a signal closes at 10, the next bar opens at 13, and the stop is 9, a
quantity of 2 that later exits at 9 loses `(9 - 13) * 2 = -8` before fees.
That trade is included in the scorecard only after both runners produce the
same trade.

## How to run it in this repo

```bash
./.venv/bin/pytest -q
./.venv/bin/ruff check src tests
./.venv/bin/mypy src
```

The reusable validation entry point is
`trading.backtest.validation.validate_long_only`; it refuses to return a
scorecard when the primary and reference results differ.

## Common mistakes

- Using the current bar's close as the fill price.
- Comparing prices through `float`, which can change a precise boundary.
- Counting a signal on the final bar as a filled trade.
- Treating a good-looking scorecard as proof that a strategy works.

## Check yourself

1. Why must a signal on the final available bar remain unfilled?
2. Which exit wins when a bar reaches both the stop and target?
3. Why do we need two backtest implementations?

## Words used in this lesson

- **Signal**: a strategy's instruction that an entry condition occurred.
- **Fill**: the simulated price at which an order is executed.
- **Scorecard**: summary statistics such as trade count, win rate, drawdown,
  and expectancy.
- **Reference implementation**: a slower, simpler implementation used to find
  mistakes in the primary implementation.
