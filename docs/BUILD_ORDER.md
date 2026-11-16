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

**First-pass scope decision (2026-11-15): bounded five-symbol pilot.** The
first P1 pass uses RELIANCE, INFY, TCS, HDFCBANK and ICICIBANK as a fixed
universe to validate the data and evaluation pipeline quickly. This sample
has survivorship and concentration bias. Its results are methodology/pipeline
validation and exploratory evidence for these five instruments only; they do
not establish an India-wide or survivorship-free strategy edge. The original
Top-50 point-in-time universe remains a tracked full-universe follow-up, not
silently considered complete. This scope decision does not waive per-symbol
candle, action, calendar, split, or evaluation gates.

| Deliverable | A/R | Notes |
|---|---|---|
| Tier A daily history in Parquet (candle store + validation) | Sol / Terra | Existing six-symbol history is exploratory only. Five pilot symbols' raw Upstox daily responses for 2010-01-01 through 2015-12-31 are archived locally (1,482 candles each except RELIANCE at 1,492); their common-session/calendar reconciliation, provider adjustment basis, and research eligibility remain unverified. |
| Tier A intraday history in Parquet (1m and 5m) | Sol / Terra | Upstox V3 intraday history has a fixed provider floor of January 2022. Do not probe for earlier intraday history; it is unavailable through this provider. One-month maximum request span for 1–15m. Resumable loader and tests are implemented; sustained full-universe collection still pending. |
| Corporate-action adjustment, source adapter added; data/coverage gates open | Terra / Sol | Authenticated Upstox per-ISIN API access works with the browser-like User-Agent after the earlier 403. Five pilot responses were archived locally; all contained dividends only, so they do not establish historical action completeness. A manual, offline register and fail-closed coverage gate are being added; no NSE/NiftyIndices automation is used. A real Reliance 1:1 bonus sample is price-continuous (Oct 2024), but volume basis and broad provider behavior remain unverified. Do not rebuild candles or claim coverage from an empty/partial response. Position replay remains incomplete. |
| Research universe: pure turnover selector; broad source unimplemented | Terra / Sol | ADR-0026's Top-50 rolling 60-session median-turnover selector remains implemented with synthetic tests only. It is not used by the five-symbol pilot. No real Top-50 snapshot or survivorship-free claim is allowed until a permitted, complete historical source is established; automated NSE/NiftyIndices collection remains prohibited. |
| Nifty 50 point-in-time manifest: validator only, benchmark-only | Terra / Sol | Membership models validate supplied manifests; no automated NSE Indices collection exists. This is outside the five-stock pilot's eligibility universe. Benchmark comparisons require an authorized series with documented return type and coverage. Broad point-in-time membership remains a follow-up. |
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

Pilot exit: reproducible daily and intraday history for the five fixed symbols
is complete over declared windows; action basis and event coverage are verified
for those exact symbols/windows or affected windows are excluded; source
artifacts and adjustment metadata are reproducible; the pilot calendar and
dataset are frozen; and chronological development/validation/holdout boundaries
are recorded before holdout access. The full Top-50 universe, historical
eligibility and broad point-in-time index membership remain a separate
follow-up. Source authorization and coverage remain hard gates.

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
The Upstox per-ISIN corporate-actions API is the selected action-data
candidate; see `specs/DATA_SOURCES.md`. On 2026-11-15, five responses were
successfully archived and contained 1-5 dividend records each, all dated in
2026. This does not cover the 2010-2015 candle window or establish completeness.
The API documentation does not explicitly include demergers, so those
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
| Fixed candidate family spec, declared before any ranking | Sol / Terra | 12 daily and 3 intraday variants are frozen in their catalogs; T3 is deferred because K=20 degenerates on five symbols, and RPF is also deferred before result inspection. |
| Declared parameter grid per candidate, with a hard cap on variations | Sol / Terra | state the cap explicitly in the spec file; no free-form parameter sweeps |
| Versioned, deterministic spec per candidate | Sol / Terra | same immutable-version discipline as `STRATEGIES.md` §6 |

Exit: every executable candidate and parameter grid exists in a spec file
before any backtest runs; the cap on variations is a number written down, not
an intention. Twelve daily variants (T1/T2/T4/T6) and a three-variant 5-minute
ORB catalog are specified. T3 and RPF are deferred. The multiple-testing
family is 15 variants across daily and intraday catalogs; no results may be
generated until P1a gates pass.
Numeric promotion policy is a P1c deliverable. Backtest results alone do not
promote a strategy to paper or live use.

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

### Candidate ideas deferred from the five-symbol P1 pilot

T3 cross-sectional momentum is deferred because its frozen `K=20` selection
and top-`2K` exit are degenerate on the five-name pilot: all names fit within
the selection and exit bands. Do not silently change the rule to fit this
small universe. Revisit only for a wider-universe follow-up.

The RPF idea below is also deferred, before any P1 result inspection.

