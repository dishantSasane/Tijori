# BUILD ORDER

Phases, owners, deliverables, and exit criteria. Each deliverable is a PR (except handoff notes). "A/R" = Author / Reviewer (`MODEL_ROLES.md`). Every milestone also produces a lesson in `docs/learn/`.

Status of each phase is tracked in `STATUS.md` on the `handoffs` branch.

---

## P0 — Foundation sprint (Claude Code; ~2 days; hard deadline: Claude plan end ≈ 2026-11-16)

Purpose: capture everything Claude is uniquely available for now, as durable specs/contracts/tests, so Codex can build alone afterwards.

Priority order (stop at the deadline; unfinished items go into a handoff note):

| # | Deliverable | Model | Files |
|---|---|---|---|
| 1 | Verify repo, CI green, branch protection assumptions, handoffs worktree works (`SETUP_CHECKLIST.md`) | Opus | repo |
| 2 | Review `MASTER_PLAN.md`, `RISK_SPEC.md`, `STRATEGIES.md` for gaps/contradictions; fix or log in `decisions.md` | **Fable** | docs |
| 3 | Contracts: Pydantic v2 models + enums (`MarketId`, `Mode`, `Candle`, `Tick`, `Signal`, `OrderRequest`, `Order`, `Fill`, `Position`, `RiskDecision`, `BrainVerdict`, `SignalOutcome`, `AuditEvent`), clock, config loader; tests | Opus | `src/trading/core/`, `docs/specs/CONTRACTS.md` |
| 4 | Adapter Protocols (`DataFeed`, `Broker`, `NewsFeed`, `LLMProvider`) + fake implementations + contract-test suite skeleton | Opus | `src/trading/adapters/`, `docs/specs/ADAPTERS.md` |
| 5 | Risk engine spec: state machine, edge cases, exact check order, reason-code catalogue | **Fable** | `docs/specs/RISK_ENGINE_SPEC.md` |
| 6 | Red-team scenario list (adversarial inputs, bypass attempts, prompt injection corpus) | **Fable** | `docs/specs/RED_TEAM.md` |
| 7 | Test specs: risk, backtester (incl. known-answer cases with hand-calculated numbers), candle builder, adapters, strategies (test vectors) | Opus | `docs/specs/TEST_SPEC_*.md` |
| 8 | Strategy spec pseudo-code + test vectors for T1-T6 and F1 | Sonnet | `docs/specs/STRATEGY_SPEC.md` |
| 9 | Lessons 00-03 (see `docs/learn/README.md`) | Sonnet | `docs/learn/` |
| 10 | Final handoff to Codex: what exists, what to build first, known gaps | Opus | handoffs branch |

Exit: items 3, 4, 5, 7 merged (or PR-ready) and a complete handoff note written. Items 6, 8, 9 are valuable but may slip.

---

## P1 — Data layer, strategy discovery, and regime-gated activation (Codex)

P1 was originally "pick strategies, backtest them." That framing rewarded the
candidate with the largest historical P&L, which is the candidate most likely
to be an overfit accident. P1 is restructured into five sub-phases: a frozen
data foundation, a pre-registered candidate library, an evaluation harness
with an experiment registry, a one-shot holdout evaluation, and a regime-gated
activation layer that decides which strategy (if any) is eligible at a given
moment. The goal is the strategy whose edge is least fragile, not the one with
the best backtest.

Each sub-phase is its own PR (or PR group) with its own exit criteria. A later
sub-phase must not start against data or splits that an earlier sub-phase has
not frozen.

### P1a — Data foundation

| Deliverable | A/R | Notes |
|---|---|---|
| Tier A daily history in Parquet (candle store + validation) | Sol / Terra | already done for the 6-symbol representative set |
| Corporate-action adjustment, verified | Terra / Sol | splits/bonuses must not silently corrupt returns; add a known-answer test per action type |
| Point-in-time Nifty 50 + Next 50 membership | Terra / Sol | **open problem — flag, do not guess.** If no authorized point-in-time source exists, say so in `decisions.md` rather than building on an unverified universe; survivorship bias is not optional to fix |
| Chronological split boundaries, written and frozen in config before any strategy runs | Sol / Terra | development period, validation period, untouched holdout; dates committed to config and never read until P1d |

