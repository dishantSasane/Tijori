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
| Research universe: rule-based, computed from free NSE bhavcopy | Terra / Sol | **primary universe — resolved, no paid licence.** Top 50 (and separately top 100 for Tier B-adjacent research) by rolling 60-day median turnover, recomputed monthly, keyed on ISIN (not symbol — symbols get renamed/reused, ISINs don't). This is survivorship-free by construction: a stock that was liquid in year N and delisted in year N+2 appears in year N's universe and vanishes after, exactly as it should, with no manifest and no vendor needed. Data: NSE's free bhavcopy archives (`sec_bhavdata_full` daily files; evaluate the maintained `nse-archives` package's licence/maintenance before adopting it, otherwise write a small fetcher) |
| Nifty 50 point-in-time manifest: reconstructed, benchmark-only | Terra / Sol | Not the research universe — only used so a scorecard can honestly say "vs. Nifty 50 as of 2021-06-30." Reconstruct by anchoring on today's known membership and walking NSE Indices' own public, dated replacement press releases (`niftyindices.com/Press_Release/ind_prsDDMMYYYY.pdf`) backward in time, one replacement at a time. Store as a dated table with the press-release URL cited per row, so every row is auditable. Cross-check against Wikipedia's replacements-since-2005 table, but never treat Wikipedia as the source; flag (don't silently resolve) any disagreement between the two |
| Chronological split boundaries, written and frozen in config before any strategy runs | Sol / Terra | development period, validation period, untouched holdout; dates committed to config and never read until P1d |

Exit: corporate-action adjustment has known-answer tests; the rule-based
universe and the reconstructed Nifty 50 benchmark manifest are both built and
ISIN-joined against the Upstox instrument master; split boundaries exist in a
committed config file with no strategy code reading the holdout range.

Progress note (2026-11-15): the pure daily split/bonus price-volume transform
and synthetic known-answer tests are in `trading.storage.corporate_actions`
and `tests/storage/test_corporate_actions.py`. The membership manifest
contract and validator in `trading.storage.membership` were built against the
"authorized vendor" design; they are being repointed at the rule-based
universe (primary) and the reconstructed press-release manifest (benchmark
only) instead — see ADR-0026, which supersedes ADR-0025's "pay for a licence"
branch. **Owner decisions recorded:** no NSE Indices licence purchase, no
vendor email; research-comparison sizing is 1% per-trade risk on a ₹1,00,000
placeholder capital (not real trading capital, used only so candidates are
sized identically). Still open: Upstox's raw/adjusted price basis
(undocumented — verify empirically against a known corporate action in the
existing 6-symbol sample, e.g. Infosys's 2018 bonus issue, before trusting any
adjusted candle), both backtesters modelling share-count changes for
positions crossing an event, the untouched holdout boundaries, and the
holding-horizon confirmation (see Open Questions).

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

## Crypto coverage (data ecosystem build, 2026-11-15)

Data source: Binance public spot REST (`/api/v3/klines`), no API key, no SDK
-- same stdlib-`urllib` style as `adapters/upstox_history.py`. Verified
directly against `api.binance.com/api/v3/exchangeInfo` and the public REST
docs on 2026-11-15:

- **History depth:** no stated cutoff; candles are available back to each
  symbol's spot-listing date (most pairs: sometime after Binance's 2017
  launch). Free, no tier gate.
- **Intraday window:** all of M1/M5/M15/H1 (plus daily) are available for the
  full listed history, not just a recent rolling window -- unlike Upstox's
  India intraday limit, Binance does not truncate intraday history.
- **Pagination cap:** 1,000 candles per `/api/v3/klines` call
  (`MAX_CANDLES_PER_REQUEST` in `adapters/binance_history.py`).
- **Rate limit:** 6,000 request-weight per IP per minute; `klines` costs
  weight 2, so up to 3,000 calls/minute is technically allowed. The
  historical loader (`storage/crypto_loader.py`) self-throttles to 60
  requests/minute (`REQUESTS_PER_MINUTE_BUDGET`) -- backfilling is not
  latency-sensitive and this stays far clear of a 429.
- **Integrity:** Binance delists/rebrands tokens with no split-style price
  adjustment needed, but a delisted symbol must stop being treated as
  tradeable, and a gap in daily candles with no matching delist/rebrand
  event must fail closed rather than be silently interpolated. Implemented
  in `storage/crypto_integrity.py` (`ListingRegistry`), tested with known
  answers in `tests/storage/test_crypto_integrity.py`.
- **Universe:** general crypto sleeve = BTC/ETH always-in + top 20 by 24h
  quote volume above a $5M floor; memecoin sleeve = tagged tokens with a
  $1M floor and a minimum 30-day listing age. Both are pure, mechanical
  functions of a liquidity snapshot (`storage/crypto_universe.py`), never a
  hand-picked list, so re-running against a historical snapshot reproduces
  the same point-in-time universe.
- **Owner decision still open:** which exchange to actually trade on
  (legality/tax/compliance for an Indian resident) is unchanged by this data
  work -- Binance here is a free data source, not an execution-venue choice.

---

## Rules for all phases

- A phase is done only when its exit criteria are met **and** its lesson exists **and** `STATUS.md` is updated.
- If a spec is missing or contradictory, write a handoff note (`needs-human` if it is an owner decision) instead of guessing.
- Never skip the promotion gates for strategies, even if a result looks great; great-looking results are the most suspicious.

