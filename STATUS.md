# STATUS (living board — update every session)

Last updated: 2026-11-14 by Codex (pre-P0 research; Claude P0 in progress)

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
1. Codex: publish `codex/data-sources` PR after GitHub device login; Claude reviews it.
2. Claude: resolve note 0003 spec questions during P0 and deliver the final handoff.
3. Owner: confirm data-access/provider choices in 0003 and branch protection; approve merges after review. Codex waits for P0 before P1.

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
