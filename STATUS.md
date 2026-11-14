# STATUS (living board — update every session)

Last updated: 2026-11-14 18:10 IST by Claude Code (starting P0)

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
1. Owner: complete `docs/SETUP_CHECKLIST.md` (repo, branch protection, handoffs branch, first prompts).
2. Claude Code: read note 0001 and start P0 in priority order.
3. Codex: read note 0002; confirm CLI version/models; wait for P0 handoff, or start P1 items that do not depend on contracts only if note 0002 allows.

## Blockers / needs-human
- Open questions listed in `docs/MASTER_PLAN.md` §13 (capital, brokers, exchange, VM, repo name, allocations).

## Environment facts (update when they change)
- Owner plans: Claude Pro (ends ~2026-11-16), ChatGPT Plus (ongoing).
- Static-IP rule applies to real India orders; research/paper can run on the laptop.
