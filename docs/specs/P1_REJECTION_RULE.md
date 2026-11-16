# P1d holdout decision rule

Status: pre-registered before any P1 holdout evaluation. Applies to the bounded
five-symbol pilot and 15-variant family in `P1_CANDIDATES.md`.

## Unit of evidence

The candidate is evaluated as the same fixed rule applied to all five pilot
symbols. Do not select a symbol, regime, date block, or variant after seeing
holdout results. Build a synchronized panel of daily **net excess returns**:
for each verified session, compute each symbol's return on its own fixed
research capital after costs, then take the arithmetic mean across the five
symbols. Flat sessions remain explicit zero returns. This panel statistic
estimates average per-instrument edge; it is not a funded portfolio return and
must not be used to claim pooled P&L, portfolio Sharpe, portfolio drawdown, or
deployable capital performance. Report all five per-symbol scorecards beside
the panel statistic.

The one-sided bootstrap test and 95% moving-block interval use the same
synchronized panel series, 20-session blocks, 10,000 replicates, and the frozen
seed recorded in the experiment row. The raw test is mean daily excess return
versus cash. Apply Bonferroni with `m=15` across the complete pre-registered
candidate family (12 daily + 3 intraday); never correct each timeframe
separately. The full five-symbol holdout panel must be complete before this
statistic is produced.

## Minimum evidence

- Daily candidates: at least 30 completed trades in the holdout.
- Intraday candidates: at least 60 completed trades in the holdout.
- All five symbols must have verified action, calendar, candle and cost
  coverage for the entire holdout; an incomplete symbol is not silently
  removed from the fixed pilot.
- Divide the frozen holdout session sequence into three consecutive blocks
  with sizes differing by at most one session; give remainder sessions to
  earlier blocks. Freeze the exact session boundaries before reading results.
- Define a symbol/block as profitable when its after-cost cumulative return is
  strictly positive. Count zero as not profitable.

## Decision categories

Every shortlisted candidate gets exactly one of these statuses after its
one-shot evaluation:

### `inconclusive` (does not advance)

Use when required coverage is incomplete, fewer than the minimum trades exist,
any required statistic is undefined, the adjusted p-value is at least 0.05, or
the 95% bootstrap interval includes zero. This means the frozen evidence is
insufficient; it is not proof that the strategy has no edge. The consumed
holdout cannot be used to tune or retry the candidate.

### `rejected`

Use when minimum evidence exists but any robustness condition fails:

- mean daily excess return after costs is not strictly positive;
- fewer than 3 of 5 symbols have positive net return; or
- fewer than 2 of 3 chronological blocks have positive net return.

Do not change the candidate, costs, universe, or boundaries after this result.

### `pass_to_paper`

Allowed only when all minimum-evidence conditions hold, mean daily excess
return after costs is positive, at least 3 of 5 symbols and 2 of 3 time blocks
are profitable, the Bonferroni-adjusted one-sided p-value is below 0.05, and
the 95% synchronized moving-block bootstrap interval has a lower bound above
zero. This only permits entry into the separate forward-paper observation
policy. It does not promote a strategy to live, approve any order, or change
capital and risk settings.

## Freeze and audit requirements

Before any holdout candle or metric is read, seal hashes for the candidate
shortlist, this rule, metrics/catalog, frozen full data manifest, source,
calendar, corporate-action register, cost model, and split plan. Reserve the
holdout through `HoldoutEvaluator`; it is consumed before evaluation starts,
including on errors. Record all candidates, outcomes, and failure reasons in
the append-only registry. The previously inspected 2016-2026 sample is burned
and cannot be selected as the untouched holdout.
