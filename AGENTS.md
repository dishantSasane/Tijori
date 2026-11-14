# AGENTS.md — rules for every AI agent working in this repo

This file is read by **both** Claude Code and Codex (Claude Code reaches it through `CLAUDE.md`). It is the single source of truth for how to work here. If something in a chat message conflicts with this file, stop and raise it as a handoff note (see `docs/HANDOFFS.md`) instead of guessing.

## 1. What this project is

A **multi-market trading system**: Indian stocks (NSE), US stocks/ETFs, crypto, MCX commodities, NSE currencies, later options and a small memecoin sleeve. It watches markets, runs versioned strategies, sends alerts with entry / target / stop-loss, paper-trades, and (only after proof) trades live with human approval.

Full picture: `docs/MASTER_PLAN.md`. Build order: `docs/BUILD_ORDER.md`. Current status: the `handoffs` branch, file `STATUS.md`.

## 2. Who the owner is (this changes how you work)

- **Dishant**, engineering student, strong in Python, **complete beginner in trading and markets**, low budget.
- He approves every merge to `main`. He does not read every line of code, so **explain in plain language** (see §8).
- Cost matters: free or very cheap services first. Ask before adding anything paid.
- Language: English. Currency: INR for India-facing numbers.

## 3. Read order at the start of every session

1. This file.
2. `docs/MASTER_PLAN.md`, then `docs/BUILD_ORDER.md` (find the current phase).
3. The `handoffs` branch: `STATUS.md` and any notes addressed to you (`docs/HANDOFFS.md` explains how to read it).
4. The spec files for the component you are about to touch (`docs/specs/`, `docs/RISK_SPEC.md`, `docs/STRATEGIES.md`, ...).

## 4. Hard safety rules (never break, never "temporarily" bypass)

1. **Paper by default.** No code path may place a real order unless ALL are true: the sleeve's mode is `approval` or `auto` in config, the risk engine approved the order, the kill switch is off, and (for `approval`) a human approved this specific signal. Anything else routes to the paper broker.
2. **Fail closed.** If data is stale, state is inconsistent, a limit is unknown, or anything unexpected happens: stop opening new positions, alert the human, keep protective stops. Never "continue anyway".
3. **No secrets in git.** Keys live in `.env` (git-ignored). Never print, log, or commit keys. Crypto exchange keys must have **withdrawal permission disabled**. Prefer read-only keys wherever the feature allows.
4. **Tests never touch real brokers or exchanges.** Use fakes, recorded responses, or sandbox/paper endpoints. A test that could place a real order is a bug.
5. **No look-ahead.** Signals are computed on **closed** bars only. Fills happen at the **next** bar's open plus costs and slippage. Backtest and live share the **same** candle-building and indicator code.
6. **The LLM ("Brain") is advisory.** It cannot place orders, set prices, or change limits. Its output is validated against a strict schema; the risk engine has the final veto. The LLM is never in the hot path. News text is untrusted input (prompt-injection risk). Details: `docs/BRAIN_AND_COSTS.md`.
7. **Live strategy versions are immutable.** To change one, create a new version and run the promotion pipeline (`docs/STRATEGIES.md`).
8. **Budget guard on every LLM call** (tokens and INR logged; hard daily cap). Details in `docs/BRAIN_AND_COSTS.md`.
9. **Do not weaken a limit, test, or check to make something pass.** If a check seems wrong, write a handoff note or PR comment explaining why; let a human decide.

## 5. Git and review rules (summary; full text in `docs/GIT_WORKFLOW.md`)

