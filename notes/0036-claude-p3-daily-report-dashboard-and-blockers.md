---
id: 0036
from: claude
to: both
date: 2026-11-16 15:00 IST
subject: P3 — daily report + dashboard shipped (PR #56); live adapter and ORB-live-wiring blocked, need owner decisions
status: needs-human
refs: ["PR #56", "docs/BUILD_ORDER.md P3", "docs/decisions.md ADR-0029/30/31", "PR #53", "docs/specs/DATA_SOURCES.md"]
---

## Context
Picked up P3 (STATUS.md had it as "Codex, waiting" — nobody had started it).
First checked `origin/main` and this file before writing anything, per the
previous session's note 0035 (P2 duplicate-work mistake). P3's 5 items per
BUILD_ORDER.md: live data adapter, ORB/breakout live in paper, auto-paper
shadow, Streamlit dashboard, daily report.

## What I did
- Built and shipped (PR #56, branch `claude/p3-live-paper-dashboard`):
  - **Daily report** (`src/trading/reporting/daily_report.py`): fills, risk
    rejection reasons, signal outcomes/P&L for a UTC date, reading only the
    shared state DB. Tests pass, ruff/mypy clean.
  - **Dashboard** (`dashboard/`): Streamlit Home + India + Paper ledger +
    Strategies pages, all read-only over the state DB (`docs/PAGES.md`'s
    page list). Deliberately reads SQLite directly instead of through
    `docs/PAGES.md` §3's not-yet-built FastAPI layer — documented as
    ADR-0030, not a silent deviation.
  - **Checked auto-paper-shadow (item 3)**: it's **already done**. PR #50
    (merged) already has `Mode.PAPER` + `ModeGate.route()` auto-routing
    every allowed signal to the paper broker with zero human action. No new
    code needed; just documented it in `docs/learn/04-*.md` so nobody
    re-builds it.
- Did NOT build (see "Open questions" — both need an owner decision):
  - **Live NSE data adapter.** `docs/specs/DATA_SOURCES.md` shows no India
    live-feed source is actually *selected* — Upstox live-feed terms
    unconfirmed; Angel One/FYERS both need the owner's own account/app
    setup first. Writing adapter code against an unconfirmed/unselected API
    would be guesswork.
  - **ORB/breakout strategies wired live into paper.** `src/trading/
    strategies/` on `main` only has `phase1.py` — T1/T2/T4/T6/ORB are still
    on **unmerged** PR #53 (STATUS.md says "implementation-complete,
    Claude-reviewed, approved" but not merged). Wiring against an unmerged
    branch risks repeating exactly the kind of duplicated/stale-ref mistake
    note 0035 flagged for P2.

## Where I stopped (exact)
- Branch: `claude/p3-live-paper-dashboard`, pushed, PR #56 open against `main`.
- Last commit: `c26bc5b` "feat(p3): add daily report and read-only Streamlit dashboard".
- Next file/function: none pending in this branch — it's a complete, tested
  slice. The next *new* work is either (a) a live-adapter branch once a
  source is picked, or (b) wiring strategies once PR #53 merges.

## What you need to do
1. **Owner**: pick (or confirm) a live India data source for P3's adapter —
   see Open Questions below.
2. **Whoever merges next**: confirm PR #53's merge status/order before any
   session starts wiring ORB/breakout into the live paper pipeline.
3. **Reviewer** (either model): PR #56 touches no risk/execution/broker
   code, so it's not an AGENTS.md §5 *mandatory* cross-model review case,
   but a look would help — it's new surface area (reporting + dashboard).

## Decisions made (+ ADR ids)
- ADR-0029: daily report scopes by UTC date-prefix string match (cheap,
  correct today; breaks only if timestamp storage format changes).
- ADR-0030: dashboard reads SQLite directly, not through `docs/PAGES.md`'s
  API (which doesn't exist yet) — documented simplification, not a gap.
- ADR-0031 (needs-human): live adapter + ORB live-wiring deferred; see Open
  Questions.

## Open questions
- **Live India data source** (ADR-0031). Options from `docs/specs/
  DATA_SOURCES.md`: (a) Upstox — already used for historical data in this
  repo, but its live-feed terms/limits are unconfirmed in the docs; (b)
  Angel One SmartAPI — explicitly offers free live feeds but needs the
  owner's own account/app and documentation access was restricted when
  this was researched; (c) FYERS Standard — free, documented rate/socket
  limits (100 symbols, no seconds data). My recommendation: confirm Upstox
  first since the historical adapter and account groundwork already exist
  here — cheapest path if its live-feed terms turn out to permit this use;
  otherwise FYERS has the most concretely documented free limits of the
  three. This is the owner's call (cost/account-setup tradeoff), not mine.
- **PR #53 merge order**: should it merge before or after P3's live-wiring
  work starts? If it's blocked on something, say what, so the next P3
  session doesn't wait on it blindly.

## Model/usage notes
- Claude Sonnet 5, single session. Full local suite (257 tests) green,
  `ruff check` and `mypy` clean on all touched files after the change.
