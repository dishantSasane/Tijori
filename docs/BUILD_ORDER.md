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

While owner inputs are pending, continue deterministic contracts, pure
algorithms, synthetic tests, and source-independent specs. Do not ingest a
source whose rights/schema are unresolved, freeze dates without a known
authorized data window, read the burned holdout, or report real-data strategy
rankings. Gather remaining owner decisions in a consolidated handoff after the
independent work is ready.

### P1a — Data foundation

| Deliverable | A/R | Notes |
|---|---|---|
| Tier A daily history in Parquet (candle store + validation) | Sol / Terra | already done for the 6-symbol representative set |
| Tier A intraday history in Parquet (1m and 5m) | Sol / Terra | Upstox V3 intraday history has a fixed provider floor of January 2022. Do not probe for earlier intraday history; it is unavailable through this provider. One-month maximum request span for 1–15m. Resumable loader and tests are implemented; sustained full-universe collection still pending. |
| Corporate-action adjustment, source adapter added; data/coverage gates open | Terra / Sol | Upstox documents an authenticated per-ISIN corporate-actions endpoint for dividends, bonuses, splits, and rights. A client and fixture tests now preserve the raw ratio/details without inferring ratio direction. A live probe was blocked by Cloudflare 403 (`browser_signature_banned`; response said do not retry), so no real event ledger was fetched or saved. The docs do not explicitly promise demerger coverage. Do not rebuild candles or treat an empty response as a complete ledger until authenticated responses and coverage are verified. Existing NSE parser is normalization-only; no NSE downloader exists. Position replay and runner screening remain incomplete. |
| Research universe: pure turnover selector; data source unimplemented | Terra / Sol | ADR-0026 selects top 50 (and separately top 100 for later Tier-B-adjacent research) by rolling 60-session median turnover, recomputed monthly, keyed on ISIN. The selector only accepts normalized inputs and has synthetic tests. Proposed NSE bhavcopy acquisition is prohibited by current source policy; no collector or scraper exists. Do not produce real snapshots or survivorship-free claims until a permitted source, schema, historical eligible-security coverage, and missing/no-trade semantics are verified. |
| Nifty 50 point-in-time manifest: validator only, benchmark-only | Terra / Sol | Membership models validate a supplied manifest; no NSE Indices press-release downloader or automated reconstruction exists. Do not automate collection from NSE Indices. The manifest remains unpopulated and incomplete; a benchmark constituent list alone does not calculate index returns. |
| Chronological split boundaries, written and frozen in config before any strategy runs | Sol / Terra | Contract in `specs/RESEARCH_SPLITS.md`; dates remain unset until authorized source/window and fresh unread holdout are available |

P1 candle scope includes **daily swing and intraday from the start**. Upstox
historical 1m and 5m data has a fixed floor of January 2022; earlier intraday
history is unavailable through this provider and must not be probed again.
Intervals 1–15m have a one-month maximum range per request. The 2026-11-15
probe found no different retention window for 1m versus 5m in the sampled
symbols. The current intraday loader uses month-bounded requests and a
conservative 0.91-second minimum interval, staying below the documented 2,000
requests per 30 minutes (and therefore also below 500 per minute and 50 per
second). Tokens are supplied at runtime and are never persisted. OAuth
auto-renewal remains out of scope until the live/paper trading phase.

Exit: corporate-action adjustment has real-event and synthetic known-answer tests; the pure rule-based
universe selector is implemented and tested; authorized, schema-verified
historical universe inputs and permitted, coverage-verified benchmark data are
available and ISIN-joined against the Upstox instrument master; split
boundaries exist in committed config with no strategy code reading the
holdout range. Source authorization and historical coverage are hard gates,
not implied by public download availability.

Progress note (2026-11-15): the pure daily/intraday split/bonus price-volume transform
and known-answer tests are in `trading.storage.corporate_actions`
and `tests/storage/test_corporate_actions.py`. The membership manifest
contract and validator in `trading.storage.membership` validate a supplied
benchmark manifest; they do not establish its source permission or
completeness. The owner selected the rule-based turnover universe and declined
an NSE Indices licence inquiry under ADR-0026. Source rights, bhavcopy schema,
historical eligible-security coverage, and completeness of the benchmark
notice archive remain unverified, so only synthetic selector validation may
proceed pending resolution. **Owner decision recorded:** research-comparison
sizing is 1% per-trade risk on a ₹1,00,000 placeholder capital (not real
trading capital, used only so candidates are sized identically). Still open:
Upstox's corporate-action basis has now been empirically checked for one
specific event: NESTLEIND 10:1 split on 2024-01-05. Upstox returned ₹1,355.80
on the prior session and ₹1,333.20 ex-date, a continuous series across the
split. Treat this split as already reflected by Upstox for these candles (case
a); do not apply the 10:1 transform a second time. Later corporate actions
may affect the absolute historical price scale, so do not infer the raw price
by dividing by ten. The real-event fixture/test checks continuity. Do not
generalize this one event to every action type or symbol.
The Upstox per-ISIN corporate-actions API is now the selected action-data
source; see `specs/DATA_SOURCES.md`. A request from this environment received
Cloudflare HTTP 403 `browser_signature_banned` with an instruction not to retry.
No live event data was acquired. Validate API access and history coverage before
using it. The API documentation does not explicitly include demergers, so those
and any unknown/missing action classes require manual reviewed records or a
different authorized source. Validate provider adjustment markers/basis for
other events, implement and independently verify position/share-count replay
across actions in both backtesters, and obtain a complete event ledger before
P1a exit.
The untouched holdout boundaries and holding-horizon confirmation also remain
open (see Open Questions).