## Open questions (P1 restructure — owner decision, do not guess)

- ~~Point-in-time universe source~~ — **resolved, see ADR-0026.** Rule-based
  turnover universe (primary, survivorship-free by construction) plus a
  reconstructed Nifty 50 manifest from public NSE Indices press releases
  (benchmark-only). No paid licence, no vendor email.
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

## US equities coverage (data ecosystem, phase 2 — verified 2026-11-15)

Live-verified against docs.alpaca.markets (not just the dated note in
`docs/MARKETS.md`), via the free "Basic" data plan bundled with any Alpaca
paper/live account (IEX feed):

- **Key required even though free.** Unlike Binance's anonymous REST, Alpaca's
  bars endpoint rejects every request without an `APCA-API-KEY-ID` /
  `APCA-API-SECRET-KEY` pair. Getting the pair costs nothing (sign up for a
  paper account) but it is not keyless the way Binance is.
- **Raw vs. adjusted — corrects the earlier dated note.** The bars endpoint's
  own default is `adjustment=raw` (unadjusted). Split/dividend-adjusted bars
  only come back if the caller explicitly passes `adjustment=all` (or
  `split`/`dividend`). `src/trading/adapters/alpaca_history.py` defaults to
  `"raw"` to match Alpaca's own default and keep the basis explicit at the
  call site.
- **Corporate actions are free.** Alpaca's `/v1/corporate-actions` endpoint
  (splits, dividends, mergers, spin-offs, etc.) is included on the free plan
  with no paid-tier gate, per its own docs. `src/trading/storage/
  us_equity_corporate_actions.py` is an independent splits+dividends
  adjustment layer built from that feed, for cross-checking Alpaca's own
  `adjustment=all` or adjusting bars fetched raw. No other free, complete US
  corporate-action source was found during this check — if Alpaca's feed is
  ever unavailable there is currently no verified free fallback; flag to the
  owner before relying on anything else.
- **History depth:** 7+ years of IEX-feed history (free plan pricing table).
- **Rate limit:** 200 API requests/minute (free "Basic" plan). The loader
  (`src/trading/storage/us_equity_loader.py`) self-throttles to 150/min.
- **Universe:** rule-based top-N-by-dollar-volume trading universe
  (`src/trading/storage/us_equity_universe.py`, survivorship-safe by
  construction, same shape as the crypto sleeve) plus a separate S&P 500
  membership manifest sourced from Wikipedia's "List of S&P 500 companies"
  changes table (free, community-maintained — not an official S&P feed) for
  benchmarking only, never for universe selection.
- Status: adapter, independent adjustment layer, universe rule, benchmark
  manifest shape, and loader are implemented with known-answer/fake-requester
  tests (no test touches Alpaca's real API). "US equities" data-ecosystem
  checklist item: done.

## NSE currencies coverage (verified, not assumed)

Checked empirically against Upstox's public API docs and NSE's currency
derivatives contract specifications before building anything, per the owner's
instruction not to assume "simpler than equities."

- **Adapter:** genuinely no new HTTP client needed. `UpstoxHistoryClient`
  (`src/trading/adapters/upstox_history.py`) is instrument-key-agnostic — it
  URL-encodes whatever key it's given and hits the same `/v3/historical-candle`
  path regardless of segment. Currency derivatives live in Upstox's `CDS`
  exchange / `CD` segment (instrument keys shaped `CDS_FO|<token>`), distinct
  from equities' `NSE_EQ`, but that's just a different string, not a different
  client. Proven by `tests/storage/test_nse_currency_universe.py::
  test_existing_upstox_client_accepts_a_currency_instrument_key`, which feeds
  a `CDS_FO|USDINR...` key through the unmodified client. Did **not** edit
  `upstox_history.py` itself (shared with Codex's India equity work) — no
  edit was needed.
- **Corporate actions / integrity:** no equivalent problem. FX futures have
  no splits or dividends, so no adjustment layer is needed (unlike India
  equities' `corporate_actions.py`).
- **Contract roll / expiry:** also simpler than first feared. Currency
  futures expire monthly like MCX, but this phase makes **no attempt to
  stitch a continuous series** — each expiry is queried as its own distinct
  `instrument_key`. Because nothing is being glued together, there is no
  "fake price jump at rollover" bug to guard against here. If a continuous
  series is ever wanted (e.g. for a strategy that needs one unbroken price
  line), build that roll-adjustment logic once for MCX (phase 4) and reuse
  it here rather than duplicating it — flagged for whoever builds phase 4.
- **Universe:** fixed, tiny, hand-enumerated set — USDINR, EURINR, GBPINR,
  JPYINR (`src/trading/storage/nse_currency_universe.py`). No liquidity-rule
  universe built; AGENTS.md §10 keeps this sleeve deliberately small.
- **Session hours:** confirmed NSE currency derivatives trade 09:00-17:00
  IST, Monday-Friday — different from NSE equity's 09:15-15:30. This
  resolves the "verify per contract" note docs/MARKETS.md previously carried
  as unverified.
- **Net verdict:** NSE currencies *is* simpler than equities overall (no
  adjustment layer, tiny fixed universe, reused adapter) but for a different
  reason than assumed — the simplification comes from skipping continuous-
  series stitching entirely, not from the segment being easy. If a continuous
  series is ever required, that assumption needs revisiting.
- Status: "NSE currencies" data-ecosystem checklist item: done.
