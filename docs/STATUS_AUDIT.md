# Status Audit — 2026-11-16

Produced per the owner's 4-stage audit request. Covers Stage 3 (phase-by-phase
completion audit) and Stage 4 (owner-decision inventory). Stages 1 and 2
(PR review and merge) were reported in chat; this document is a point-in-time
snapshot, not a live PR dashboard. At publication, of 8 open PRs, only
**#53** was both CI-green and independently (cross-model) reviewed, and it has
been merged to `main`. Later updates may change review/CI status and must be
checked on the pull requests themselves before making a merge decision.

Phase list below is the real, current one from `docs/BUILD_ORDER.md` as of
this audit: **P0 through P8**, with P1 split into **P1a–P1e**. This is not a
guess — it is what BUILD_ORDER.md itself defines today; no phases have been
renumbered since.

---

## Stage 3 — Phase-by-phase completion audit

Status key: **Done** (verified against real tests/data, merged to main) /
**Partial** (code exists, merged or PR-ready, but a real gate is still open —
synthetic data, deferred integration, or unmerged) / **Not started**.

### P0 — Foundation sprint
**Done.** Contracts, adapter Protocols + fakes, risk engine spec, test specs,
strategy spec, lessons 00-03, and the Codex handoff all merged to `main`
early in the project. No open items.