Intraday history probe (2026-11-15): Upstox V3 returned 375 one-minute and 75
five-minute candles per full session for Nifty 50 and RELIANCE, INFY, TCS,
HDFCBANK, ICICIBANK on 2026-11-13, 2026-10-15, and 2026-05-15. Both intervals
returned zero rows on 2024-11-15. Nifty 50 returned history for 2022-01-03
through 2022-01-31 at both intervals and none for December 2021. The provider
documents minute availability since January 2022 and a one-month request cap
for 1–15 minute intervals; both 44-day probes were rejected with UDAPI1148.
Requests at the documented boundary were chunked by month. Published rate
limits for standard APIs (including historical candles) are 50/second,
500/minute, and 2,000/30 minutes; this low-rate probe did not trigger a 429.
The runtime token is daily and must be freshly injected by the operator or
future login flow; the loader deliberately has no `.env` fallback.

Progress note (2026-11-15, selector slice):
`trading.storage.research_universe.build_snapshot` and synthetic contract
tests implement the pure monthly turnover ranker. Real feed parsing and
collection remain blocked by the source gate above. The selector API and
provenance contract are specified in `specs/RESEARCH_UNIVERSE.md`.
The three-way split contract is in `specs/RESEARCH_SPLITS.md`; it deliberately
contains no boundaries because the available 2016–2026 window is burned and
source/coverage gates remain unresolved.

### P1b — Candidate library (pre-registered)

The P1-specific catalogs in `specs/P1_CANDIDATES.md` freeze daily-swing and
intraday families and limit each family to three total variants. The broad
sweep ranges in `STRATEGIES.md` remain general guidance and do not authorize a
larger P1 search.

| Deliverable | A/R | Notes |
|---|---|---|
| Fixed candidate family spec, declared before any ranking | Sol / Terra | daily families plus a parallel pre-registered intraday family catalog from the start; ORB requires its own exact intraday rules and is not deferred to a later phase |
| Declared parameter grid per candidate, with a hard cap on variations | Sol / Terra | state the cap explicitly in the spec file; no free-form parameter sweeps |
| Versioned, deterministic spec per candidate | Sol / Terra | same immutable-version discipline as `STRATEGIES.md` §6 |

Exit: every executable candidate and parameter grid exists in a spec file
before any backtest runs; the cap on variations is a number written down, not
an intention. The daily catalog is drafted, but its RPF hypothesis remains
non-executable until its complete rules are specified. A separate intraday
catalog with exact ORB rules and parameter variants remains to be written.
Owner confirmation of the promotion horizon and viability thresholds is still
required before result generation.

### P1c — Evaluation harness and experiment registry

| Deliverable | A/R | Notes |
|---|---|---|
| Ranking metrics: net return after costs, expectancy, max drawdown, Calmar/Sharpe/Sortino, turnover and cost sensitivity, % profitable instruments, % profitable time windows, block-bootstrap confidence intervals, performance vs. buy-and-hold | Sol / Terra | raw rupee P&L is never a ranking key |
| Multiple-testing correction / reality-check method | Sol / Terra | name the method explicitly (e.g. White's Reality Check, SPA test, or a Bonferroni-style correction on the pre-registered candidate count); do not skip this because P1b capped variations — the cap bounds it, it doesn't replace it |
| Experiment registry | Sol / Terra | every candidate and variant attempted, including failures, logged with run ID, spec version, split used, and result, so the eventual winner can be discounted for the number of attempts behind it |

Exit: the registry has one row per attempted run (pass or fail); the ranking
report states which correction method was applied and shows results both with
and without it. The append-only registry, deterministic moving-block bootstrap
and Bonferroni helpers now exist, but no ranking report can be produced until
P1a's source/split gates and the portfolio aggregation contract are settled.

### P1d — Holdout evaluation

| Deliverable | A/R | Notes |
|---|---|---|
| Shortlist frozen before the holdout is read | Sol / Terra | frozen means: no further parameter changes once this step starts |
| One-shot evaluation on the untouched holdout from P1a | Terra / Sol | |
| Explicit, pre-written rejection rule | Sol / Terra | a candidate is rejected if its advantage disappears after costs, or does not hold across regimes; write the rule before seeing the holdout result so it cannot be renegotiated after |

Exit: holdout is evaluated exactly once per shortlist candidate; rejections
and survivors are both recorded with the rejection rule applied, not a
post-hoc judgment call. A durable one-shot evaluator now records consumption
before evaluation; actual use waits for a fresh unread holdout and frozen
shortlist/rejection/metric hashes.

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
part of the per-instance scorecard (`STRATEGIES.md` §7). The fixed two-axis
regime calculation and router skeleton are implemented and synthetically
tested; promotion thresholds, empirical validation and production scorecard
integration remain gated on P1a-P1d.

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

- **Research-universe data source remains unimplemented.** ADR-0026 selected
  the turnover-ranking rule, but no permitted turnover history has been
  acquired. The selector is pure and tested only with synthetic normalized
  rows. Automated NSE/NSE Indices collection is prohibited by the current
  project source policy. The Nifty membership package is a validator only; no
  press-release scraper or populated manifest exists.
- ~~Capital and per-trade risk assumptions~~ — **resolved.** 1% per-trade risk
  on a ₹1,00,000 placeholder capital for P1b/P1c comparisons; not real trading
  capital, used only so every candidate is sized identically.
- **Target holding horizon.** The data collected so far is daily, which
  implies daily swing trading as the default horizon for the candidate
  library. Confirm this is intended, or say which other horizon P1 should
  target instead. — **still open.**

No time estimate is given for the restructured P1 — the owner's original
Claude-Pro time-box applied to the P0 sprint, not to this multi-sub-phase
research program, and guessing a duration here would just be noise.
