# P1 evaluation and experiment registry

Status: pre-registered design. No real-data candidate result has been produced
under this evaluation plan.

P1's first pass evaluates daily and intraday strategy families on the fixed
five-symbol pilot declared in `P1_CANDIDATES.md`. This is a survivorship-biased
methodology study, not evidence for the broad Indian equity universe. Maintain
separate frozen candidate catalogs and sample/coverage checks for each
timeframe; use 1-minute/5-minute history only from complete sessions and split
at session boundaries. Upstox V3 minute requests are capped at one month for
1–15 minute intervals, so ingestion is resumable and month-chunked. The
provider documents minute history from January 2022; this is materially
shorter than daily history and constrains the intraday holdout design.

## Units of analysis and required records

One experiment is one immutable candidate version on one frozen universe,
calendar, data snapshot, adjustment basis, cost profile, sizing assumption,
and split. Runs must record failed as well as completed attempts. Candidate
variants are the trials; repeated diagnostics on the same run do not create a
new candidate but every change to rules, universe, data, costs, or boundaries
does.

Each registry record contains:

- experiment ID, timestamp supplied by the runner, outcome/status and error;
- candidate ID/version and exact parameter JSON;
- catalog, source snapshot, parser, universe, calendar, corporate-action,
  cost-model, sizing and split-plan IDs/hashes;
- sample window and partition (development, validation, holdout);
- code revision and software/environment version;
- instrument and time-window coverage, trade count, exposure and turnover;
- all metrics below, uncertainty interval/method, and multiple-testing family
  and adjusted result where applicable.

The registry is append-only. Corrections create a linked superseding record;
they never overwrite or erase a failed/poor result. Its selection API exposes
development and validation only. Holdout rows require a complete consumed
`HoldoutPlan` and are filtered to that plan and data-window identity. Completed
runs require non-empty metric evidence; failed runs retain exact identity and
error details. Non-finite JSON constants are rejected; undefined metrics use
JSON `null` plus a reason field.

## Metrics (after costs)

Report per instrument and per declared market-regime/time block. Do not rank
by rupee P&L or win rate alone. The current primary/reference runners are
single-instrument, fixed-quantity simulators and do not implement simultaneous
portfolio allocation. Until a shared, independently checked portfolio replay
exists, calculate per-instrument metrics only; do not claim pooled portfolio
performance or apply the portfolio-return bootstrap to concatenated or
averaged independent runs.

- Total and annualized return on the same capital path; CAGR only for a
  continuous, fully specified equity curve.
- Maximum peak-to-trough drawdown in INR and percent; Calmar ratio only when
  CAGR and drawdown are defined.
- Sharpe and Sortino on daily portfolio returns, with annualization factor
  declared from the verified calendar; label estimates and show sample size.
- Trade count, win rate, mean/median trade return, expectancy, gross profit
  factor, exposure, turnover, average holding sessions, fees/slippage and
  cost drag.
- Fraction of instruments and predeclared non-overlapping time blocks with
  positive net return; compare against cash and buy-and-hold on identical
  dates, sizing and costs.

Open positions at the end of a partition are marked to market for portfolio
returns and drawdown, but are not counted as completed trades. Unfilled signals
are logged separately. Metrics with undefined denominators are `null` with a
reason, never silently set to zero. Future portfolio aggregation must state
how simultaneous signals, 1% risk sizing, cash reservations, capital limits,
and conflicts are handled.

## Uncertainty and multiplicity

- Primary uncertainty summary: 95% moving-block bootstrap interval for the
  mean daily net portfolio return, resampling synchronized date blocks across
  all instruments (so cross-sectional dependence is preserved). Block length
  is fixed before results: 20 trading sessions; 10,000 replicates; fixed seed
  recorded. This is a descriptive interval, not proof of future returns.
- The bootstrap input is a complete, ordered, finite vector of **daily
  portfolio net returns**, one value per verified exchange session, including
  explicit zero-return sessions while flat. Do not bootstrap trade returns,
  instrument rows independently, or omit flat days. Sample 20-session blocks
  with replacement until each replicate has the same number of sessions as
  the input; truncate the final block. For each replicate compute the
  arithmetic mean. The interval is the nearest-rank 2.5th and 97.5th
  percentiles of the 10,000 replicate means. Record seed, block size,
  replicate count, sample count, and quantile convention.
- Primary family-wise correction: Bonferroni across the 15 predeclared
  strategy variants in `P1_CANDIDATES.md` and `P1_INTRADAY_CANDIDATES.md`;
  cash and buy-and-hold are fixed
  reference baselines, not tested hypotheses. Adjusted
  `p = min(1, m*p_raw)`. Only compute a raw p-value from a predeclared test of
  mean net daily excess return against cash using the same synchronized
  bootstrap distribution. Report raw and adjusted values; do not interpret a
  non-significant result as evidence of no edge.
- This correction is conservative and depends on the stated family count. Any
  newly added variant, metric-driven family selection, universe change, or
  post-result rule change is a new trial family and must be recorded before
  rerunning. Prefer a broad stable performance plateau and cross-instrument
  consistency over the best point estimate.
- Holdout results are descriptive one-shot evidence. Do not select or tune
  candidates by holdout p-values or intervals.
- The implemented raw test uses a one-sided centered circular moving-block
  bootstrap of the mean daily excess return against cash, with plus-one
  correction `(exceedances + 1) / (replicates + 1)`. It uses the same fixed
  20-session blocks, 10,000 replicates, and recorded seed. The frozen
  family-wise correction is Bonferroni across 15 strategy variants; the two
  fixed baselines are comparators, not hypotheses.

## Ranking and rejection

No single composite score will hide trade-offs. Produce a Pareto table over
net return, max drawdown, Calmar, Sharpe/Sortino, cost drag, positive-instrument
fraction, and uncertainty. First eliminate candidates that fail pre-written
minimum viability criteria; then compare non-dominated candidates. For P1d
holdout evaluation, `P1_REJECTION_RULE.md` is the authoritative pre-registered
source for the minimum sample sizes, coverage requirements, decision thresholds
and failure reasons. Rejection always includes a reason; no candidate is
dropped merely because it ranks low.

## Promotion bar by frequency

Intraday candidates require a stricter promotion bar than daily candidates:
longer forward paper observation and more conservative position sizing. Exact
durations, sample requirements, and size limits must be written into the
promotion policy before intraday results are evaluated; do not infer numbers
from the retrospective backtest.

## Holdout separation

Development and validation may be used only as specified in the candidate
catalog. The holdout is hidden from ranking, registry queries used for
selection, and strategy authors until the shortlist, rejection rules, metrics,
and multiple-testing family are frozen. Its first evaluation marks the split
plan consumed. See `RESEARCH_SPLITS.md`.