Exit: corporate-action adjustment has known-answer tests; point-in-time
universe status is either resolved or logged as a `needs-human` blocker; split
boundaries exist in a committed config file with no strategy code reading the
holdout range.

### P1b — Candidate library (pre-registered)

| Deliverable | A/R | Notes |
|---|---|---|
| Fixed candidate family spec, declared before any ranking | Sol / Terra | buy-and-hold benchmark, cash/no-trade benchmark, moving-average trend, Donchian breakout, RSI/Bollinger mean reversion, volatility breakout, momentum, plus existing T1/T4 baselines |
| Declared parameter grid per candidate, with a hard cap on variations | Sol / Terra | state the cap explicitly in the spec file; no free-form parameter sweeps |
| Versioned, deterministic spec per candidate | Sol / Terra | same immutable-version discipline as `STRATEGIES.md` §6 |

Exit: every candidate and its parameter grid exists in a spec file before any
backtest of it runs; the cap on variations is a number written down, not an
intention.

### P1c — Evaluation harness and experiment registry

| Deliverable | A/R | Notes |
|---|---|---|
| Ranking metrics: net return after costs, expectancy, max drawdown, Calmar/Sharpe/Sortino, turnover and cost sensitivity, % profitable instruments, % profitable time windows, block-bootstrap confidence intervals, performance vs. buy-and-hold | Sol / Terra | raw rupee P&L is never a ranking key |
| Multiple-testing correction / reality-check method | Sol / Terra | name the method explicitly (e.g. White's Reality Check, SPA test, or a Bonferroni-style correction on the pre-registered candidate count); do not skip this because P1b capped variations — the cap bounds it, it doesn't replace it |
| Experiment registry | Sol / Terra | every candidate and variant attempted, including failures, logged with run ID, spec version, split used, and result, so the eventual winner can be discounted for the number of attempts behind it |

Exit: the registry has one row per attempted run (pass or fail); the ranking
report states which correction method was applied and shows ranked results
both with and without it.

### P1d — Holdout evaluation

| Deliverable | A/R | Notes |
|---|---|---|
| Shortlist frozen before the holdout is read | Sol / Terra | frozen means: no further parameter changes once this step starts |
| One-shot evaluation on the untouched holdout from P1a | Terra / Sol | |
| Explicit, pre-written rejection rule | Sol / Terra | a candidate is rejected if its advantage disappears after costs, or does not hold across regimes; write the rule before seeing the holdout result so it cannot be renegotiated after |

Exit: holdout is evaluated exactly once per shortlist candidate; rejections
and survivors are both recorded with the rejection rule applied, not a
post-hoc judgment call.

### P1e — Regime-gated activation layer

Each strategy that survives P1d carries declared preconditions (trend state,
volatility regime, liquidity) under which it is eligible. At each decision
point the activation layer selects the eligible strategy or strategies for an
instrument.

| Deliverable | A/R | Notes |
|---|---|---|
| Rule set spec: small, declared in advance, versioned alongside the strategies it gates | Sol / Terra | a complex activation layer tuned on development data is a second overfitting surface — cap its complexity and note the cap in the spec, same discipline as P1b |
| Rule set subject to the same split discipline as P1a-P1d | Terra / Sol | the activation rules themselves get a development/holdout split; they are not exempt because they "just route," not predict |
| Overlap handling | Sol / Terra | when two strategies are eligible and signal the same instrument, the existing overlap guard (`RISK_SPEC.md` §2 check 9/15, I11) applies; the dropped signal is audited with a reason code |
| Default-flat behaviour | Sol / Terra | when no strategy is eligible, the system stays flat; abstention is a valid, expected output, not a failure |
| Activation-frequency tracking per strategy | Terra / Sol | a strategy that rarely activates is a candidate for removal from the library |

Exit: activation rule set exists as a versioned spec with a stated complexity
cap; overlap and abstention are both covered by tests; activation frequency is
part of the per-instance scorecard (`STRATEGIES.md` §7).

### Candidate original hypothesis (frozen pre-registered, untested)

**Regime-Gated Failed-Breakout Pullback.** Long only when price is above a
rising SMA(200) and volatility is not extreme. Detect a Donchian breakout that
fails and closes back inside the channel. Wait for a controlled pullback
(RSI(2) oversold, still above the trend filter, volatility contracting). Enter
at the next bar's open after recovery confirmation. ATR stop plus a fixed time
stop. No pyramiding. No trade when trend and volatility signals disagree.

The thesis is selective participation: deliberately refusing most T1/T4
signals rather than taking more of them. This is a hypothesis, not a
conclusion — it must be frozen in a P1b spec file before its ranking (P1c/P1d
result) is seen by anyone, including the model that wrote it.

Exit (P1 overall): P1a-P1d complete for the pre-registered candidate library;
P1e activation layer specced and tested; lesson "What is a backtest and how to
read one" plus a lesson on why ranking by raw P&L is wrong.

## P2 — Paper broker, risk engine, minimal alerts

Paper broker with cost/slippage models; risk engine per spec (I1-I13 tests, blind tests, mutation run); mode gate; SQLite state; outcome tracker; Telegram alert with Approve/Paper test/Reject (paper-only wiring first); kill switch (manual + automatic). A/R: Sol / Astra (+ Terra blind tests).
Exit: all invariants passing; kill-switch drill executed in paper.

## P3 — India Tier A end to end (paper) + dashboard

Live data adapter (free source), candle builder (live), market scheduler, ORB + breakout strategies live in paper, auto-paper shadow, Streamlit Home + India page + Paper ledger + Strategies pages, daily report. A/R: Sol (+UI) / Terra, Astra spot review.
Exit: a full week of unattended paper trading with logs and daily reports.

## P4 — Tier B scanner and Stocks page

Daily scanner, universe filters, shortlist, promotion/demotion, Stocks page (ideas with target/"reconsider" levels, Paper track), scanner backtest (shortlist forward outcomes). A/R: Terra / Sol.

## P5 — Crypto and US sleeves (paper)

CCXT and Alpaca adapters, market profiles, T1/T2/momentum instances, funding data, Usage/Accounts page v1 (balances read-only). A/R: Sol / Terra.

## P6 — Brain and News

News page (RSS/official feeds), LLM provider interface, budget guard, schema validation, shared context cache, Brain A/B in paper. A/R: Sol / Astra.

## P7 — Go-live readiness (India first)

Cloud VM with reserved static IP, broker whitelisting, secrets handling, reconciliation drills, audit by a Claude model (buy Pro/API briefly), `TESTING.md` §6 checklist, tiny live in **approval** mode. A/R: Sol / Astra + Claude audit; owner signs off.

## P8 — Expansion (each gated)

MCX commodities and NSE currencies; ML ranker (walk-forward, champion/challenger); options (defined-risk only, after dedicated learning); memecoin sleeve (paper-only until forward record justifies); gold/bond ETF filter.

---

## Rules for all phases

- A phase is done only when its exit criteria are met **and** its lesson exists **and** `STATUS.md` is updated.
- If a spec is missing or contradictory, write a handoff note (`needs-human` if it is an owner decision) instead of guessing.
- Never skip the promotion gates for strategies, even if a result looks great; great-looking results are the most suspicious.

## Open questions (P1 restructure — owner decision, do not guess)

- **Point-in-time universe source.** Which authorized source provides
  point-in-time Nifty 50 + Next 50 membership (including delisted symbols)?
  P1a cannot be marked done without one, or an explicit owner sign-off to
  proceed with a known survivorship-bias caveat.
- **Capital and per-trade risk assumptions.** What capital and per-trade risk
  % should the P1b/P1c candidate comparisons use, so every candidate is sized
  the same way and results are comparable?
- **Target holding horizon.** The data collected so far is daily, which
  implies daily swing trading as the default horizon for the candidate
  library. Confirm this is intended, or say which other horizon P1 should
  target instead.

No time estimate is given for the restructured P1 — the owner's original
Claude-Pro time-box applied to the P0 sprint, not to this multi-sub-phase
research program, and guessing a duration here would just be noise.
