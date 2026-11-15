# P1 research split contract

Status: source-independent contract. No date boundaries are frozen yet. The
previously inspected 2016–2026 sample is burned and cannot be reused as the
untouched holdout (ADR-0024).

## Required split plan

A `ResearchSplitPlan` is an immutable, versioned record containing:

- a unique plan ID and data-window ID;
- a half-open overall date range `[start, end)`;
- ordered, non-overlapping development, validation, and holdout ranges that
  exactly partition the overall range;
- a positive embargo in bars at each boundary;
- an explicit `holdout_status`, initially `unread`;
- a content hash and creation provenance.

The plan must identify the exact source snapshot and universe version. It may
be frozen only after authorized historical inputs, the complete calendar,
corporate-action basis, and universe coverage are verified. Date ranges are
never inferred from the current dataset length.

## Use rules

- Candidate construction and parameter selection may read development data.
- Validation can be used only for the predeclared robustness/selection rules
  in the strategy plan.
- The holdout must not be accessible to a strategy-ranking or parameter-search
  API. It is exposed through a separate one-shot evaluator after shortlist and
  rejection rules are frozen.
- The evaluator atomically records the holdout as consumed before returning
  any result. Re-running requires a new plan and a new genuinely unread data
  window; it cannot reset the old plan.
- Every split is half-open. A bar belongs to one range only. The embargo drops
  bars near boundaries where a next-open fill could cross partitions.
- Any split, source, calendar, universe, or corporate-action change produces a
  new plan version and invalidates prior comparisons.

## Current gate

The 2016–2026 sample has been inspected and is unavailable as an untouched
holdout. Upstox remains the only P1 candle source (ADR-0023), but the current
sample cannot establish the selected point-in-time universe or a fresh
holdout. Do not write dates into production config, rank strategy candidates,
or evaluate a holdout until the required data and owner confirmation exist.
The source-independent one-shot access guard is implemented in
`trading.backtest.holdout`; it marks a plan consumed before the evaluator runs
and keeps it consumed even if evaluation raises. Consumption is unique by
data-window ID as well as plan ID, so changing a plan label cannot unlock the
same window again. Registry selection queries omit holdout rows, and explicit
holdout reads require the consumed plan and matching frozen hashes.
