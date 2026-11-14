# 02 — What is a backtest, and how to read one

## What this is
A **backtest** replays a trading rule over old price history and records
what would have happened: when it would have bought, when it would have
sold, and the profit or loss of each trade. It turns "I think this rule is
good" into a number you can actually look at.

## Why it exists
Without a backtest you're trading on a feeling. With one, you get an honest
(if imperfect — see lesson 03) estimate of how a rule has behaved in the
past, which is the only evidence available before risking real money.

## Tiny example
Say a rule bought RELIANCE at ₹2,500 and sold at ₹2,580 ten days later; then
bought again at ₹2,600 and was stopped out at ₹2,560 five days later.
Two trades:

| Trade | Entry | Exit | Days held | P&L |
|---|---|---|---|---|
| 1 | 2500 | 2580 | 10 | +80 (+3.2%) |
| 2 | 2600 | 2560 | 5 | -40 (-1.5%) |

From these two trades you can already compute the numbers every scorecard
reports:

- **Win rate:** 1 of 2 trades won = 50%.
- **Average win / average loss:** +80 / -40.
- **Expectancy** (average P&L per trade, the single most important number):
  `(80 + -40) / 2 = +20` per trade — on average, this rule made money, even
  though it lost on half its trades. Win rate alone can be misleading: a
  rule that wins 80% of the time but loses big on the 20% can still lose
  money overall.
- **Profit factor:** total wins ÷ total losses = `80 / 40 = 2.0`. Above 1
  means the rule made more than it lost; below 1 means it didn't, no matter
  how often it "won."
- **Drawdown:** the worst peak-to-trough dip in your account value along the
  way — how bad did it get before it recovered? A rule can have a great
  final number and still have been terrifying to hold through a 40%
  drawdown in the middle.

## How to run it in this repo
There's no backtester yet (it's a later build phase — see
`docs/BUILD_ORDER.md` P1), but the exact fill rule it will follow is already
written down: a signal that fires on a closed bar's close price fills on the
**next** bar's open, plus trading costs and a small unfavorable slippage
(`docs/specs/TEST_SPEC_BACKTEST.md` has worked numeric examples once that
spec lands). That "next bar's open, never the signal bar's own close" rule
is the single most important thing to understand about how backtests here
are kept honest — it's explained further in lesson 03.

## Common mistakes
- Judging a strategy by win rate alone (see the expectancy example above —
  a 50% win rate with asymmetric wins/losses can still be profitable, or a
  90% win rate can still be a loser if the 10% losses are huge).
- Ignoring drawdown. A strategy that makes money but asks you to sit through
  a 50% account dip to get there is a different (much harder) thing to
  actually hold than the final return number suggests.
- Looking at one good run and calling it proven. One backtest over one
  period is a hypothesis, not a result — see lesson 03 for why.

## Check yourself
1. A rule has a 70% win rate but a profit factor of 0.8. Is it profitable?
2. Why might two strategies with the same total return be very different to
   actually trade, based on their drawdown?
3. What does "expectancy" tell you that "win rate" alone doesn't?

## Words used in this lesson
- **Backtest:** replaying a rule over historical price data to see what it
  would have done.
- **Win rate:** the percentage of trades that made money.
- **Expectancy:** the average profit or loss per trade.
- **Profit factor:** total profit from winning trades divided by total loss
  from losing trades.
- **Drawdown:** the biggest drop from a peak account value to a later low,
  before it recovers.
