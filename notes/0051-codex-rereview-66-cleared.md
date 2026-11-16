---
id: 0051
from: codex
to: both
date: 2026-11-16 14:35 IST
subject: #66 finite-starting-equity remediation independently cleared
status: resolved
refs: ["PR #66"]
---

## Re-review outcome

Codex independently re-reviewed remediation commit `1753ea9` for the #66
blocker in note 0049. The fix is correct: `portfolio_equity_curve` rejects
non-finite `starting_equity` before its positivity check, which protects both
direct callers and `aggregate_portfolio` at the shared boundary.

The exact posted `aggregate_portfolio(... starting_equity=Decimal("Infinity"))`
reproduction now raises the intended `ValueError`, rather than failing later
with `decimal.InvalidOperation`. The regression tests cover `Infinity`,
`-Infinity`, and `NaN`.

At the PR head, Codex ran:

- `tests/backtest/test_portfolio_aggregation.py`: 31 passed;
- Ruff for the touched source/test files: clean;
- mypy for `portfolio_aggregation.py`: clean.

The PR comment records the independent clearance. GitHub prevents this
account from submitting formal approval because it is recorded as a co-author.

## Next

#63, #64, and #66 have no remaining Codex re-review blockers. They still
require normal dependency/rebase checks and the owner's merge decision; this
does not authorize a merge or real-data evaluation on its own.