### P1 — Data layer, strategy discovery, regime-gated activation
**Partial**, phase-wide. Just merged (#53) to `main`, but "merged" ≠ "ready
to run on real decisions" — several hard gates remain open:

- **P1a (data foundation): Partial.** Five-symbol (RELIANCE/INFY/TCS/
  HDFCBANK/ICICIBANK) daily history for 2010–2015 is archived and reconciled
  (1,482 common sessions; 10 RELIANCE-only dates explained, 9 as weekends, 1
  as the 2011-10-26 Diwali special session). Intraday (1m/5m) loader is
  resilient and tested but **sustained full-universe collection has not run**.
  Corporate-action adjustment: only one real event (NESTLEIND 10:1 split) has
  been empirically verified against Upstox's basis; the five pilot symbols'
  archived action responses contain **dividends only**, so action completeness
  for the pilot window is **not established** — demergers/rights/unknown
  events are explicitly unhandled pending a manual reviewed ledger. The
  Top-50 turnover-based research universe and Nifty 50 point-in-time
  membership are implemented with **synthetic tests only** — no real data has
  flowed through either. Chronological split boundaries (dev/validation/
  holdout) remain **unset** — the 2016–2026 window is burned (ADR-0024) and a
  fresh authorized window has not been obtained.
- **P1b (candidate library): Partial, in the sense that is honestly scoped.**
  15 variants (12 daily + 3 intraday) are frozen in spec with a stated,
  written cap. T3 and the RPF idea are deliberately deferred before any
  result inspection — this is correct practice, not a gap. No backtest has
  run against these on real/pilot data pending P1a gates.
  Pre-registration itself is complete.
- **P1c (evaluation harness): Partial.** Ranking metrics, block-bootstrap,
  Bonferroni-style correction, and an append-only experiment registry are
  implemented and independently verified (per note in `STATUS.md`/commit
  history) with synthetic data. **No real ranking report has ever been
  produced** — explicitly blocked on P1a's source/split gates.
- **P1d (holdout evaluation): Partial.** A durable one-shot evaluator exists
  with minted-token authorization and reuse/forgery protection (hardened in
  recent commits, e.g. `426471a`, `b0a6630`). It has **never been exercised
  against a real holdout** — there is no fresh unread holdout to evaluate
  against yet.
- **P1e (regime-gated activation): Partial.** Rule spec, router skeleton,
  overlap/abstention tests, and activation-frequency reporting exist and are
  synthetically tested. Empirical validation and production scorecard
  integration are gated on P1a–P1d completing on real data, which they have
  not.

**Net: P1 is implementation-complete and self-consistent, but zero rows of
real strategy ranking or holdout results exist yet.** Treat any claim of
"P1 done" as referring to pipeline/methodology readiness only.

### P2 — Paper broker, risk engine, minimal alerts
**Done, merged to `main`** (PRs #50, #52, commit `39a50ea` + follow-ups).
Risk engine, paper broker, Telegram alert wiring, mode gate, kill switch are
in `src/trading/risk/`. Decision: this phase was implemented out of the
original role-split order by the owner's direct instruction (ADR-0028).
No live-broker code exists (correct — P2 is paper-only by design).

### P3 — India Tier A end-to-end (paper) + dashboard
**Partial.** Daily report + read-only Streamlit dashboard (Home/India/Paper
ledger/Strategies) are built on `claude/p3-live-paper-dashboard` (PR #56,
CI green) but **not merged** and has had **no independent review**. The
live NSE data adapter and ORB/breakout live-paper wiring are explicitly
**blocked on an owner decision** (no live data source chosen yet) — this is
not an oversight, it's a stated gate.

### P4 — Tier B scanner and Stocks page
**Partial.** Daily scanner, shortlist persistence, no-look-ahead scanner
backtest, and a read-only Stocks page are built on PR #57 (CI green, **no
independent review**). Ranking is explicitly a **placeholder momentum score**
pending P1's real strategy library landing — documented as a placeholder in
the PR, not hidden. A file-duplication issue (`dashboard/_data.py` also
exists on the unmerged #56) needs resolving whichever of #56/#57 merges
second.

### P5 — Crypto and US sleeves (paper)
**Partial.** Data adapters are done; market profiles, T1/T4 strategy
instances, and an Accounts page v1 are on PR #58. The branch is stacked on
PR #54, not `main`; check its current CI and review state before merging.
T2/momentum deferred (needs P1's unmerged strategy library). Funding data is
deferred (spot-only sleeve, nothing consumes it). Live-paper execution wiring
(candle feed → signal → risk → broker) is **not built yet**. Open owner
decision: which crypto exchange/account for paper trading — data adapter
picked Binance, but order routing is unsettled.

### P6 — Brain and News
**Partial.** Real RSS news feed, Anthropic Brain provider (lazy-imported),
budget guard (fails closed, sums spend from the existing audit log), strict
schema validation on LLM output, context cache, and an A/B harness are built
on PR #59 (CI green, **no independent review** — flagged mandatory per
AGENTS.md §4.6/§4.8 since this is LLM-advisory/risk-adjacent code). **No
production call site exists yet** — there is no live paper signal-generation
loop for the Brain to advise on. A Usage dashboard tile is deferred.

### P7 — Go-live readiness (India first)
**Partial.** Go-live checklist, live-audit checklist, and a reconciliation
module (compares local vs. broker positions, engages kill switch on mismatch)
are built on PR #60 (CI green, **no independent review**, mandatory per
AGENTS.md §5 since execution-adjacent). Tested only against a fake broker —
correct, since AGENTS.md §4.4 forbids real-broker tests. No code places a
real order or needs a real secret; going live remains explicitly a manual
owner action behind this checklist plus a separate audit pass. Open owner
decisions: cloud VM provider (ADR-0030, referenced but not found committed to
`decisions.md` on `main` as of this audit — likely lives only on an unmerged
branch) and which broker for the first live sleeve.

### P8 — Expansion (each gated)
**Partial, and this is the last phase in BUILD_ORDER.md — confirmed, not
assumed; there is no P9+.** MCX/NSE-currency strategy instances, GLD/BND
added to US Tier A, an experimental advisory-only walk-forward ML ranker
(scoped to never search raw candles, only re-rank P1's pre-registered
candidates), and a memecoin sleeve with a hard code-level paper-only gate
(`ModeGate.PAPER_ONLY_SLEEVES`, tested across every Mode × human-action
combination) are built on PR #61, stacked on PR #58 and then #54. **Options
trading code was
deliberately NOT written** — gated behind `docs/specs/OPTIONS_LEARNING_
PLAN.md` and a future owner-authored ADR, exactly per BUILD_ORDER's "after
dedicated learning" instruction. This is correct scoping, not a gap.

---

## Stage 4 — Owner-decision inventory

Every item below was explicitly deferred to the owner somewhere in the repo
(code comments, specs, ADRs, or handoff notes). None have been decided for
you below — this is the compiled list only.

| # | Decision | Current default/interim behavior |
|---|---|---|
| 1 | **Starting capital per sleeve** (paper and live) — `MASTER_PLAN.md` §13.1 | Research/P1 comparisons use a placeholder ₹1,00,000 at 1% per-trade risk (ADR-0026) — explicitly *not* real trading capital, used only so candidates are sized identically. No real sleeve capital has been set. |
| 2 | **Which broker/source for free Indian market data** (Angel One SmartAPI, Fyers, vs. paying ~₹500/mo for Kite Connect data) — `MASTER_PLAN.md` §13.2 | Upstox is the chosen P1 *historical* source (ADR-0023); no live-data broker has been chosen, which is why P3's live NSE adapter is blocked. |
| 3 | **Order-routing broker for India** (Zerodha Kite Connect Personal assumed) and **US route** (Alpaca paper assumed, LRS/IBKR later) — `MASTER_PLAN.md` §13.3 | Assumptions only, not confirmed. No order-routing code exists for either yet (P2/P3 are paper-only against fakes). |
| 4 | **Crypto exchange/account for paper trading + legal/tax approach** — `MASTER_PLAN.md` §13.4, handoff note 0038 | Binance picked for the *data* adapter only; order routing for crypto paper trading is unsettled. |
| 5 | **Cloud VM provider and static-IP plan** (Oracle free tier / student credits / cheap VPS) — `MASTER_PLAN.md` §13.5, referenced as ADR-0030 in handoff notes | Not decided. P7's go-live checklist lists this as a required step but no infra exists. Research/paper work runs on the laptop, which is fine for now — the static-IP rule only binds real India orders. |
| 6 | **Repo name / GitHub owner / CODEOWNERS for critical folders** — `MASTER_PLAN.md` §13.6 | Repo exists as `dishantSasane/Tijori`; no CODEOWNERS file was found protecting `risk`/`execution`/`backtest`/`brokers` paths, despite AGENTS.md §5 requiring cross-model review on exactly those paths. Right now that review requirement is enforced by agent discipline/handoff notes only, not by branch protection. |
| 7 | **Final sleeve allocations and risk limits** — `MASTER_PLAN.md` §13.7 | `config/risk.example.yaml` values are proposals only, not confirmed limits. |
| 8 | **Corporate-action ledger/source authorization** for the five-symbol pilot windows (demergers, unknown-class events, volume basis) — handoff "Blockers" section | Fail-closed: the P1a screening module reports in-window unhandled actions and excludes affected symbols rather than guessing a factor. No real ranking can run until this is resolved — this is the #1 blocker on `STATUS.md`'s "Next 3 actions." |
| 9 | **A fresh, unread, authorized chronological holdout/split** — handoff "Blockers" section, ADR-0024 | 2016–2026 is burned and may not be reused. No split boundaries are set; P1d's evaluator cannot be exercised for real until this exists. |
| 10 | **Forward-paper promotion policy** (daily vs. intraday observation duration, sample size, sizing) — handoff "Next 3 actions" #3 | Distinct from P1d's already-fixed backtest rejection rule. Not yet frozen; nothing currently depends on it being decided, but nothing can promote past paper without it either. |
| 11 | **Options sleeve go-ahead** — `docs/specs/OPTIONS_LEARNING_PLAN.md`, handoff note 0042 | Hard gate: no options code may be written until the owner completes the learning plan's reading and records a go-ahead ADR in `decisions.md`. Currently fully blocked, by design. |
| 12 | **Anthropic model + current per-token INR pricing + daily/monthly Brain budget cap** — handoff note 0039 | `BudgetGuard` exists and fails closed (blocks the call if the guard can't confirm budget), but the actual cap value and model/pricing to plug in haven't been confirmed. `BRAIN_ENABLED` should stay `false` until this is set. |
| 13 | **PR merge order across the whole P2–P8 sweep** — handoff note 0042 | Addressed in this audit's Stage 1/2: only #53 qualified for merge and has been merged. The rest need independent review (see Stage 1 summary) before any further merge decision is made. |
| 14 | **Smaller live universe or alternate data arrangement** if the Top-50 broad universe can't be sourced — `docs/specs/DATA_SOURCES.md:204` | The five-symbol pilot is the current interim scope; it is explicitly flagged as not a survivorship-free or India-wide claim. |
| 15 | **T4/T6 exit-rule ambiguity** flagged in `docs/specs/STRATEGY_SPEC.md:152` as needing a `needs-human` decision rather than a silent guess | Unresolved as of this audit; check the current `STRATEGY_SPEC.md` text for the exact ambiguity before anyone implements against it. |
| 16 | **Memecoin data source** (public DEX API) terms-of-service check — `docs/MARKETS.md:60` | TBD; sleeve is paper-only and capped at an illustrative 5% regardless, so this doesn't block anything else yet. |
| 17 | **MCX session calendar** machine-readability — `docs/specs/CANDLE_BUILDER_AND_SCHEDULER_SPEC.md:118,211` | Flagged `needs-human` if no free machine-readable MCX calendar exists; not confirmed either way in this audit. |

Note: several of these (#5, #11, #12) were already being tracked as
`needs-human` in the live `handoffs` branch `STATUS.md` — this document
consolidates them with the items that were only in spec/doc comments, so they
don't have to be found twice.
