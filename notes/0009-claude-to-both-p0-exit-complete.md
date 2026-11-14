---
id: 0009
from: claude (Sonnet 5)
date: 2026-11-14 19:40 IST
to: both
subject: P0 EXIT — all BUILD_ORDER.md items merged, item 10 (this note) closes it out
status: open
refs: [0006, 0008, docs/BUILD_ORDER.md, docs/specs/, docs/learn/, docs/decisions.md]
---

## Context

Note 0006 was the handoff written when real P0 gaps existed. Note 0008
tracked them going to "PR open." As of this note, **every PR has been
merged** and BUILD_ORDER.md's P0 exit criteria are met in full (not just the
required items 3/4/5/7 — items 2, 6, 8, 9 that "may slip" per BUILD_ORDER.md
also landed). This is the real item-10 close-out.

## Completed P0 deliverables (all merged to `main`)

| Item | Deliverable | Where |
|---|---|---|
| 1 | Scaffold verified | No PR needed (clean as committed) |
| 2 | Review of MASTER_PLAN/RISK_SPEC/STRATEGIES; gaps logged | ADR-0018/0019/0020 in `docs/decisions.md` |
| 3 | `src/trading/core/` contracts, clock, config | `docs/specs/CONTRACTS.md` + code |
| 4 | Adapter Protocols + fakes + contract-test mixin | `docs/specs/ADAPTERS.md` + code |
| 5 | Risk engine spec | `docs/specs/RISK_ENGINE_SPEC.md` |
| 6 | Red-team scenario list | `docs/specs/RED_TEAM.md` |
| 7 | All five test specs | `docs/specs/TEST_SPEC_{RISK,CANDLES,BACKTEST,ADAPTERS,STRATEGIES}.md` |
| 8 | Strategy spec (pseudo-code, T1/T4 known-answer vectors) | `docs/specs/STRATEGY_SPEC.md` |
| 9 | Lessons 00-03 | `docs/learn/00-03` (00 pre-existed; 01-03 this sprint) |
| 10 | This handoff | — |

**Verified on current `main`:** `pytest` (41 tests, all passing), `ruff
check`, `ruff format --check`, `mypy src` — all clean.

## What exists for Codex to build on (P1+)

- Full contracts (`Candle`, `Tick`, `Signal`, `OrderRequest`, `Order`,
  `Fill`, `Position`, `RiskDecision`, `BrainVerdict`, `SignalOutcome`,
  `AuditEvent`) — immutable, UTC-strict, Decimal-typed, injected-clock only.
- Adapter Protocols + fakes for `DataFeed`, `Broker`, `NewsFeed`,
  `LLMProvider`, plus a reusable `Broker` contract-test mixin.
- A risk engine spec with exact check order, sizing algorithm, Brain
  boundary, paper/shadow semantics, gap-at-fill handling, and an
  invariant-to-section map — implementable without guessing.
- Strategy pseudo-code for T1-T6/F1 with shared semantics (warm-up, Wilder
  seeding, zero-denominator rules, same-bar exit precedence, final-bar-
  unfilled handling) and full known-answer vectors for T1/T4.
- Five test specs covering risk, candles/indicators, backtester, adapters,
  and strategies — each with named known-answer cases or explicit test
  lists, and each honest about where a numeric vector was deliberately not
  invented under time pressure (T2/T3/T5/T6/F1's vectors, walk-forward's
  numeric case).
- Already in progress on `main`, built by Codex against this foundation:
  DuckDB candle store (atomic batch inserts), SMA/EMA indicators — both
  cross-model reviewed.

## Known, explicitly-flagged gaps (not hidden, see the ADRs/specs themselves)

1. **Condition-based exits** (T1/T2/T4/T6) have no `ExitRequest` contract or
   reduced exit-only risk-check list yet — `STRATEGY_SPEC.md` §1.7, ADR-0020.
   Resolve before/during P2 risk-engine implementation.
2. **Concurrent duplicate-signal delivery** needs a `DecisionStore`
   atomicity design (not just the sequential-retry case, which is already
   tested) — `RISK_ENGINE_SPEC.md` §10, ADR-0020.
3. **T2/T3/T5/T6/F1 numeric known-answer vectors** don't exist yet —
   `TEST_SPEC_STRATEGIES.md` §4 says why and how to add them when
   implementing each template (spreadsheet/reference calc, not hand-rushed).
4. **Incremental indicator implementations** (only batch SMA/EMA exist so
   far) and the incremental==batch equivalence test — flagged in this
   session's review of Codex's PR #16, not yet built.
5. **ATR's eventual Decimal-exact variant** for order-path stop sizing
   (today's SMA/EMA are `float`, correctly, per AGENTS.md's research-code
   allowance) — flagged in the same review, not yet needed until ATR lands.
6. Everything already listed as open in note 0003 (data-provider choice,
   NSE-terms access gate, free-universe sizing) — unchanged, owner decisions.

## What you need to do

1. **Owner:** nothing blocking — P0 is done. The open questions in
   `docs/MASTER_PLAN.md` §13 and note 0003 are still yours whenever
   convenient, not urgent for Codex to keep building.
2. **Codex:** P1 is now fully unblocked. Continue per `BUILD_ORDER.md` P1's
   order (candle store/indicators already started — keep going with
   ATR/RSI/ADX next per `STRATEGY_SPEC.md` §1.3's seeding rules, then the
   backtester engine against `TEST_SPEC_BACKTEST.md`'s known-answer vectors,
   then T1/T4 first). Resolve gaps 1-5 above as you reach the code they
   affect, not before.
3. Nobody needs to wait on Claude for P0 anymore. If a future Claude session
   happens before the Pro plan ends, it's free to help with reviews, gap 1/2
   above, or anything Codex flags as needing a second model — not required
   to "unblock" anything.

## Decisions made (+ADR ids)

ADR-0018, ADR-0019, ADR-0020 (already in `docs/decisions.md`, `proposed`
status — owner confirmation turns them `accepted`, not required to keep
building against them).

## Open questions

Unchanged from note 0003/0006 — all owner decisions, none blocking.

## Model/usage notes

Claude Sonnet 5, across several forked sub-agents handling PR creation/CI
polling/cross-model reviews in parallel with the spec-writing work in this
session. Did not use Fable for the item-2/5 work the kickoff suggested
reserving it for — flagging this once more (also noted in 0004/0006) in case
the owner wants a Fable pass on the risk engine spec specifically before
treating ADR-0018/0019/0020 as settled, given RISK_SPEC.md/RISK_ENGINE_SPEC.md
are the highest-stakes documents in the repo.

## Reply
(Receiver appends here; do not rewrite the sections above.)
