# 03B — Pre-registration, multiple testing, and the holdout

## What this is

Pre-registration means writing down the strategies, parameter choices, metrics,
and decision rules before looking at their results. A holdout is a final period
kept separate from strategy design and used once to check whether a frozen
shortlist still behaves acceptably.

## Why it exists

Trying many rules makes it likely that one looks good by chance. If 20
unhelpful candidates each have a 5% chance of looking significant, the chance
that at least one does is much larger than 5%. Bonferroni adjusts a p-value by
the number of predeclared candidates. It is conservative, but it makes the
search size visible. The holdout gives one last check after design is frozen;
reusing it turns it into more training data.

## Tiny example

If a candidate has raw `p=0.01` and the catalog contains 19 attempts, its
Bonferroni adjusted value is `min(1, 19 × 0.01) = 0.19`. That is not
statistically significant at 5%. The candidate may still be a useful
hypothesis, but this result alone does not establish an edge.

## How to run it in this repo

```bash
.venv/bin/python -m pytest tests/backtest/test_multiple_testing.py tests/backtest/test_holdout.py -q
```

The registry is tested separately in `tests/backtest/test_experiment_registry.py`.
No real-data results exist under the P1 catalog yet.

## Common mistakes

- Adding candidates after seeing results without counting the new trials.
- Treating a corrected p-value as proof of profitability or future stability.
- Looking at holdout results repeatedly while changing rules.
- Dropping failed runs from the registry.
- Resampling each stock independently when stocks move together; the agreed
  bootstrap resamples synchronized date blocks.

## Check yourself

1. Why does testing more candidates increase false discoveries?
2. Why does a failed holdout evaluation still consume the holdout?
3. What does Bonferroni do to `p=0.01` across 19 declared candidates?

## Words used in this lesson

- **Pre-registration**: recording rules and analysis choices before results.
- **Multiple testing**: evaluating many hypotheses, increasing chance wins.
- **P-value**: a measure of how surprising data are under a specified null
  model; it is not the probability that a strategy is profitable.
- **Holdout**: a final unseen data period reserved for one frozen evaluation.