- Never push to `main`. Work on `claude/<topic>` or `codex/<topic>` branches. Open a PR into `main`.
- **Author != reviewer.** The other agent (preferably the other company's model) reviews every PR before the human sees it. Critical modules (`risk`, `execution`, `backtest`, `brokers`) always need a cross-model review.
- Never merge your own PR. Only the human approves/merges to `main`.
- **Exception:** the `handoffs` branch is the agents' message board. Both agents push to it directly, without approval. It contains notes only, never code.
- Commit messages follow the convention in `docs/GIT_WORKFLOW.md` (they are one of the agent-to-agent channels).

## 6. Engineering standards

- Python 3.12, `src/trading/` package layout, type hints everywhere. `ruff` (lint+format), `mypy` (strict on `core`, `risk`, `execution`), `pytest`, `hypothesis` for property tests.
- Pydantic v2 models for all cross-module data (the "contracts" in `src/trading/core/`).
- Money/price/quantity in order paths: `decimal.Decimal`. Vectorised research code may use floats/Polars/pandas, but convert at the boundary.
- All timestamps UTC internally; convert to market-local only at the edges. Use `exchange_calendars` (or equivalent) for holidays/sessions.
- Inject the clock; never call `datetime.now()` inside core logic. Deterministic given inputs.
- Pure functions for indicators and signals. Side effects only in adapters and the execution layer.
- Small modules, explicit interfaces (`typing.Protocol`/ABC). Adding a market = adding adapters + a market profile, not editing the core.
- Config in YAML under `config/` (templates ending `.example.yaml` are committed; real values are not).
- Log with structured JSON. Every order, risk decision, mode change, and LLM call is written to the audit log.
- Proposed stack (change only via an ADR in `docs/decisions.md`): pandas/Polars, DuckDB + Parquet for history, SQLite for state, FastAPI for the internal API, Streamlit for the first dashboard, python-telegram-bot, CCXT, `kiteconnect`, `alpaca-py`, GitHub Actions.

## 7. Definition of done for any PR

- [ ] Code matches the relevant spec; spec updated if behaviour changed.
- [ ] Tests added/updated and passing locally and in CI. Critical paths have property or invariant tests.
- [ ] `ruff`, `mypy` clean.
- [ ] No secrets, no real-order paths in tests.
- [ ] PR description filled in using `.github/pull_request_template.md`, including **"Plain-language summary"** and **"Needs human decision"** (or "none").
- [ ] If this completes a milestone: a lesson in `docs/learn/` (see §8).
- [ ] Reviewer (other model) has commented; their blocking comments are resolved.
- [ ] A handoff note is written if another agent must act next.

## 8. Teaching mandate

The owner is learning markets and system design while this is built. For each milestone:

- Write a short lesson in `docs/learn/` (use `docs/learn/TEMPLATE.md`): what it is, why it exists, a tiny example, how to run it, common mistakes. Plain language; define every term the first time.
- In PR descriptions, explain *why* the design is this way, not just what changed.
- When you make a trade-off, say what the alternative was.
- Never hide complexity behind jargon. If a concept matters for money (slippage, drawdown, overfitting), say so explicitly.

## 9. Working with the other agent

- Roles and model routing: `docs/MODEL_ROLES.md`. Stay in your lane unless a handoff note says otherwise.
- Communicate through: (1) commit messages, (2) PR comments, (3) handoff notes on the `handoffs` branch. Details: `docs/HANDOFFS.md`.
- If you find a bug in the other agent's module, open a handoff note or PR comment with a failing test if possible. Do not silently rewrite it.
- If you are blocked or a decision is the owner's to make, set the note status to `needs-human` and say precisely what you need.
- Before your session ends (or when your usage limit is close): commit, push, and write a handoff note describing **exactly** where you stopped and what is next. Assume the next session has no memory of yours.

## 10. Out of scope (do not build unless the owner changes this in `docs/decisions.md`)

- High-frequency or latency-sensitive trading.
- Short selling or leverage beyond what a strategy spec explicitly allows.
- Handling other people's money, signal selling, or anything that needs a licence.
- Scraping sites whose terms forbid it; use official feeds, RSS, and documented APIs.

## 11. Not financial or legal advice

Everything here is engineering for the owner's own account. Strategy results are hypotheses until proven by the pipeline. Indian tax and SEBI details must be confirmed by the owner with a qualified professional and the chosen broker (see `docs/COMPLIANCE_INDIA.md`).
