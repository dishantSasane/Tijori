# Multi-Market Trading System

A learning-first, low-cost, **paper-by-default** system that watches Indian stocks, US stocks, crypto, commodities, currencies (and later options and a small memecoin sleeve), finds setups with tested strategies, explains each alert (entry / target / stop-loss / reason), and trades live only after a strategy has earned trust.

Built by two AI agents (Claude Code and Codex) under the owner's approval. **Nothing reaches `main` without the owner.**

> Status: planning complete, building not started. See `STATUS.md` on the `handoffs` branch for live status.

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