**Regime-Gated Failed-Breakout Pullback.** Long only when price is above a
rising SMA(200) and volatility is not extreme. Detect a Donchian breakout that
fails and closes back inside the channel. Wait for a controlled pullback
(RSI(2) oversold, still above the trend filter, volatility contracting). Enter
at the next bar's open after recovery confirmation. ATR stop plus a fixed time
stop. No pyramiding. No trade when trend and volatility signals disagree.

This idea is deferred before P1 results and does not count as a P1 candidate.
It may be specified for a separate future catalog version before that study's
data is inspected; it cannot be added to this P1 family after results.

Exit (P1 overall): P1a-P1d complete for the 15-variant pre-registered pilot
candidate library;
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

## Open questions and bounded decisions (P1 restructure)

- **Full-universe research data source remains unimplemented.** ADR-0026 selected
  the turnover-ranking rule, but no permitted turnover history has been
  acquired. The selector is pure and tested only with synthetic normalized
  rows. Automated NSE/NSE Indices collection is prohibited by the current
  project source policy. The Nifty membership package is a validator only.
  First pass uses the fixed five-symbol pilot; broad generalization remains
  blocked until the historical universe source gap is resolved.
- ~~Capital and per-trade risk assumptions~~ — **resolved.** 1% per-trade risk
  on a ₹1,00,000 placeholder capital for P1b/P1c comparisons; not real trading
  capital, used only so every candidate is sized identically.
- **Target holding horizon.** Owner directed daily swing and intraday research
  together from the start. Both remain in P1; promotion uses the stricter
  intraday bar described in P1c.

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

## MCX commodities coverage (verified, not assumed)

Checked empirically against Upstox's public API docs (instrument master and
V3 historical-candle docs) and MCX's own public bhavcopy page, per AGENTS.md
rule 9 ("do not build on an unverified source") and the explicit flag that
this phase was most likely to hit a paywall.

- **Free source found:** Upstox. Its daily-refreshed instrument master
  (`https://assets.upstox.com/market-quote/instruments/exchange/MCX.json.gz`)
  lists `MCX_FO` as a segment alongside `NSE_EQ`/`NSE_FO`/`BSE_FO`/`CDS_FO`,
  with `lot_size` and `expiry` per contract — a free, structured
  contract-master feed, no separate vendor needed. `UpstoxHistoryClient`
  (`src/trading/adapters/upstox_history.py`) is instrument-key-agnostic (it
  URL-encodes whatever key it's given and hits the same
  `/v3/historical-candle` path regardless of segment) — proven by
  `tests/storage/test_mcx_universe.py::
  test_existing_upstox_client_accepts_an_mcx_instrument_key`, which feeds an
  `MCX_FO|GOLD...` key through the unmodified client, same pattern as the
  NSE-currencies phase. Did **not** edit `upstox_history.py`.
- **MCX's own site:** mcxindia.com publishes free daily bhavcopy (CSV/PDF,
  no login) as a secondary/cross-check source, but only recent history for
  free (roughly the last ~3 months outside the most recent 12, per MCX's own
  terms) — Upstox is the primary source for depth.
- **Contract roll / continuous series — unlike NSE currencies, built this
  time.** MCX futures have real term-structure (contango/backwardation from
  cost-of-carry), so a continuous series is more likely to be wanted than
  for FX. `src/trading/adapters/mcx_roll.py` implements ratio
  back-adjustment (ponytail: chose ratio over additive specifically because
  commodities can swing enough in relative price that an additive offset
  risks pushing an old leg through zero/negative — a ratio cannot). Proven
  with a known-answer test
  (`tests/adapters/test_mcx_roll.py::test_continuous_series_has_no_fake_jump_at_the_roll`)
  using illustrative-but-realistic gold-futures contango prices: raw
  concatenation shows a fake ~300 jump at the roll date; the back-adjusted
  series shows none. This is a **display/backtest series only** — live
  signal code must still read the single current-expiry instrument_key
  directly (AGENTS.md §4.5, no look-ahead); the adjustment runs after a
  leg's full history is already known, exactly like
  `trading/storage/corporate_actions.py`'s multiplicative `adj_factor`
  convention (reused here, not reinvented).
- **Reusable for NSE currencies:** `build_continuous_series` takes a plain
  list of `ContractLeg(instrument_key, candles)` — nothing MCX-specific in
  its signature. If a continuous FX series is ever wanted (phase 3 flagged
  this), it can call this function directly with CDS_FO legs.
- **Universe:** fixed, tiny, hand-enumerated set — GOLD, SILVER, CRUDEOIL,
  NATURALGAS, COPPER (`src/trading/storage/mcx_universe.py`), MCX's own most
  liquid contracts. No liquidity-rule universe (AGENTS.md §10).
- **Session hours:** docs/MARKETS.md's "approx 09:00–23:30, or 23:55 in some
  seasons" note was not re-verified against a primary source in this pass
  (out of scope for the data-adapter work) — still flagged for a human/future
  session to confirm against MCX's circular before any live/paper trading
  uses the session boundary.
- **Net verdict:** a free source exists and is the one already in use for
  every other NSE-routed sleeve; MCX did *not* hit the paywall this project
  feared. Status: "MCX commodities" data-ecosystem checklist item: done.
