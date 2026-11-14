# P1 statistical validation protocol

Status: research protocol; no strategy is promoted by this document.

## 1. What is being evaluated?

T1 and T4 are deterministic, rules-based trading hypotheses. They are not
supervised-learning models: no parameter vector is fitted by minimizing a loss
on labelled examples. For a closed candle history (D), a strategy produces a
signal using only information available at that candle:

\[
s_t = f(D_{\leq t}; \theta)
\]

where `theta` is the documented rule configuration. The backtester then maps
signals to next-open fills, costs, slippage, stops, and exits. It estimates how
that fixed rule would have behaved on the historical sample.

If a future strategy changes `theta` after looking at results, the process has
become model selection. That can overfit even though the strategy is not an ML
model.

## 2. The quantity of interest

For completed trade (i), the primary outcome is net P&L after configured costs:

\[
X_i = q_i(P_{exit,i} - P_{entry,i}) - fees_i - slippage_i
\]

The sample expectancy is:

\[
\hat{\mu} = \frac{1}{n}\sum_{i=1}^{n} X_i
\]

This is not the same as win rate. A strategy can win often and lose money if
losses are larger, or lose often and make money if winners are larger. P&L must
also be reported relative to capital, exposure, drawdown, and a benchmark; a
fixed quantity in rupees is not directly comparable across instruments with
different prices.

## 3. Why naïve trade statistics are unsafe

Trades are not independent observations. Trades in one stock share market
regimes, and the six tested instruments are correlated. Therefore a standard
IID standard error or a binomial win-rate test can be misleading. The final
validation implementation should use contiguous time-block bootstrap (or an
equivalent dependence-aware method), report uncertainty intervals, and show
results by instrument and chronological window.

The following are separate questions:

1. Is the observed average net P&L positive in this sample?
2. Is the uncertainty interval compatible with zero or a loss?
3. Is the result economically meaningful after drawdown and capital usage?
4. Does it generalize across assets and future time windows?

No single p-value answers all four.

## 4. Correct chronological protocol

The periods must be selected before looking at the strategy results:

1. **Development:** write the hypothesis and, if needed, choose a small set of
   parameters.
2. **Validation:** check limited parameter perturbations and robustness. Do not
   keep searching until a preferred result appears.
3. **Final holdout:** run once after the rule version is frozen. Do not tune on
   this period.
4. **Paper trading:** compare live paper outcomes with the frozen backtest
   expectation before considering any live approval path.

Walk-forward windows are useful for regime coverage, but they do not become an
untouched final holdout merely because they are called “out-of-sample.” The
2016–2026 representative period has already been inspected in this project.
Its current walk-forward report is therefore labelled
`retrospective_walk_forward`, not final OOS evidence.

Each test window uses prior candles for indicator warm-up, restricts signals to
the test interval, and uses a one-bar embargo. A position still open at a
window boundary is explicitly censored and excluded from completed-trade P&L;
this is a window score, not a continuous portfolio simulation.

## 5. Keep/reject gate

The gate must be fixed before reviewing a new strategy. A research candidate
must satisfy all of these conditions:

- data provenance, candle validation, adjustment status, and membership status
  are known;
- primary and independent reference backtesters agree exactly;
- no look-ahead or warm-up violation is found;
- net results include the declared costs and slippage;
- results are positive in a pre-declared majority of assets and chronological
  test windows, not just in one aggregate;
- dependence-aware uncertainty does not make the result indistinguishable from
  zero after costs;
- drawdown and capital usage fit the risk budget;
- the final holdout remains positive after the rule version is frozen.

Failure means “not a promotion candidate,” not “mathematically impossible in
all markets.” A rejected version remains as an immutable baseline. It must not
be silently retuned and renamed; a changed rule is a new strategy version.

## 6. Current P1 conclusion

The representative Upstox sample gives negative full-window results for both
T1 and T4 on every tested member. The retrospective walk-forward aggregates
are also negative for every member. This is sufficient to reject the current
defaults as P1 promotion candidates and to move research toward challenger
strategies, while retaining T1/T4 as baselines.

It is not sufficient to claim a universal statistical theorem that T1 or T4
can never work. The complete historical Tier A universe, point-in-time
membership, delisted instruments, and corporate-action treatment are still
missing. Upstox is the only P1 historical provider; the P3 live provider stays
undecided.

