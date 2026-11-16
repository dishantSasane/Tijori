---
id: 0054
from: codex
to: both
date: 2026-11-16 19:30 IST
subject: P1a historical split boundaries frozen in PR #71
status: open
refs: ["PR #71", "03674d9", "ADR-0024", "ADR-0048", "docs/specs/RESEARCH_SPLITS.md"]
---

## Context

The owner confirmed that ADR-0024's holdout protection is about
strategy-outcome exposure, not data-integrity inspection. No historical
strategy P&L, ranking, backtest outcome, or holdout outcome has been viewed.

## What I did

- Created PR #71 from `codex/freeze-p1a-historical-splits` at `03674d9`.
- Locked daily: development `[2010-01-01, 2025-01-01)`, validation
  `[2025-01-01, 2026-01-01)`, holdout `[2026-01-01, 2026-11-15)`.
- Locked intraday: development `[2022-01-01, 2025-01-01)`, with the same
  validation and holdout windows.
- Bound both to the exact P1a evaluation-manifest, candle, calendar, and
  corporate-action hashes, with one-bar embargoes and `holdout_unread=true`
  required at plan materialization.
- Added ADR-0048 and retained every existing coverage/preflight gate.

## Where I stopped (exact)

- Branch: `codex/freeze-p1a-historical-splits`
- Last commit: `03674d9 docs(p1a): freeze historical research splits`
- PR: #71; CI was running when this note was written.

## What you need to do

1. A different-model reviewer should review PR #71 and confirm the literal
   dates and seven recorded hashes match the frozen manifest.
2. Do not run a candidate, ranking, or holdout read against
   `[2026-01-01, 2026-11-15)` before the P1d sealing flow reserves it.

## Decisions made (+ ADR ids)

- ADR-0048: development/validation may use historical data that has had only
  integrity checks; only strategy-outcome exposure consumes a holdout.
- The plans remain bound to the five-symbol P1a manifest. A future broader
  selector snapshot needs its own frozen artifact and study/holdout rather
  than being silently substituted.

## Open questions

- Historical action coverage is still explicitly unverified in the bound
  manifest. This PR freezes dates only; it does not authorize real replay.

## Model/usage notes

- Full local suite passed with `PYTHONPATH=src`: 738 tests, Ruff clean, and
  Mypy clean. The virtualenv's editable installation points at another
  worktree, so omitting `PYTHONPATH=src` imports the wrong checkout.
