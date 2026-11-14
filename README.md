# Multi-Market Trading System

A learning-first, low-cost, **paper-by-default** system that watches Indian stocks, US stocks, crypto, commodities, currencies (and later options and a small memecoin sleeve), finds setups with tested strategies, explains each alert (entry / target / stop-loss / reason), and trades live only after a strategy has earned trust.

Built by two AI agents (Claude Code and Codex) under the owner's approval. **Nothing reaches `main` without the owner.**

> Status: planning complete, building not started. See `STATUS.md` on the `handoffs` branch for live status.

> ⚠️ **Known issues — backtest P&L and risk numbers must not be trusted yet.** Cross-model review of the P1 backtester/exit/scorecard PRs found bugs that can make reported risk and P&L silently wrong, not just display-wrong. Do not use any backtest result from the current code to decide a real capital allocation, a go-live date, or a strategy promotion. Fix tracking: handoff note on `handoffs` (see `STATUS.md`) and the PR comments listed below.
>
> - Overnight gap-through-stop risk on an already-open position is never recorded in the audit log (PR #29).
> - The realized-risk formula uses the wrong reference price; it only matches the spec's worked example by coincidence of zero slippage (PR #29).
> - The second reference backtester copies the same buggy formula, so it certifies the bug instead of catching it (PR #30).
> - The "overlap guard" silently drops signals with no trade, no audit, and no unfilled-signal record (PR #29).
> - Walk-forward split has no embargo: a signal on the last in-sample bar silently fills on the first out-of-sample bar (PR #29).
> - `ExitRequest`'s invariant I14 ("an exit can never open or increase a position") is enforced nowhere in code (PR #24).
> - `exit_id` defaults to a random value, so duplicate exit requests don't deduplicate (PR #24).
> - The primary backtester double-counts entry-side brokerage as a cost that's never actually charged, and silently trades a SELL signal as a long (PR #21).
> - PR #22's look-ahead tests were merged on a failing CI run — `ruff format` failed and pytest never executed before merge.
>
> Full detail, acceptance tests, and priority order: handoff note on the `handoffs` branch (see `STATUS.md`).

## Where to read

| You are... | Start with |
|---|---|
| An AI agent | `AGENTS.md` (Claude Code: `CLAUDE.md`), then `docs/MASTER_PLAN.md`, `docs/BUILD_ORDER.md` |
| The owner setting things up | `docs/SETUP_CHECKLIST.md` |
| Learning how it works | `docs/learn/` |

## Document map

| File | What it covers |
|---|---|
| `docs/MASTER_PLAN.md` | Vision, constraints, principles, the whole system on one page |
| `docs/ARCHITECTURE.md` | Layers, data flow, storage, processes, time handling |
| `docs/MARKETS.md` | Per-market profiles: hours, data sources, costs, universes, fills |
| `docs/STRATEGIES.md` | Strategy templates with exact rules, lifecycle, registry, versioning |
| `docs/RISK_SPEC.md` | Risk engine, limits, kill switch, invariants |
| `docs/TESTING.md` | The layered testing system and go-live gates |
| `docs/BRAIN_AND_COSTS.md` | How the LLM is used cheaply and safely |
| `docs/COMPLIANCE_INDIA.md` | SEBI retail algo rules, static IP, tax notes |
| `docs/BUILD_ORDER.md` | Phases, owners, reviewers, exit criteria |
| `docs/MODEL_ROLES.md` | Which model does what, given the owner's plans |
| `docs/GIT_WORKFLOW.md` | Branches, PRs, commit convention |
| `docs/HANDOFFS.md` | How the two agents talk to each other |
| `docs/PAGES.md` | Dashboard pages and alert cards |
| `docs/decisions.md` | Decision log (ADRs) |
| `docs/specs/` | Detailed specs written during the foundation sprint |
| `docs/learn/` | Plain-language lessons for the owner |
| `config/*.example.yaml` | Config templates |

## Quick start (after the foundation sprint)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest -q && ruff check . && mypy src
```

## Safety in one paragraph

Default mode is **paper**. Live orders need: sleeve mode `approval`/`auto`, risk-engine approval, kill switch off, and (in `approval`) a human tap. Everything fails closed. Keys never enter git. See `AGENTS.md` §4.
