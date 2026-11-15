---
id: 0037
from: claude
to: both
date: 2026-11-16 (note, no clock access -- see PR timestamps)
subject: P4 -- daily scanner, shortlist, Stocks page, scanner backtest shipped (PR #57)
status: needs-human
refs: ["PR #57", "docs/BUILD_ORDER.md P4", "docs/decisions.md ADR-0029/30/31", "PR #53", "PR #56"]
---

## Context
Picked up P4 (STATUS.md had P3 as the last completed phase via PR #56,
still open). Followed the "fetch origin, read STATUS.md + recent notes
first" rule from note 0035's duplicate-work lesson before writing anything.
Branched `claude/p4-scanner-stocks-page` off `origin/main` (not a stale
local ref).

## What I did
Built and shipped (PR #57, branch `claude/p4-scanner-stocks-page`, based
on current `main`):
- **Daily scanner** (`src/trading/scanner/filters.py`, `scanner.py`): pure
  liquidity + data-quality filters, momentum-based ranking. No-look-ahead
  enforced by construction -- filters only ever see candles strictly
  before the scan's `as_of` date.
- **Shortlist persistence** (`shortlist_store.py` + new
  `scanner_shortlist` table added to `src/trading/storage/state_db.py`):
  one write path, `apply_scan()`, promotes today's survivors to `active`
  and demotes yesterday's survivors that no longer qualify to `removed`
  (never deleted). This is list membership, **not** the strategy-version
  promotion pipeline in `docs/STRATEGIES.md` §6/§8 -- kept them clearly
  separate per the task brief, documented in ADR-0030.
- **Scanner backtest** (`backtest.py`): replays the scanner per historical
  session date, measures forward price return over a horizon -- no fills,
  fees, or P&L. Deliberately distinct from `src/trading/backtest/`'s
  strategy backtester (ADR-0031); the owner-facing lesson spells out why a
  "hit rate" here isn't a trading-edge claim.
- **Stocks page** (`dashboard/pages/4_Stocks.py`): read-only Streamlit page
  over the shortlist, shows target/reconsider levels and whether an idea
  already has an open paper position.
- **Lesson**: `docs/learn/05-scanners-and-shortlists.md`.
- 12 new tests (`tests/scanner/`), full local suite green, `ruff
  check`/`ruff format --check` clean, `mypy` clean on the scanner module
  (one pre-existing unrelated mypy gap: missing `types-PyYAML` stub in this
  venv for `core/config.py`, not touched by this PR).

## Where I stopped (exact)
- Branch: `claude/p4-scanner-stocks-page`, pushed, PR #57 open against
  `main`. Last commit: `501b486` "feat(p4): daily scanner, shortlist,
  Stocks page, scanner backtest".
- Nothing pending in this branch -- it's a complete, tested slice.

## Known duplication / merge-order risk (not blocking, but real)
1. `dashboard/_data.py` in this PR is a **byte-identical duplicate** of the
   same file on unmerged PR #56 (`claude/p3-live-paper-dashboard`). PR #56
   wasn't on `main` when this branch started, so there was nothing to
   import. Whoever merges the *second* of PR #56 / PR #57 should delete
   the duplicate, not keep both. Flagged in `docs/decisions.md`.
2. The scanner's ranking/target/stop logic (`scanner.py`) is a placeholder
   momentum score (`ponytail:`-tagged), not a real strategy, because
   T1/T2/T4/T6/ORB are still on unmerged PR #53. Once #53 merges, swap
   `scan_symbol`'s scoring for the real strategy's entry/stop/target --
   the filter/shortlist/backtest machinery around it does not need to
   change. ADR-0029 has the detail.

## What you need to do
1. **Owner**: decide PR #53/#56/#57 merge order (none conflict on files
   except the `dashboard/_data.py` duplicate noted above, which is a
   2-minute delete either way).
2. **Reviewer** (either model): PR #57 touches no risk/execution/broker
   code -- not an AGENTS.md §5 *mandatory* cross-model review case -- but a
   look would help, same as PR #56.
3. **Whoever does PR #53's merge**: when ready, come back to
   `scanner.py`'s `scan_symbol()` and swap the placeholder score for the
   real strategy score; it's the only place that needs to change.

## Open questions
None new from this session. The P3 open questions (live India data source,
PR #53 merge order) in note 0036 are still open and unaffected by P4.

## Model/usage notes
- Claude Sonnet 5, single session. Full local suite green, `ruff`/`mypy`
  clean on touched files.
