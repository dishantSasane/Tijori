# STATUS (living board — update every session)

Last updated: 2026-11-14 19:35 IST by Claude Code (P0 items 1/3/4 shipped, PR pending; see note 0004)

## Phase tracker (see docs/BUILD_ORDER.md on main)

| Phase | Owner | State | Notes |
|---|---|---|---|
| P0 Foundation sprint | Claude Code | in progress | **Deadline: Claude plan ends ~2026-11-16** (Fable 5.2 inclusion ends 2026-11-16 11:59 pm PT) |
| P1 Data layer + backtester | Codex | waiting on P0 | |
| P2 Paper broker + risk engine + minimal alerts | Codex | waiting | |
| P3 India Tier A paper end-to-end + dashboard | Codex | waiting | |
| P4 Tier B scanner + Stocks page | Codex | waiting | |
| P5 Crypto + US sleeves (paper) | Codex | waiting | |
| P6 Brain + News | Codex | waiting | |
| P7 Go-live readiness | both + owner | waiting | needs Claude audit before first live money |
| P8 Expansion | both | waiting | gated |

## Next 3 actions
1. Owner: inspect PR refs for `claude/p0-scaffold-verify` (#3/#5) and `codex/data-sources` (#2/#4); identify active PRs, review/CI, and merge only after cross-model review.
2. Claude (next session): P0 items 2 (RISK_ENGINE_SPEC, RED_TEAM), 7 (TEST_SPEC_*), 8 (STRATEGY_SPEC), 9 (lessons 01-03) — see note 0004.
3. Codex: keep waiting on P0; note 0003's spec questions have partial answers in its Reply section.

## Blockers / needs-human
- Open questions listed in `docs/MASTER_PLAN.md` §13 (capital, brokers, exchange, VM, repo name, allocations).

## Environment facts (update when they change)
- Owner plans: Claude Pro (ends ~2026-11-16), ChatGPT Plus (ongoing).
- Static-IP rule applies to real India orders; research/paper can run on the laptop.

## Codex pre-P0 checkpoint
- Research: `codex/data-sources` at `b3400e3` (pushed); note 0003 has findings and exact stopping point.
- CLI 0.166.0; Python 3.12.3; ChatGPT Plus confirmed through read-only app-server calls.
- Available: GPT-6.1 Sol, GPT-6 Astra, GPT-6.1 Terra, GPT-6 Luna (plus legacy models).
- Usage snapshot: five-hour window 12% used; weekly window 5% used. Recheck next session.
- Local ruff lint/format, mypy, pytest pass (one smoke test).
- Main/root layout and handoffs/root layout repaired; worktrees operational.
- P1 waiting on P0. NSE website ingestion is blocked pending authorized source/use; free live universe sizes need reconciliation (note 0003).

## Claude P0 checkpoint (2026-11-14 19:35 IST)
- Fixed repo bootstrap: `main` created (commit `2839936`), `handoffs` flattened
  (commit `e058593`) — see note 0004 for why `main` didn't exist before this.
- Branch `claude/p0-scaffold-verify`: P0 items 1 (verify, no fixes needed), 3
  (`trading/core/` contracts), 4 (`trading/adapters/` Protocols+fakes). 31
  tests, ruff/mypy clean. PR not opened (no gh/API token available); link in
  note 0004.
- Items 2, 5 (continuation), 6, 7, 8, 9, 10 of BUILD_ORDER P0 are NOT done yet.

- Publication checkpoint: PR #4 contains research and PR #5 contains Claude's foundation. Both are open, clean, and CI `test` passed. Codex review comments are posted; PR #5 has two blocking contract findings. P1 remains waiting.
