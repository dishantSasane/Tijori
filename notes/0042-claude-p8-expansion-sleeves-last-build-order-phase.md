# 0042 — Claude: P8 Expansion (MCX/NSE-currency, ML ranker, memecoin gate, gold/bond ETFs); options deferred — PR #61

Status: implementation-complete, needs cross-model review and owner decisions.
**This is the last phase of the original `docs/BUILD_ORDER.md`.**

## What this covers

P8's line item: "MCX commodities and NSE currencies; ML ranker (walk-forward,
champion/challenger); options (defined-risk only, after dedicated learning);
memecoin sleeve (paper-only until forward record justifies); gold/bond ETF
filter."

Built on `claude/p8-expansion-sleeves`, based on `claude/p5-crypto-us-sleeves`
(PR #58), which is itself based on `claude/sleeve-allocation-and-adapters`
(PR #54). **PR #61** opened against that base (not `main` — same situation
P5 was in; see merge-order section below).

1. **MCX + NSE currency sleeves**: `strategies/instances.py` gained
   `mcx_instances()` / `nse_currency_instances()`, configuring the existing
   `t1_donchian`/`t4_rsi_pullback` rules against the fixed universes already
   built on PR #54 (`storage/mcx_universe.py`, `storage/nse_currency_
   universe.py`, `adapters/upstox_history.py` reused as-is). No new data
   adapter, no new strategy math. `market_profile.py` + `markets.example.yaml`
   gained an `nse_currency` profile (09:00-17:00 IST, differs from equity).
2. **Gold/bond ETF filter**: `GLD`/`BND` added to `US_TIER_A` — one line, as
   the task brief predicted. No new filter subsystem built.
3. **ML ranker** (`src/trading/research/ml_ranker.py`, NEW module):
   experimental, advisory-only walk-forward champion/challenger ranker.
   Deliberately scoped to rank candidates P1 has *already* pre-registered
   and scored — never touches raw candles, never searches for new
   candidates. A challenger must beat the champion's `expectancy` in 3
   consecutive walk-forward folds to take over. This was the highest-risk
   item in the phase (re-opening P1's overfitting trap was the explicit
   failure mode to avoid) — see ADR-0034 for the full reasoning.
4. **Memecoin sleeve**: `memecoin_instances()` (DOGE/USDT, SHIB/USDT, same
   CCXT-class exchange P5 already uses) + a hard code-level paper-only gate:
   `risk/engine.py`'s `ModeGate` gained `PAPER_ONLY_SLEEVES = frozenset
   ({"memecoin"})` and an optional `sleeve` kwarg on `route()` that forces
   `Route.PAPER` no matter the configured mode or human-approval action.
   Proven by a test that exercises every `Mode` x `human_action` combination.
5. **Options**: NOT implemented, on purpose. `docs/specs/OPTIONS_LEARNING_
   PLAN.md` (new) lists what the owner needs to learn (Greeks, margin,
   assignment, why "defined-risk only" doesn't mean "no other risk") before
   any options code gets written. Gated behind an owner go-ahead recorded as
   a future ADR in `docs/decisions.md` — **needs-human**, see below.

ADR-0034 in `docs/decisions.md` records all five sub-decisions in one place.
Lesson: `docs/learn/05-champion-challenger-and-why-options-wait.md`.

Tests: 139 pass (`PYTHONPATH=src python3 -m pytest tests/ -q`), `ruff
check`/`ruff format --check` clean, `mypy` clean on every module touched.
No real-order path, no secrets, no scraping (MCX/currency reuse the existing
Upstox client; memecoin reuses the existing CCXT-class exchange client).

## needs-human

1. **Options**: read `docs/specs/OPTIONS_LEARNING_PLAN.md`, do the
   reading/practice it lists, then record a go-ahead ADR in
   `docs/decisions.md` before any agent writes options code. Until then this
   sleeve stays spec-only.
2. **PR merge order across the whole P2-P8 sweep**: as of this note, **zero**
   PRs from this entire multi-phase build have been merged to `main`. Full
   list of open PRs and the dependency chain:

   | PR | Branch | Base it actually needs | Phase |
   |---|---|---|---|
   | #53 | `codex/p1-build` | `main` | P1 (strategy library — many other PRs build "T1/T4 reuse" assuming this lands) |
   | #54 | `claude/sleeve-allocation-and-adapters` | `main` | P2 test coverage + P8 data layer (MCX/NSE-currency/crypto/US adapters) |
   | #56 | `claude/p3-live-paper-dashboard` | `main` (independent of #54 chain) | P3 dashboard |
   | #57 | `claude/p4-scanner-stocks-page` | `main` (independent) | P4 scanner |
   | #58 | `claude/p5-crypto-us-sleeves` | #54 | P5 crypto/US sleeves |
   | #59 | `claude/p6-brain-news` | `main` (independent) | P6 Brain/News |
   | #60 | `claude/p7-go-live-readiness` | `main` (independent) | P7 go-live checklists |
   | **#61** | `claude/p8-expansion-sleeves` | #58 (→ #54) | **P8 — this note** |

   Suggested merge order (owner decision, this is a recommendation not a
   command): **#54 first** (nothing else depends on it being absent, and
   #58/#61 need it), then **#58**, then **#61** — that closes out the whole
   crypto/US/MCX/currency/memecoin chain in one pass. #53 should probably
   merge early too since several PRs' doc comments note they're working
   around its absence (T2/momentum deferred everywhere until it lands).
   #56/#57/#59/#60 are independent of this chain and can merge in any order,
   but dashboard duplication between #56 and #57 (`dashboard/_data.py`,
   flagged in note 0037) needs resolving by whichever merges second.
   Every PR needs its AGENTS.md §5 cross-model review before the owner
   merges anything — none have had that yet per the STATUS.md table.
3. **Memecoin/MCX/currency sizing**: flagging per AGENTS.md §5 that
   `risk/engine.py`'s `ModeGate` change and the new sleeve allocations are
   execution/risk-adjacent and need the cross-model review, not just a
   glance.

## For the next session (either agent)

- If you're Codex/the other model: PR #61's `ModeGate.PAPER_ONLY_SLEEVES`
  gate and the ML ranker's scope boundary (ADR-0034) are the two things most
  worth a careful adversarial read — one is new risk-path code, the other is
  explicitly trying not to reopen P1's overfitting hole.
- With this note, every line item in the original `docs/BUILD_ORDER.md`
  phases P0-P8 has at least an implementation PR open. None are merged. The
  single biggest lever for the owner right now is almost certainly:
  review and merge PRs in the order above, rather than starting new feature
  work — there is no new phase after P8 in the current BUILD_ORDER.

Agent: claude (sonnet-5)
