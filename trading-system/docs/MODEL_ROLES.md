# MODEL ROLES

As of **2026-11-14**. Plans and limits change; re-check with `/status` (Codex) and the Claude usage page.

## 1. What the owner has

| Plan | Status | Notes |
|---|---|---|
| **Claude Pro** | Ends in ~2 days (~2026-11-16) | Claude Code is bundled in paid plans with 5-hour and weekly limits shared across Claude products. Opus/Sonnet/Haiku are within plan limits. **Fable 5.2 was included for up to 50% of the weekly limit until 2026-11-16 11:59 pm PT (≈ 1:30 pm IST on 2026-11-17), then needs paid usage credits.** After the plan ends, Claude Code stops unless a plan or API credit is bought |
| **ChatGPT Plus** | Ongoing | Codex included in the plan. Per OpenAI help pages: Codex offers **Sol, Terra, Luna for Plus**, and Plus includes **GPT-6 Astra** in Work and Codex (gradual rollout). Astra needs Codex CLI **0.153.0+**. Usage is per 5-hour window plus weekly caps, shared with ChatGPT Work |

OpenAI's published estimates (local messages per 5 h) put **Astra at roughly 5-45 versus Sol 15-160 and Luna 350-3,000**; Astra's credit rate is about 5x Sol's. Treat Astra as scarce.

Neither subscription pays for the running system's **API** usage (Brain). See `BRAIN_AND_COSTS.md`.

## 2. Model capabilities in one line each

- Claude: **Fable 5.2** (top, hardest reasoning/long-horizon agentic), **Opus 5.5** (default for complex coding/agents), **Sonnet 5.5** (best speed/intelligence balance), **Haiku 5.5** (fast, cheap, high volume).
- OpenAI: **GPT-6 Astra** (hardest reasoning/coding/agentic), **GPT-6.1 Sol** (complex coding, research, computer use), **GPT-6.1 Terra** (balanced everyday work), **GPT-6 Luna** (fastest, cheapest).
- These descriptions come from vendor pages and reviews, not from our own tests. Section 6 defines a bake-off to correct assignments with evidence.

## 3. Principles

1. Different tasks to different tiers; do not give everything to one model.
2. **Author != reviewer.** Critical modules (`risk`, `execution`, `backtest`, `brokers`) get a cross-model review; ideally cross-company.
3. Tests for a component are written **blind** from the spec by a different model than the author.
4. Spend scarce models (Fable now, Astra always) on the highest-stakes work: specs, risk, reviews, hard bugs.
5. Specs written by the strongest models are the durable asset that outlives any plan.

## 4. Phase A: next ~2 days — Claude (foundation sprint P0)

| Model | Work | Notes |
|---|---|---|
| **Fable 5.2** (sparingly; 2-3 short focused sessions) | Review `MASTER_PLAN.md` for gaps; deepen `RISK_SPEC.md` into `docs/specs/RISK_ENGINE_SPEC.md` (state machine, edge cases); write `docs/specs/RED_TEAM.md` (adversarial scenarios) | Uses limits fast; stop when value drops |
| **Opus 5.5** | Repo scaffolding refinements, CI, `src/trading/core/` contracts (Pydantic models, enums, clock, config loader), adapter Protocols, `docs/specs/CONTRACTS.md`, `ADAPTERS.md`, `TEST_SPEC_*.md` for risk/backtest/adapters/candles, `GIT_WORKFLOW`/handoff verification | The main workhorse for P0 |
| **Sonnet 5.5** | `docs/specs/STRATEGY_SPEC_*.md` (turn `STRATEGIES.md` rules into pseudo-code + test vectors), lesson drafts `docs/learn/00-03`, config templates, `PAGES.md` details | Cheaper; steady output |
| Haiku 5.5 | Only mechanical formatting/checks if needed | |

Everything must be committed and pushed, and a handoff note written, **before the Claude plan ends**.

## 5. Phase B: after Claude access ends — ChatGPT Plus (Codex)

| Model | Used for | Why |
|---|---|---|
| **GPT-6 Astra** (a few sessions/day max) | Review of `risk`, `execution`, `backtest`; final architecture reviews; hard debugging; red-teaming | Strongest reasoning, spent where money is at stake |
| **GPT-6.1 Sol** (main workhorse) | Backtester, risk engine implementation, broker/data adapters, Brain layer, strategy templates, dashboard UI | Complex coding with a workable allowance |
| **GPT-6.1 Terra** | Bhavcopy pipeline, scanner, news ingestion, Telegram, API endpoints, **writing blind tests from specs** | Balanced cost |
| **GPT-6 Luna** | Docs, boilerplate, fixtures/test data, formatting, simple refactors, lesson formatting | Cheapest, largest allowance |

Component ownership (author -> reviewer):

| Component | Author | Reviewer / blind tests |
|---|---|---|
| Contracts, specs (P0) | Claude (Opus/Fable) | Astra review at start of P1 |
| Risk engine + kill switch + order router | Sol | Blind tests: Terra (from spec). Review: Astra |
| Backtester engine | Sol | Second reference backtester: Terra. Review: Astra |
| Broker/data adapters | Sol | Contract tests: Terra. Review: Sol (other session) or Terra |
| Bhavcopy/scanner/corp-actions | Terra | Review: Sol |
| Strategy templates | Sol | Known-answer vectors from Claude's specs; Terra tests |
| Brain layer + cost guard | Sol | Review: Astra |
| Dashboard/UI | Sol | Review: Terra |
| Telegram, news, usage page | Terra | Review: Luna/Terra spot-check, Sol on logic |
| Docs, lessons | Luna (draft) | Terra spot-check |

**Losing Claude as an independent reviewer:** compensate with (a) the independent specs, invariants, test specs and red-team list written by Claude in P0, (b) different OpenAI models/effort levels and fresh sessions as reviewers, (c) **before the first live money, buy one month of Claude Pro or API credit and run a Claude audit of `risk` and `execution`** (`TESTING.md` §6).

## 6. Bake-off protocol (replace guesses with evidence)

After P1 starts: give two models the same small, well-specified task (e.g., implement `ATR` incremental + batch with tests). Compare: tests passing, hidden-test pass rate, defects found by a third model, time/usage cost. Update this table via an ADR in `decisions.md`.

## 7. Usage discipline

- Check `/status` or usage pages at session start; plan work to fit the 5-hour window.
- Keep prompts focused; point models at specific files and specs rather than the whole repo.
- Record in the handoff note which model did what, so future sessions know provenance.
- Never let a session end with unpushed work.
