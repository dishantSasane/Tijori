---
id: 0031
from: codex
to: both
date: 2026-11-15 19:45 IST
subject: Correct Upstox split finding; screen unhandled actions
status: open
refs: [codex/p1-build, docs/specs/CORPORATE_ACTIONS.md, tests/storage/test_corporate_actions.py]
---

## Context
This supersedes the price-basis conclusion in note 0030. The exact Upstox fixture row was reread: the 2024-01-04 NESTLEIND close is ₹1,355.80, not ₹13,558. The ex-date close is ₹1,333.20 on 2024-01-05, the official 10:1 split date (NSE circular FAOP60123).

## What I did
- Corrected the real known-answer test: prior/ex-date closes are near-continuous at about 0.983 ratio. The prior candle is already on the post-split price scale; a raw-scale prior close would be about ₹13,558, and the 10:1 adjusted equivalent about ₹135.58. Therefore Upstox is pre-adjusted for this observed split (case a); do not apply a second 10:1 transform to it.
- Corrected `CORPORATE_ACTIONS.md`, `DATA_SOURCES.md`, `BUILD_ORDER.md`, and the P1 source decision note. This conclusion is limited to the NESTLEIND split/event; other actions and symbols still need validation.
- Added normalized NSE row parsing/classification for split, bonus, demerger, rights, dividend, and unknown action purpose (`other`). It uses symbol, purpose, ex-date, and source reference; it assigns no ratio/factor.
- Added `inspect_unhandled_actions` to flag in-window actions for candidate symbols. Split/bonus only count as handled with an exact `(symbol, ex-date)` handled key (provider adjusted or approved transformer applied). Demerger, rights, dividend, and unknown actions always flag.
- Added `screen_backtest_symbols`: affected symbols are excluded unless that exact `(symbol, ex-date, kind)` has explicit review. Flags remain in result for audit. The future orchestrator must call it before both primary and reference replay and record flags/exclusions/reviews.
- Added tests for NSE-style row parsing, event classification, window boundaries, exact event coverage/review and default exclusion.
- Recorded the future P1c promotion policy note: intraday candidates require longer forward paper observation and more conservative sizing than daily; exact thresholds must be prewritten, not invented here.
- Verification: all pytest, Ruff, Ruff format, mypy and `git diff --check` passed.

## Where I stopped (exact)
- Branch: `codex/p1-build`
- Last commit: `87bf195`; code remains uncommitted and no PR is open.
- No automated NSE downloader was added; this is a parser/screen for normalized authorized feed rows. Existing source-rights/coverage gate remains in force.
- The screen is a reusable preflight contract; existing low-level backtest functions do not yet accept action coverage directly. Wire this preflight into the P1 experiment orchestration before real result generation.
- Intraday history probe needs no repeat. OAuth renewal remains deferred; loader takes a fresh runtime token.

## What you need to do
1. Re-review the corrected NESTLEIND fixture interpretation and corporate-action screening API.
2. Wire screening into both primary and reference experiment orchestration and persist the flags.
3. Resolve permitted complete corporate-action feed/coverage; add more provider-basis cases, especially event types with subsequent actions (e.g. bonus adjustment layering).
4. Keep the P1c intraday promotion bar explicit: longer paper period and more conservative sizing, with numeric gates frozen before results.

## Decisions made (+ ADR ids)
- Correction: observed Upstox values indicate case (a), pre-adjusted, for NESTLEIND 10:1 split 2024-01-05. Previous note 0030's statement of case (b) is wrong and superseded.
- Do not auto-adjust demergers, rights, dividends, or unknown corporate actions. Flag and exclude unless exact event is reviewed.
- Intraday candidates receive a stricter promotion bar (longer paper observation, smaller/more conservative sizing); numeric thresholds remain to be set before evaluation.

## Open questions
- What event-level record will establish that the provider series already adjusted a split/bonus for each symbol/action?
- Which authorized complete action source will supply point-in-time ex-date rows and corrections?
- Exact longer paper duration and conservative intraday size limits must be frozen in promotion policy.

## Model/usage notes
- Implementation by Codex. No real feed harvest beyond the prior authorized single event probe; no credentials were recorded.

## Reply
