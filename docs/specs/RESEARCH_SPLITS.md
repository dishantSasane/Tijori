# P1 research split contract

Status: **P1a boundaries frozen**. The two owner-confirmed plans below are
pre-registered against the frozen P1a evaluation manifest. ADR-0024's
holdout protection is triggered by strategy-outcome exposure, not by a
data-integrity check. No strategy-outcome result was computed or viewed for
any recorded-history period before this lock, so the specified 2026 holdout
is unread. Corporate-action continuity, no-trade-day decoding, and universe
selector checks are not strategy-outcome exposure.

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

## Frozen P1a historical plans

Confirmed by the owner on 2026-11-16. All ranges are half-open: the final
included session is the day before the stated end date. The common holdout is
therefore the latest historical window in the frozen dataset, ending with
2026-11-14.

| Plan | Development | Validation | Untouched holdout | Embargo |
|---|---|---|---|---|
| `p1a-daily-historical-v1` | `[2010-01-01, 2025-01-01)` | `[2025-01-01, 2026-01-01)` | `[2026-01-01, 2026-11-15)` | 1 daily bar at each boundary |
| `p1a-intraday-historical-v1` | `[2022-01-01, 2025-01-01)` | `[2025-01-01, 2026-01-01)` | `[2026-01-01, 2026-11-15)` | 1 bar at each boundary, independently for M1 and M5 |

Separate plans are required because the daily source begins in 2010 whereas
the provider's M1/M5 source begins in 2022. They deliberately share the same
validation and holdout dates, so daily and intraday candidates face the same
unread market period at P1d.

### Frozen evidence bindings

Both plans are bound to the immutable evaluation-manifest artifact
`docs/specs/P1A_EVALUATION_MANIFEST.json`:

`evaluation_manifest_sha256 = aa1c0a786f78cf321c2fb4f042413d0c47c276e74063b45dfb8944ce58e60e55`

That manifest fixes the five-symbol P1a pilot universe, in sorted order:
`HDFCBANK`, `ICICIBANK`, `INFY`, `RELIANCE`, `TCS`. Its content hash is the
universe binding for these plans; the selector implementation alone is not a
substitute for a separately frozen broader-universe snapshot.

| Binding | Daily plan | Intraday plan |
|---|---|---|
| Source candle snapshot(s) | `1d = 74d334595083e445c1c1301293abc03884d27bc5d91604d8bb7514b87cf80942` | `1m = 42bb1b2a3481d9a996ba1c9bb1718dcbb6316ce96d3dc324de2b4e7aa069213f`; `5m = 634a74d90c9bf89d6d822f31bfec33cb77c8335dadd9e056bb0451c801e0b090` |
| Universe snapshot | five-symbol universe contained in evaluation manifest above | same |
| Calendar snapshot | `37017e9c34e111279500921e472359d9ce1d1edb92e696c076d0ce68d1fe261f` | `3879c1e8a2887c2d1310431048da1d929277ff78db0ca8dc0bf240b835d6cda7` |
| Corporate-action register | `f0abc42ed748a87d444431193a3a9c9322ca5b263ae082b580ba031a1949256b` | same |

The manifest currently labels action coverage `unverified`; this date lock
does **not** authorize a real-data run or relax any preflight, source,
calendar, action-coverage, or broader-universe gate. A run remains blocked
until all applicable gates are independently satisfied.

### Lock and one-shot protection

Before a holdout candle or metric is read, materialize each plan with the
bindings above and seal its content hash alongside the candidate shortlist,
P1d rejection-rule hash, metric/catalog hash, cost-model hash, and frozen
data-manifest hash. Set `holdout_unread` to `true` for each plan.

Do not change a candidate, costs, universe, source, calendar,
corporate-action register, embargo, or **any boundary in these plans after a
result**. A change requires a new catalog/rule/study version and a new,
genuinely unread holdout; it must not reuse this holdout to tune or retry a
candidate. The existing one-shot evaluator must reserve and mark the matching
data-window ID consumed before it returns a result, including on error.

The source-independent one-shot access guard is implemented in
`trading.backtest.holdout`; it keeps a consumed holdout consumed even if
evaluation raises. Consumption is unique by data-window ID as well as plan
ID, so changing a plan label cannot unlock the same window again. Registry
selection queries omit holdout rows, and explicit holdout reads require the
consumed plan and matching frozen hashes.
