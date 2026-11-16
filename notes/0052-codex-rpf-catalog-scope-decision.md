---
id: 0052
from: codex
to: dishant
date: 2026-11-16 15:00 IST
subject: RPF needs a catalog-scope and fixed-parameter decision before implementation
status: needs-human
refs: ["PR #53", "docs/specs/P1_CANDIDATES.md", "docs/BUILD_ORDER.md"]
---

## Current state

The existing 15 strategy variants are already merged, executable, and frozen
as `p1-catalog-v3` by PR #53: 12 daily candidates plus 3 intraday ORB
candidates. Their multiple-testing family is exactly 15; the two baseline
comparators are not hypotheses.

RPF is intentionally deferred in the current catalog. Its prose describes an
idea, but does not yet define a runnable strategy: it lacks fixed values for
the Donchian window, what makes a breakout "failed", SMA slope period,
volatility ceiling/contraction measurement, pullback deadline and threshold,
recovery confirmation, ATR stop multiple, and time-stop length.

## Decision required

Choose whether RPF is:

1. **A separate, future research catalog (recommended):** preserve the
   P1 `p1-catalog-v3` family at 15 and specify/implement RPF as a separately
   versioned hypothesis before that separate study's data is inspected; or
2. **A 16th P1 hypothesis:** create a new P1 catalog version, change the
   pre-registered hypothesis count and multiple-testing correction from 15 to
   16, then specify and implement RPF before any P1 result is read.

Codex must not choose this silently: it changes the statistical family and the
promotion interpretation. Once the owner selects scope, Codex can propose a
fixed, auditable mechanical rule for approval before implementation.
