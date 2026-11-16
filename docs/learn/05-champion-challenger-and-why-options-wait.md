# 05 — Champion/challenger ranking, and why options wait

## What this is
Two unrelated ideas from this phase, both worth understanding before you
look at the code: (1) "champion/challenger" is a way to decide which already
-approved strategy should actually run, without falling back into
cherry-picking; (2) options trading needs a different risk model than
stocks, which is why this phase deliberately did not build it yet.

## Why it exists
Phase P1 of this project went to a lot of trouble (five sub-phases!) to stop
us from picking a strategy just because it had the best backtest number —
that number is usually luck, not edge (see lesson 03, "why backtests lie").
But eventually, if we have several strategies that already passed P1's
honest evaluation, we still need to decide *which one is actively trading
right now*. That decision also needs a disciplined rule, or we're back to
square one — just picking whichever one "looks good today."

Options needed a different kind of discipline: not "don't cherry-pick
results," but "don't build the wrong safety model." A stock's worst case is
bounded by its price going to zero. An option's risk depends on price, time
left, and volatility all at once, and a *sold* option's possible loss isn't
even capped by anything simple. Building an options sleeve by copy-pasting
the equities risk engine would quietly create a way to lose much more money
than the system thinks it's risking.

## Tiny example
Say strategy A ("champion") and strategy B ("challenger") have both already
passed P1's holdout test and are both pre-approved. Each month we measure
"expectancy" (average profit per trade) for each, on fresh data neither has
seen:

| Month | A (champion) | B (challenger) |
|---|---|---|
| 1 | 1.0 | 0.5 |
| 2 | 1.0 | 1.5 |
| 3 | 1.0 | 1.3 |

B only beats A in months 2 and 3 — not three months in a row — so A stays
champion. If B had beaten A in months 1, 2, *and* 3, B would take over. One
good month proves nothing; this rule asks for three in a row before
switching, the same logic as "don't trust one lucky backtest."

For options: a long call's most you can lose is the premium you paid — that
part's "defined risk." But if you also *sell* a call as part of a spread,
and get assigned stock you didn't plan for, your actual position and margin
requirement can look nothing like what you expected from the premium alone.
That's the piece this system doesn't model yet.

## How to run it in this repo
```bash
python -m trading.research.ml_ranker   # self-check demo, prints "OK"
pytest tests/research/test_ml_ranker.py
pytest tests/strategies/test_instances.py -k memecoin
```

## Common mistakes
- Treating the ranker as a way to "search" for a better strategy. It isn't
  — it only ranks candidates that already passed P1's pre-registration and
  holdout process. If you feed it a brand-new, untested candidate, you've
  recreated the exact overfitting trap P1 exists to prevent.
- Assuming "defined-risk" options (like a spread) have *zero* other risk.
  The loss on the structure is capped, but margin and assignment on its
  short leg are still real and not modelled here yet.
- Flipping champion/challenger on a single good period. The rule in this
  repo requires several consecutive winning folds on purpose.

## Check yourself
1. Why doesn't the ranker read raw price candles directly?
2. If a challenger wins 2 out of the last 3 folds but not all 3, does it
   become champion in this repo's rule? Why that threshold and not "majority
   wins"?
3. Why is a short (sold) option's risk harder to bound than a long stock's?

## Words used in this lesson
- **champion/challenger**: the strategy currently active ("champion") versus
  one waiting on the bench that keeps getting re-measured ("challenger"); it
  only takes over if it consistently out-performs, not on one lucky result.
- **walk-forward**: testing a strategy on a sequence of time windows it
  hasn't seen yet, one after another, instead of one single test — closer to
  how it would actually be used going forward.
- **expectancy**: average profit (or loss) per trade, across many trades.
- **defined-risk (options)**: a structure (e.g. a spread) where the maximum
  possible loss is capped and known before you enter, unlike a naked short
  option.
- **assignment**: when a short option position is exercised against you,
  creating a stock position you didn't directly order.
