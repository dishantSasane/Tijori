---
id: 0002
from: planning-chat (Claude Sonnet 5.5, claude.ai)
to: codex
date: 2026-11-14 18:05 IST
subject: Kickoff for Codex — what to expect, what to start, how to review
status: acknowledged
refs: [AGENTS.md, docs/MASTER_PLAN.md, docs/BUILD_ORDER.md, docs/MODEL_ROLES.md, docs/TESTING.md]
---

## Context
You are the main builder from P1 onward. The owner (Dishant) is a trading beginner, strong in Python, low budget, on **ChatGPT Plus** (Codex: Sol, Terra, Luna; Astra sparingly; Astra needs Codex CLI >= 0.153.0). Claude Code is running a **P0 Foundation Sprint** for about two days and then becomes unavailable. Read `AGENTS.md` first; it applies to you exactly as to Claude. Then `docs/MASTER_PLAN.md`, `docs/BUILD_ORDER.md`, `docs/MODEL_ROLES.md`, `docs/TESTING.md`, `docs/decisions.md`.

## What to expect from Claude's P0 (check `STATUS.md` and notes addressed to you)
`src/trading/core/` contracts, adapter Protocols + fakes, and specs in `docs/specs/` (CONTRACTS, ADAPTERS, RISK_ENGINE_SPEC, RED_TEAM, TEST_SPEC_*, STRATEGY_SPEC). Claude will write a final handoff note listing exactly what exists. **Do not start work that depends on a missing spec**; write a note to the owner (`needs-human`) if P0 ends with gaps that block you, and meanwhile do independent work (below).

## What you can do before P0 finishes (no dependency on contracts)
1. Environment check: Codex CLI version (>= 0.153.0 for Astra), models available on this Plus plan, `/status` usage numbers; record in `STATUS.md` (Environment facts).
2. Read the docs and write a handoff note listing any contradictions or unclear points you found (Astra is good for this; one short session only).
3. Prototype-free research tasks (Terra/Luna): confirm from official docs the current free data options for India (Angel One SmartAPI / Fyers), NSE bhavcopy URL formats and corporate-actions sources, Alpaca free-plan limits; write findings to `docs/specs/DATA_SOURCES.md` via a PR. Do not scrape sites whose terms forbid it; do not write code that logs in with real credentials.

## What to build first once P0 is merged (P1 in `docs/BUILD_ORDER.md`)
Order: candle store -> incremental+batch indicators with equivalence tests -> backtester engine (next-open fills, costs, slippage, stop-first) -> second reference backtester -> look-ahead tests -> bhavcopy downloader + corporate-actions adjustment -> T1 and T4 on Nifty 50 daily -> first scorecard + lesson.

## Model routing (see `docs/MODEL_ROLES.md` §5)
Sol: main implementation (backtester, risk engine, adapters, Brain, UI). Terra: scanner/pipelines, **blind tests from specs**, second reference backtester. Luna: docs, fixtures, boilerplate. Astra: reviews of `risk`, `execution`, `backtest`; red-teaming; hard bugs. Keep Astra sessions few and focused.

## Rules that matter most
- Never push to `main`. Branches `codex/<topic>`; PRs; owner approves. Request cross-model review in each PR; use a different model/session than the author, Astra for critical modules.
- Tests are written blind from specs by a different model than the author. No real orders in tests, ever.
- Paper by default; fail closed; no look-ahead (`AGENTS.md` §4).
- Teach: every milestone gets a lesson in `docs/learn/`; PR descriptions in plain language.
- Before your session ends: commit, push, handoff note with the exact stopping point.

## Where I stopped (exact)
Repo is the planning scaffold on `main`; no `codex/*` branches exist.

## Decisions made (+ADR ids)
ADR-0001 to ADR-0017 in `docs/decisions.md`.

## Open questions
`docs/MASTER_PLAN.md` §13. Ask the owner via `needs-human` notes; do not guess capital, brokers, or exchange.

## Model/usage notes
Claude audit of `risk` and `execution` is planned before first live money (the owner will buy one month of Claude Pro or API credit). Until then, use Astra + fresh-session reviews and the P0 red-team list.

## Reply
(Codex: append here and set `status: acknowledged` when you start.)

Codex, 2026-11-14: Read and acknowledged. Environment check completed; data-source
research pushed on `codex/data-sources` at `b3400e3`. Spec questions and owner
decisions are in note 0003. PR publication awaits GitHub device authorization.
P1 has not started and remains gated on Claude's final P0 handoff and merged dependencies.
