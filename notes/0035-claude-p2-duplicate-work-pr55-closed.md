---
id: 0035
from: claude
to: both
date: 2026-11-16 IST
subject: P2 task re-assigned to me duplicated already-merged PR #50 — closed without merge
status: needs-human
refs: [PR #55 (closed, no merge), PR #50 (merged, main), docs/specs/RISK_ENGINE_SPEC.md, docs/specs/PAPER_BROKER_SPEC.md, docs/specs/TELEGRAM_ALERT_SPEC.md]
---

## What happened (so this doesn't happen again)

I was asked to implement P2 (risk engine, paper broker, mode gate, SQLite
state, outcome tracker, Telegram alert wiring, kill switch) end to end in a
fresh worktree. I read `AGENTS.md`/`RISK_SPEC.md`/the P2 specs, but I did
**not** fetch `origin/main` or read `STATUS.md` on `handoffs` before
branching (skipped AGENTS.md §3's read order, step 3) — I branched from a
stale local `main` ref in the worktree that predated PR #50.

PR #50 (`claude/p2-implementation`) already implements this exact scope and
was **merged to `main` on 2026-11-15** (commit `39a50ea`): `src/trading/risk/`
(engine, kill_switch, portfolio, sizing, decision_store, audit, promotion,
fakes), `src/trading/broker/` (paper_broker, reconciliation), `src/trading/
alerts/telegram.py`, plus `tests/risk/`, `tests/broker/test_kill_switch_drill.py`
(the full 6-step drill), `tests/alerts/test_telegram.py`. `STATUS.md` already
said "implemented, under review" for P2 before I started.

I built a parallel, independent implementation of the same surface
(`src/trading/risk/engine.py`, `mode_gate.py`, `kill_switch.py`,
`src/trading/execution/paper_broker.py`, `outcome_tracker.py`,
`src/trading/adapters/telegram_alert.py`, `src/trading/storage/state_store.py`,
plus a full test suite including my own kill-switch drill test) on
`claude/p2-paper-risk-engine`, opened PR #55, then discovered the collision
while writing this handoff note (checking `STATUS.md` for the handoff, which
I should have done *first*). **PR #55 is closed without merge** — I left a
comment on it explaining why. Nothing from it was merged to `main`.

## Is there anything worth salvaging from PR #55?

I checked `origin/main` for one real gap: an `OutcomeTracker` /
`signal_outcomes` persistence layer. `SignalOutcome` (the contract) exists in
`trading/core/models.py`, but I did not find a tracker class or table reading/
writing it on `main` as of commit `39a50ea` — my `src/trading/execution/
outcome_tracker.py` (on the now-closed `claude/p2-paper-risk-engine` branch)
is small (~40 lines) and might be worth a second look if the owner/Codex
confirms it's genuinely still missing after reviewing PR #50's full diff
properly (I only grepped; I did not read PR #50 end to end). I did **not**
re-open or push this separately, to avoid adding a second unreviewed
branch while the collision itself is still fresh — flagging it here instead.

I also wrote `docs/learn/04-risk-engine-and-kill-switch.md` and an ADR
(`docs/decisions.md` ADR-0028) on the closed branch; both describe generic
risk-engine/kill-switch concepts accurately (not tied to my specific
abandoned implementation) and could be ported over if useful, but I have not
pushed them anywhere live — they only exist on the local, closed branch.

## What the owner/next session needs to decide

1. **Confirm `STATUS.md`'s "P2 implemented, under review" (PR #50, merged)
   is in fact the one to keep building on** — I have not reviewed PR #50's
   contents in depth (I only confirmed its file list and that it's merged),
   so I cannot personally vouch for its correctness. Per AGENTS.md §5,
   `risk`/`execution` modules need a **different-model** review before the
   owner merges/trusts them further — note 0032 and `STATUS.md` line for P2
   say "under review"; I don't know if that review (Codex or Astra) has
   actually happened yet since the merge. That's the real open question,
   not whether the code exists.
2. Whether the `OutcomeTracker` gap above is real and worth a small,
   targeted PR (not a full re-implementation) against current `main`.
3. **Process fix, not a code fix:** whoever picks up the next phase should
   `git fetch origin <target-branch>` and read `STATUS.md` *before* running
   `git checkout -b ... main` in a fresh worktree — a worktree's local
   `main` ref is not guaranteed fresh. I'm flagging this explicitly because
   it cost this entire session.

## Branches/PRs touched this session

- `claude/p2-paper-risk-engine`: exists locally in my worktree, pushed to
  `origin`, PR #55 opened then **closed without merge**. Safe to delete the
  remote branch; I have not deleted it myself in case the owner wants to
  look at the outcome-tracker/lesson/ADR content first.
