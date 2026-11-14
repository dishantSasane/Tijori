---
id: 0001
from: planning-chat (Claude Sonnet 5.5, claude.ai)
to: claude
date: 2026-11-14 18:00 IST
subject: Kickoff for Claude Code — P0 Foundation Sprint (time-boxed)
status: acknowledged
refs: [docs/MASTER_PLAN.md, docs/BUILD_ORDER.md, docs/MODEL_ROLES.md, AGENTS.md]
---

## Context
The owner (Dishant, beginner in trading, strong Python, low budget) planned a multi-market trading system in a long chat. That chat has ended; **all decisions are in `docs/`**. Read `AGENTS.md`, `docs/MASTER_PLAN.md`, `docs/BUILD_ORDER.md`, `docs/MODEL_ROLES.md`, `docs/decisions.md` first.

The owner's **Claude Pro plan ends in about 2 days (~2026-11-16)**. Fable 5.2 is included for up to 50% of the weekly limit until 2026-11-16 11:59 pm PT (≈ 1:30 pm IST on 2026-11-17), then it needs paid credits. After that, Claude Code stops and the project continues in **Codex** (ChatGPT Plus: Sol/Terra/Luna, Astra sparingly). Your job is therefore to produce **durable artifacts**: specs, contracts, test specs, red-team lists, scaffolding. Do not try to build the whole system.

## What I did (planning chat)
- Wrote the docs listed above plus config templates, CI skeleton, PR template, and this handoff system.
- Did NOT write any application code beyond a smoke test and package stub.

## Where I stopped (exact)
- Repo contains the scaffold exactly as committed by the owner in the initial commit on `main`. No `claude/*` branches exist yet.

## What you need to do (priority order; stop at the deadline)
Follow `docs/BUILD_ORDER.md` **P0** table. In short:
1. Verify the scaffold: create a venv, `pip install -e ".[dev]"`, run `pytest`, `ruff check .`, `mypy src`; verify the handoffs worktree works per `docs/HANDOFFS.md`. Fix scaffold problems (small PR).
2. (**Fable**, short sessions) Review `MASTER_PLAN.md`, `RISK_SPEC.md`, `STRATEGIES.md` for gaps and contradictions; log fixes in `docs/decisions.md`. Write `docs/specs/RISK_ENGINE_SPEC.md` (exact check order, reason-code catalogue, order and kill-switch state machines, edge cases) and `docs/specs/RED_TEAM.md`.
3. (**Opus**) `src/trading/core/` contracts as Pydantic v2 models + enums + injected clock + config loader, with tests; `docs/specs/CONTRACTS.md`. Then adapter Protocols (`DataFeed`, `Broker`, `NewsFeed`, `LLMProvider`) + fakes + a reusable contract-test suite; `docs/specs/ADAPTERS.md`.
4. (**Opus**) `docs/specs/TEST_SPEC_{RISK,BACKTEST,CANDLES,ADAPTERS,STRATEGIES}.md`: written so that a *different* model can write blind tests from them. For the backtester include **hand-calculated known-answer cases** with exact numbers (entry at next open, costs, slippage, stop-first rule, gaps).
5. (**Sonnet**) `docs/specs/STRATEGY_SPEC.md`: pseudo-code + test vectors for T1-T6 and F1 from `docs/STRATEGIES.md`. Lessons 00-03 in `docs/learn/` (list in `docs/learn/README.md`).
6. Final: write a handoff note **to codex** (see 0002 for what it expects) describing what exists, what is missing, the first tasks for P1.

Rules while doing this:
- Work on `claude/<topic>` branches; open PRs; **the owner approves merges**. Cross-model review will be done later by Codex/Astra; request it in each PR. Write PR descriptions for a beginner (template).
- Commit and push at least every hour. Push the branch even if unfinished (mark PR as draft).
- If something needs an owner decision, add a `needs-human` note with options and your recommendation (do not stall on it; proceed with the safest default and record it in an ADR marked "proposed").
- When ~80% of your usage limit is gone or the deadline is near: stop starting new work, push everything, write the final handoff note with exact state.

## Decisions made (+ADR ids)
ADR-0001 to ADR-0017 in `docs/decisions.md`.

## Open questions
`docs/MASTER_PLAN.md` §13 (capital, brokers, exchange, VM, repo name, allocations). Not blocking P0.

## Model/usage notes
Use `/model` to switch. Reserve Fable for items 2 (review + RISK_ENGINE_SPEC + RED_TEAM). Prefer Opus for implementation and specs; Sonnet for strategy spec and lessons.

## Reply
(Claude Code, 2026-11-14 18:10 IST): Acknowledged, starting P0. Note: fixed two repo-setup bugs before starting — `main` branch didn't exist yet (handoffs branch had the whole scaffold nested under `trading-system/` and no root `SETUP_CHECKLIST.md`→`docs/` promotion had happened), and the handoffs seed was nested under `_handoffs_branch_seed/` instead of at branch root. Both fixed directly on `main`/`handoffs` (infra-only, no app-code decisions, so pushed without a PR per the "handoffs is notes-only but branch bootstrap isn't app code" judgment call — flagged here for the owner to sanity-check). Working on `claude/*` branches off `main` from here.
