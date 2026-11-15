# P1 promotion-policy proposal (daily vs. intraday)

**Status: PROPOSED DEFAULT, not approved.** Every number below is a starting
point for the owner to review, adjust, or reject — none of it is frozen, and
nothing here authorizes any live or paper run on its own. This is distinct
from the live-mode escalation gate already in the repo
(`experiment_registry`/P2's approval-to-auto promotion, commit `711aceb`,
`config/risk.example.yaml`'s `pause_after_consecutive_losses`) — that gate
governs a strategy already running in paper/auto mode; this document governs
whether a P1-shortlisted *backtest* candidate is even allowed to start a
forward paper run at all, and under what conditions it can later be
considered for that live-mode gate. The two are sequential, not the same
mechanism.

## Why intraday needs a stricter bar than daily (rationale, not a number)

- Intraday (T5 ORB) has far more trades per unit of calendar time than a
  daily swing strategy, so a given trade count is reached much faster —
  "more trades" is not the same evidence as "more calendar time survived."
  A stricter bar should weight calendar-time survival, not just trade count.
- Intraday Upstox history only goes back to January 2022 (`BUILD_ORDER.md`'s
  verified coverage note) — there is strictly less independent historical
  evidence available than for daily, which argues for leaning more on forward
  paper evidence before any promotion, not less.
- Session-level execution risk (slippage, partial fills near square-off,
  5-minute-bar granularity) is harder to validate from backtest cost
  assumptions alone than daily's next-open fill — more real-world paper
  observation is the only way to find out if the assumed cost model holds.

## Proposed thresholds

| Gate | Daily (T1/T2/T3/T4/T6) | Intraday (T5 ORB) | Rationale |
|---|---|---|---|
| Minimum completed trades before promotion eligibility | 30 | 60 | Intraday's higher trade frequency means 60 trades is reached faster in calendar time than 30 daily trades — the count alone doesn't equalize evidence, hence the calendar-time gate below. |
| Minimum forward paper period (calendar days, continuous) | 60 | 120 | Twice the daily minimum, directly reflecting "longer forward paper observation" already agreed qualitatively; 120 days also spans multiple NSE expiry/rebalance cycles. |
| Maximum live/paper drawdown vs. backtest max drawdown | 125% of backtest max DD | 110% of backtest max DD | Any live drawdown exceeding backtest by more than this halts promotion -- intraday gets a tighter band because execution-risk divergence (assumption C above) should show up fast if the cost model was wrong. |
| Position-size fraction of the eventual target sizing | up to 100% at promotion | capped at 50% at promotion, reviewed before any increase | Matches "more conservative sizing" already agreed; intraday starts capped rather than full-sized even after clearing the other gates. |
| Consecutive-loss pause (carried from `config/risk.example.yaml`) | 5 | 5 | No change proposed -- this is a sleeve-level risk control, not specific to promotion; kept identical rather than invented differently per timeframe without a reason to diverge. |
| Statistical gate | Bonferroni-adjusted p-value (m=18, the full predeclared family) significant AND holdout survives the predeclared rejection rule | same | Both timeframes draw from the same single family-wise correction (`P1_EVALUATION.md`) -- no separate, looser correction per timeframe. |

## What this proposal deliberately does not do

- Does not invent a number where the owner previously asked a question
  instead (e.g. the exact live sizing target itself, starting capital per
  sleeve — those remain `MASTER_PLAN.md` §13 open items).
- Does not relax AGENTS.md §4's hard rule that nothing reaches a real broker
  without `mode=approval`/`auto`, risk-engine approval, kill-switch off, and
  (for `approval`) explicit human sign-off per signal — this document only
  ever governs whether a candidate is eligible to *enter* forward paper, not
  whether paper trades reach a real order.
- Does not claim any of the above numbers have been validated against real
  P1 results — none exist yet; this is a policy proposal to review now so
  it's ready the moment P1a's data gates clear, not a retroactive fit to
  evidence.

## Open for owner decision

1. Are the trade-count/calendar-day minimums in the right ballpark, or does
   the owner have a different risk tolerance in mind?
2. Is 50% sizing cap for intraday's first promotion the right fraction, or
   should it start even smaller (e.g. 25%)?
3. Does the drawdown-vs-backtest band (125%/110%) match how much backtest-vs-
   live divergence the owner is willing to tolerate before treating a
   strategy as invalidated rather than just paused?
