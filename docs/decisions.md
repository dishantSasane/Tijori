# DECISIONS (ADR log)

Append-only. Format: `ADR-NNNN · date · status · title` then Context / Decision / Consequences. Change a decision by adding a new ADR that supersedes the old one.

---

**ADR-0001 · 2026-11-14 · accepted · Multi-market system built from "sleeves"**
Context: owner wants diversification across Indian stocks, US stocks, crypto, commodities, currencies, later options/memecoins.
Decision: each market is a sleeve with its own profile, budget, limits, hours, costs, strategy instances.
Consequences: adapters + profile per market; shared core.

**ADR-0002 · 2026-11-14 · accepted · Five-layer architecture (Eyes, Calculator, Brain, Hands, Voice)**
Decision: as in `ARCHITECTURE.md`. The Brain (LLM) is optional and advisory; risk engine has final veto.

**ADR-0003 · 2026-11-14 · accepted · Two tiers per stock market**
Context: thousands of listed companies cannot be streamed.
Decision: Tier A ≈100 live names; Tier B whole market via daily files + scanner -> shortlist -> promotion to live watch. Penny stocks are a config filter, not a separate feature.

**ADR-0004 · 2026-11-14 · accepted · Summarise ticks into candles; keep candles, drop ticks**
Decision: persist closed candles forever; raw ticks rolling buffer (default 3 days). Incremental indicators in live; identical batch implementations in backtest; equivalence tests.

**ADR-0005 · 2026-11-14 · accepted · Modes: paper -> approval -> auto; auto-paper shadow**
Decision: per-sleeve mode; Approve/Paper test/Reject buttons; shadow paper-trading of all signals and outcome tracking of rejected ones; alerts show similar-setup statistics over many signals.

**ADR-0006 · 2026-11-14 · accepted · Strategy instances = template x market profile; nothing transfers across markets**
Decision: registry with immutable versions; promotion gates; champion/challenger; daily monitoring, weekly review, monthly/quarterly retune; early review triggers.

**ADR-0007 · 2026-11-14 · accepted · Phase-1 strategy templates**
Decision: T1 Donchian, T2 MA+ADX, T3 cross-sectional momentum, T4 RSI(2) pullback, T5 ORB, T6 Bollinger reversion, F1 candlestick filter (confirmation only). Later templates in `STRATEGIES.md` §4.

**ADR-0008 · 2026-11-14 · accepted · Brain cost and safety rules**
Decision: Brain OFF until rules-only works; called only on formed signals with ~500-token summaries; cached shared context; strict output schema (support/neutral/veto, size multiplier 0..1, can only reduce); hard INR budget guard; judged only by forward paper A/B. Provider swappable (Anthropic/OpenAI API). Subscriptions do not cover API use.

**ADR-0009 · 2026-11-14 · accepted · Free-first data/broker stack**
Decision: free data from Angel One SmartAPI or Fyers (verify), orders via Zerodha Kite Connect Personal (free, no data), Alpaca free for US, CCXT public for crypto. Separate `DataFeed` and `Broker` adapters.

**ADR-0010 · 2026-11-14 · accepted · India live orders require a static IP -> cloud VM at go-live**
Context: SEBI framework mandatory since 2026-04-01 (`COMPLIANCE_INDIA.md`).
Decision: laptop for research/paper; small VM with reserved static IP registered with the order broker before live; keep IP stable.

**ADR-0011 · 2026-11-14 · accepted · Fail closed and safety gates**
Decision: AGENTS.md §4 gates; kill switches; invariants I1-I13; reconciliation; mode escalation only by human.

**ADR-0012 · 2026-11-14 · accepted · Data retention**
Decision: keep downloaded raw files/candles (small); delete only regenerable derived data; history must include delisted instruments and be corporate-action adjusted.

**ADR-0013 · 2026-11-14 · accepted · Repo workflow with two agents**
Decision: `main` protected; agents work on `claude/*` and `codex/*` branches via PR; cross-model review; owner approves merges; `handoffs` branch is the open message board (notes only). Commit-message trailers carry short signals. See `GIT_WORKFLOW.md`, `HANDOFFS.md`.

**ADR-0014 · 2026-11-14 · accepted · Model routing under the owner's plans**
Decision: Claude Pro (ends ~2026-11-16) is used for a P0 foundation sprint producing specs/contracts/tests; ChatGPT Plus (Codex: Sol/Terra/Luna, Astra sparingly) builds from P1; Claude audit before first live money. See `MODEL_ROLES.md`.

**ADR-0015 · 2026-11-14 · accepted · Testing system**
Decision: layered tests (unit, blind, property, equivalence, look-ahead, known-answer, adapter contract, failure injection, adversarial, replay, mutation, soak); author != tester; second reference backtester. See `TESTING.md`.

**ADR-0016 · 2026-11-14 · accepted · Pages**
Decision: Home, market pages, Stocks, News, Paper ledger, Strategies, Usage and accounts, Settings and risk. See `PAGES.md`.

**ADR-0017 · 2026-11-14 · accepted · Options and memecoins are gated**
Decision: options only defined-risk and only after dedicated learning; memecoins paper-only until a forward record justifies more; both last in the build order.

**ADR-0018 · 2026-11-14 · proposed · Risk-engine clarifications made while writing RISK_ENGINE_SPEC.md**
Context: `docs/RISK_SPEC.md` left several behaviors implicit; Codex's handoff note 0003 flagged them as contradictions/ambiguities before any code existed. Writing `docs/specs/RISK_ENGINE_SPEC.md` required picking concrete answers rather than leaving them for an implementer to guess.
Decision: (1) a `RiskDecision(allowed=False)` never produces a fill of any kind, in any mode — `auto_paper_shadow` only shadows a *human* rejection in `approval` mode, never a risk-engine rejection (RISK_ENGINE_SPEC.md §7). (2) On a gap through the stop, the position fills at the actual open and the resulting excess risk is logged as a distinct `gap_risk_realized` audit event rather than silently absorbed or resized (§9). (3) Freshness (`DATA_STALE`) is checked only while a market's session is open — outside session, `MARKET_CLOSED` is the fail-closed gate instead, so the two checks aren't in conflict (§6). (4) A Brain call that returns invalid/unparseable output must be caught at the **adapter** layer and turned into `None` before it ever reaches `RiskEngine.check()`, which only ever sees a schema-valid verdict or `None` (§5) — logged as a distinct `brain_call_invalid` vs. `brain_call_absent` audit event so the two cases stay distinguishable later.
Consequences: implementers build against these answers directly; if any is wrong, it's one ADR to supersede, not a silent behavior buried in code. Status `proposed` because none of this has been confirmed by the owner or tested in practice yet — only written down so the question doesn't have to be re-asked.

**ADR-0019 · 2026-11-14 · proposed · Strategy-spec clarifications made while writing STRATEGY_SPEC.md**
Context: `docs/STRATEGIES.md` is precise about entry/exit rules but silent on several mechanical details a backtester/live engine needs. Resolves handoff note 0003's Q5-Q6.
Decision: (1) `Signal.target` stays optional; T1/T2/T4/T6 have no target and exit by re-evaluating a condition each closed bar instead (STRATEGY_SPEC.md §1.7) — T5 is the only template with a mandatory target. (2) A signal formed on the last available closed bar with no next bar yet to fill at is excluded from backtest results entirely (not synthesized a fill), and expires unfilled in live if the session ends before a next bar forms (§1.6). (3) Wilder-smoothed indicators (RSI/ATR/ADX) seed with a simple average of the first `n` values, then recurse (§1.3) — stated explicitly so two implementations don't silently diverge on seeding. (4) Bollinger Band standard deviation uses the **population** formula (not sample) by default, since STRATEGIES.md didn't specify either (TEST_SPEC_CANDLES.md §2) — flagged as a genuinely open micro-decision, not a confident choice.
Consequences: same as ADR-0018 — these are the defaults code should be built against; any of them can be revisited via a new ADR once real backtests expose a problem with the choice. Status `proposed`.

**ADR-0020 · 2026-11-14 · proposed · Known gaps deliberately left open rather than guessed**
Context: writing the P0 specs surfaced two design questions genuinely beyond this session's scope to answer well.
Decision: left open, flagged in-place rather than silently resolved: (1) condition-based exits (T1/T2/T4/T6) need a new `ExitRequest`-shaped contract and a reduced, exit-only risk-check list (closing risk should not need the full entry check list) — STRATEGY_SPEC.md §1.7. (2) Concurrent delivery of the same `signal.id` needs an explicit `DecisionStore` atomicity design (single-process lock vs. a datastore-level check-and-set) before invariant I7 can be proven under real concurrency, not just sequential retries — RISK_ENGINE_SPEC.md §10, TEST_SPEC_RISK.md §7.
Consequences: P2's risk-engine implementer should resolve both before or during implementation, not discover them mid-build. Status `proposed` pending that work.

**ADR-0021 · 2026-11-14 · accepted · Exit requests are position-reducing and Brain-independent**
Context: T1/T2/T4/T6 condition-based exits need a contract distinct from entry
orders. Protective exits must remain possible during a kill switch, while an
invalid position or reconciliation state must fail closed rather than guess.
Decision: introduce an `ExitRequest` with a unique `exit_id`, required
`position_id`, derived position side, `reason_code` plus non-executable human
text, and `0 < quantity <= open quantity`. Exits enforce position/broker truth,
reconciliation, quantity, market-session/queue, paper-mode, and audit checks;
they skip entry-only sizing, allocation, max-position, and Brain checks.
`STOP` and `KILL` exits cannot be vetoed. No exit may open or increase a
position (new invariant I14); duplicate `exit_id` delivery is idempotent.
Consequences: condition exits can be implemented without routing them through
entry sizing. Exit execution remains fail-closed on state mismatch, and I14
requires property-based coverage plus blind tests from the specification.

**ADR-0022 · 2026-11-14 · accepted · Reference condition exits are a P3 gate**
Context: the primary runner now accepts close-based condition exits, but the
independent reference runner currently covers stop, target, and gap behavior
only. Condition exits must not be accepted on one implementation alone because
timing errors can materially change a scorecard.
Decision: by P3, the second reference backtester must independently implement
T1, T4, and T6 condition exits and match the primary runner's trade list. The
condition is evaluated on a closed bar, then the exit fills at the next bar's
open with adverse sell slippage; a final-bar condition remains pending/unfilled.
Match timing, reason, fees, and final position state on known-answer and
property datasets. Until that gate passes, condition-exit scorecards are not
promotion evidence.
Consequences: P1 can proceed with non-condition backtester validation, but
strategy promotion and go-live remain blocked on this cross-model equivalence
gate. No implementation may silently treat a stop/target-only reference as
complete.

**ADR-0023 · 2026-11-14 · accepted · Upstox is the P1 India historical-data source**
Context: the owner chose one concrete source for the P1 research and backtesting
slice after the tokenless daily and past-day intraday probes and the validated
Parquet loader were completed.
Decision: use the existing Upstox historical-candle adapter for P1 India daily
and intraday research data. Keep raw provider responses/fixtures, request
parameters, ingestion timestamps, and candle provenance. This does not select a
P3 live feed, an execution broker, or authorize live orders.
Consequences: P1 can collect the Nifty 50/Tier A research set and generate T1/T4
scorecards against one adapter. Corporate-action adjustment, historical
membership, and provider terms still need validation before results are called
survivorship-free or production-ready.

**ADR-0024 · 2026-11-15 · accepted · P1 restructured into pre-registered discovery/validation/holdout + regime-gated activation**
Context: P1 was originally "pick strategies, backtest them," which ranks
candidates by historical P&L — the metric most vulnerable to overfitting and
selection bias. The owner decided to replace this before any strategy
discovery beyond the existing T1/T4 baselines proceeds.
Decision: split P1 into P1a (frozen data foundation: corporate-action
adjustment, point-in-time universe, frozen chronological splits), P1b
(pre-registered candidate library with a capped parameter grid), P1c
(evaluation harness with a multiple-testing correction and an experiment
registry logging every attempt including failures), P1d (one-shot holdout
evaluation with a pre-written rejection rule), and P1e (a regime-gated
activation layer that selects the eligible strategy per instrument, subject
to the same split discipline, defaulting to flat when nothing is eligible).
Risk engine mode gating is correspondingly tiered: auto-execute only for
strategies marked `promoted` under declared thresholds, approval required
otherwise or on an anomaly check, pre-market batch approval, and a Telegram
spec where silence never means "something broke." Full detail:
`BUILD_ORDER.md` P1a-P1e, `RISK_SPEC.md` §2A.
Consequences: strategy-discovery work (beyond T1/T4) does not start until
P1a's data gaps (point-in-time universe, corporate actions) are resolved or
explicitly waived by the owner. Source-independent candidate definitions,
metric implementations, registry contracts, and synthetic validation may be
built before that gate; no real-data discovery/ranking may run. The untouched
holdout from the current 2016-2026 sample is no longer valid once inspected,
so a new, genuinely unread holdout range must be committed in P1a config
before P1b/P1c runs.

**ADR-0025 · 2026-11-15 · superseded by ADR-0026 (membership branch) · P1 data and evaluation assumptions requiring owner decision**
Context: P1a-P1c cannot be made reproducible by implementation choices alone.
Historical index membership has a possible official source, but its coverage,
licence, and price are unpublished; using today's membership creates
survivorship bias. P1's comparison also needs common sizing assumptions and an
explicit holding horizon before metrics can be interpreted.
Decision: leave these as hard gates, not defaults. For historical Nifty 50 /
Next 50 membership, first request a quote and written coverage/licence details
from NSE Indices; proceed only after the owner accepts the source/terms or
explicitly signs off on a scoped survivorship-bias caveat. For comparisons,
the owner must choose (or explicitly authorize a documented research-only
assumption for) starting capital and per-trade risk. The owner must confirm
daily swing horizon or specify another target horizon. Until these are settled,
do not freeze split dates, ingest index history under an assumed licence, or
rank a strategy library as if the results represented the intended system.
Consequences: P1 can continue on source research, data-contract design, and
synthetic/known-answer validation that does not consume the holdout. Real-data
discovery and P1a completion remain blocked on the relevant decisions.

**ADR-0026 · 2026-11-15 · accepted · Research universe rule and comparison sizing**
Context: ADR-0025 gated P1a on historical membership/licensing, sizing, and
horizon decisions. The owner selected a turnover-ranked universe and declined
an NSE Indices licence inquiry. That resolves the selection method, but does
not itself verify source rights or historical completeness.
Decision: (1) The **research universe rule** is monthly, ISIN-keyed ranking of
NSE cash equities by trailing 60-session median turnover: top 50 for primary
research, with top 100 reserved for later research. NSE
`sec_bhavdata_full` is the proposed turnover source. Public availability does
not establish permission for systematic collection, storage, derived data, or
backtesting. The archived schema, stable identifiers, eligible-security
coverage, and treatment of missing/no-trade rows remain unverified. A
survivorship-free claim requires evidence that authorized dated inputs include
eligible securities later delisted and resolve coverage gaps. (2) A **Nifty
50 point-in-time manifest remains benchmark-only**, not the research universe.
The proposed reconstruction uses dated official replacement notices and
records their URLs. The notices' completeness, corrections, and permitted use
remain to be established; unresolved events or identities prevent a
completeness claim, and a constituent manifest alone does not calculate index
returns. (3) No NSE Indices quote/licence inquiry will be sent. (4)
Research-comparison sizing is set at 1% per-trade risk on ₹1,00,000 placeholder
capital, not the owner's real trading capital, so candidates use a common
comparison assumption.
Consequences: `trading.storage.membership` remains a validator for a
benchmark-membership manifest, not evidence that a complete manifest has been
assembled. Pure selector and manifest contracts may be developed with
synthetic data. Real source collection/use and P1a completion remain gated on
documented rights, schema, and coverage. Sizing is resolved. Still open: the
holding horizon and untouched holdout range (the 2016-2026 sample remains
burned per ADR-0024). A later empirical probe found Upstox's NESTLEIND daily
candles already adjusted for its 10:1 split effective 2024-01-05; do not
double-adjust this event. Adjustment basis for other event types/symbols and
corporate-action position replay remain to be verified.

---

**ADR-0027 · 2026-11-15 · accepted · P2/P3 wiring specs: Telegram state machine, risk test vectors, candle builder/scheduler**
Context: `PAPER_BROKER_SPEC.md` (P2) and `RISK_SPEC.md` §2A defined the fill
model and routing rules but not the Telegram approve/paper-test/reject
state machine or concurrency behaviour; `TEST_SPEC_RISK.md` had no test
vectors for the paper broker's 6-step kill-switch drill; and P3's live
candle builder / market-session scheduler was referenced in `ADAPTERS.md`
and `ARCHITECTURE.md` but never pinned down as one algorithm shared by the
live and backtest/bhavcopy paths.
Decision: (1) wrote `docs/specs/TELEGRAM_ALERT_SPEC.md` — a 5-state machine
(PENDING/APPROVED/PAPER_TESTED/REJECTED/EXPIRED) backed by a
`telegram_decisions` SQLite table, pre-market batch mechanics, and an
optimistic-write rule so Telegram and the dashboard can race on the same
signal without double-deciding it. (2) extended `TEST_SPEC_RISK.md` §8 with
the drill's automated-test form, explicitly using the real paper broker
(not `FakePaperBroker`, which can't exercise persistence). (3) wrote
`docs/specs/CANDLE_BUILDER_AND_SCHEDULER_SPEC.md`, pinning the previously-
open "which tick's price is `open` under reordering" question
(`TEST_SPEC_CANDLES.md` §1.3) to "chronologically-earliest tick by its own
timestamp," and defining a `CLOSED -> PRE_OPEN -> OPEN -> POST_CLOSE ->
CLOSED` per-market session state machine. (4) cherry-picked
`PAPER_BROKER_SPEC.md` from the still-open `claude/p2-paper-broker-spec`
branch (PR #48) into this branch, since the three new specs reference it
and it wasn't yet present here — the file's content is unchanged from that
PR; `docs/specs/README.md` was updated to list all P2/P3 spec files in one
place instead of drifting further out of sync with `ls docs/specs/`.
Consequences: Codex can implement P2's Telegram wiring and P3's candle
builder/scheduler against a fixed contract. Two things left genuinely open,
flagged `needs-human` rather than guessed: MCX's exact session calendar
(`CANDLE_BUILDER_AND_SCHEDULER_SPEC.md` §3.1 — no confirmed free
machine-readable source yet) and the daily report's content/format (§3.4,
deferred to a future spec if P3 proves one is needed).

---
**ADR-0029 · 2026-11-15 · accepted · P1 corporate-action source and NSE collection boundary**
Context: NSE/NSE Indices website terms prohibit systematic or automated
collection for the intended P1 workflow, and the project must not build an NSE
site scraper. P1 also needs corporate-action events so split/bonus price
history and open positions are handled without silently ignoring demergers or
rights issues.
Decision: use Upstox's documented authenticated per-ISIN Corporate Actions API
as the P1 action-source candidate. Preserve the response and raw ratio/details;
do not infer factor direction from text. Do not automate downloads from
NSE/NSE Indices. The research-universe selector and index-membership validator
remain source-independent contracts only; no NSE bhavcopy collector, Nifty
press-release scraper, or populated historical membership manifest exists.
The Upstox API docs list dividends, bonuses, splits, and rights but do not
explicitly promise demerger coverage or exhaustive historical completeness;
demergers and unknown/missing events require a manually reviewed permitted
supplement or another authorized source. A live request on 2026-11-15 received
Cloudflare HTTP 403 `browser_signature_banned` and said not to retry, so no
response ledger was acquired. Keep P1a data rebuild, backtest runner screening,
position replay, and split freeze blocked until API access and coverage are
verified and event records are persisted.
Consequences: an Upstox API client may be tested from documented fixtures, but
must not treat an empty result as proof of no actions. Data-source rights and
technical access are separate gates; this decision selects the intended
provider but does not claim successful acquisition or full event coverage.


**ADR-0028 · 2026-11-15 · accepted · P2 implemented out of role-split order, by owner's direct instruction**
Context: `MODEL_ROLES.md` assigns P2 implementation (risk engine, paper broker,
Telegram wiring) to Codex (Sol/Astra), with Claude's role limited to specs
and cross-model review. The owner explicitly instructed Claude to implement,
test, and move on rather than wait — overriding that role split for this
phase only, not any of AGENTS.md §4's hard safety rules (those still apply
unconditionally and were followed: paper-only, no real-order path, fail
closed, no secrets).
Decision: implemented P2 against `docs/specs/RISK_ENGINE_SPEC.md`,
`docs/specs/PAPER_BROKER_SPEC.md`, and `docs/specs/TELEGRAM_ALERT_SPEC.md`
in `src/trading/risk/`, `src/trading/broker/paper_broker.py`, and
`src/trading/alerts/telegram.py`, with SQLite persistence
(`src/trading/storage/state_db.py`) shared by all three. Reused
`trading.backtest.fills` for fill/slippage math rather than reimplementing
(per the spec's own instruction). Telegram wiring uses a `MessageSender`
Protocol with a `LoggingMessageSender` stand-in — no real bot token exists
yet (owner said not to wait for it); swapping in a real Telegram client
later requires no change to the state machine. Added two `ReasonCode`/
`OutcomeResult` enum values the specs required but hadn't been appended yet:
`CONCURRENT_POSITION_EXISTS`, `SESSION_ENDED_UNFILLED`. Full automated
6-step kill-switch drill (docs/specs/PAPER_BROKER_SPEC.md §6) implemented
and passing against the real `PaperBroker`/SQLite, not `FakePaperBroker`.
`ruff`/`mypy --strict` clean on the whole repo; full test suite green
(tests/risk, tests/broker, tests/alerts).
Consequences: found and did **not** silently fix a pre-existing arithmetic
error in `docs/specs/TEST_SPEC_RISK.md`'s S4 known-answer row (equity=10,000
example computes `qty=1`, not the stated `qty=0`) — flagged in the test file
itself rather than changing the sizing formula to match broken numbers
(AGENTS.md §4 rule 9). The risk engine's check order collapses check 2
("mode permits any route") to a documented no-op, since no current `Mode`
value fails it — routing itself is `ModeGate`'s job per spec §7. P2's
`DecisionStore` concurrency note (RISK_ENGINE_SPEC.md §10's open question)
is resolved here via a single atomic `INSERT ... WHERE NOT EXISTS`, adequate
for a single-process deployment; a multi-process deployment would need the
same guarantee from the database layer, not this code. Still owned by Codex
going forward: real `exchange_calendars` session wiring (today a
`SessionCalendar` Protocol + fake), real `DataFeed` freshness wiring (same
pattern), and the real Telegram bot once a token exists.

**ADR-0028 follow-up (2026-11-15, same day): PaperBroker routes exits through
the canonical `ExitRequest` path.** The owner flagged, during review of
PR #50, that `PaperBroker._close_position` closed positions with a direct
SQL delete instead of through `ExitRequest`/`apply_exit_quantity` (the I14/I7
path PR #40 hardened) — a legitimate gap, not a false alarm. Fixed: every
stop/target close now builds a real `ExitRequest` (`PaperBroker.
build_exit_request`), validates it through `apply_exit_quantity` (raises if
it would leave a nonzero remainder — this broker only supports full closes
today), and dedupes on `exit_id` via the same atomic
`INSERT ... WHERE NOT EXISTS` pattern as `DecisionStore`, before touching the
`positions`/`fills` tables. `OpenPosition.position_id` is a stable,
broker-truth-derived string (`"{market}:{symbol}:{sleeve}"`), not a fresh
UUID per call, so the same open position always resolves to the same
`exit_id` across restarts. Two new tests prove this is not a bypass:
`test_exit_goes_through_canonical_exit_request_not_a_bypass` (the fill
actually recorded carries the independently-derived `exit_id`) and
`test_duplicate_exit_for_same_position_reason_bar_is_idempotent` (re-applying
the identical exit produces zero new fills, one `exit_already_applied` audit
row). Full suite, `ruff`, `mypy --strict` re-verified clean after the change.

**ADR-0029 · 2026-11-16 · accepted · P3 daily report reads the state DB directly, scoped by UTC date-prefix match**
Context: BUILD_ORDER.md P3 item 5 needs an end-of-day summary (signals, fills,
P&L, rejection reasons). The state DB (`state_db.py`) already carries
`fills`, `decisions`, and `signal_outcomes` tables with `TEXT` UTC timestamp
columns written as ISO-8601 strings.
Decision: `build_daily_report(conn, date)` in
`src/trading/reporting/daily_report.py` takes a `YYYY-MM-DD` UTC date,
never calls `datetime.now()`, and matches rows with `ts_utc LIKE '<date>%'`
-- a plain string-prefix match, not a timezone-aware range query. This is
only correct because every writer in this repo stores UTC with a fixed
`+00:00`/`Z` suffix (AGENTS.md §6); it would silently misbehave if a writer
ever stored local time. Alternative rejected: a `BETWEEN` range query on
parsed datetimes -- more robust to timestamp format drift, but the schema
has no index on a parsed form and it's extra code for a format this repo
already guarantees elsewhere. Flagged with a `ponytail:`-style note in the
module docstring instead of building the general form now.
Consequences: cheap, correct today; if timestamp storage format ever
changes, this function (and nothing else, since it's the only reader) needs
a matching update.

**ADR-0030 · 2026-11-16 · accepted · P3 Streamlit dashboard reads SQLite directly, not through an internal API**
Context: `docs/PAGES.md` §3 specifies a FastAPI internal API
(`GET /home`, `GET /ledger/{live|paper}`, ...) that the dashboard is meant
to call, with §4's rule that "the dashboard never talks to brokers
directly; only the engine/API does." That API does not exist yet -- there
is no running engine process this session, only the SQLite state file it
will eventually write to.
Decision: ship four read-only Streamlit pages (`dashboard/Home.py`,
`dashboard/pages/{1_India,2_Paper_Ledger,3_Strategies}.py`) that open the
state DB directly via `dashboard/_data.py::get_connection()`, which only
ever issues `SELECT`s. The owner's rule still holds in spirit -- nothing
here can place an order or change a mode, because nothing here writes --
but it is a real simplification: once `docs/PAGES.md`'s API exists,
`_data.py` is the one file to swap for HTTP calls, and no page changes.
Alternative rejected: build the FastAPI layer first -- correct per spec,
but there is no engine running yet to serve it against, so it would be
untestable scaffolding today.
Consequences: needs-human note filed (see handoff) that this is a
deliberate scope cut, not an oversight, so a reviewer doesn't flag it as a
silent spec deviation.

**ADR-0031 · 2026-11-16 · needs-human · P3 live data adapter and ORB/breakout paper wiring deferred**
Context: P3's remaining scope (BUILD_ORDER.md) calls for (a) a real
live/intraday `DataFeed` for NSE and (b) wiring the P1b ORB/breakout
strategies through candle builder -> risk engine -> paper broker. Checking
`origin/main`: `src/trading/strategies/` contains only `phase1.py`; the
T1/T2/T4/T6/ORB implementations are still on PR #53 (per `handoffs`
STATUS.md, "implementation-complete, Claude-reviewed, approved" but not
merged). `docs/specs/DATA_SOURCES.md` confirms no India source is yet
*selected* for a live feed -- Upstox's live-feed terms are unconfirmed, and
every free alternative (Angel One, FYERS) needs the owner's own
account/app setup before any adapter code can be written against it, let
alone tested.
Decision: do not build either item in this session. Building a live
adapter against an unconfirmed/unselected API would be guesswork; wiring
strategies that are not on `main` would mean importing from an unmerged PR
branch, which is exactly the kind of duplicated-work mistake a previous
session already made (see STATUS.md note 0035).
Consequences: see the handoff note for the precise question for the owner
and for Codex/Claude's next session.

**ADR-0032 (2026-11-16): P4 scanner ranking is a placeholder momentum score, not a strategy.**
Context: P4 asks for a daily scanner and shortlist. The real strategy
candidate library (T1/T2/T4/T6/ORB) is still on unmerged PR #53 — wiring the
scanner to it now would repeat the stale-ref mistake note 0035 already
flagged once this build.
Decision: `scanner.py` ranks candidates by "closes above its own 20-day
average" (a momentum score), with a flat +8%/-5% target/reconsider band.
This is labeled with `ponytail:` comments as a placeholder in the module
constants. It is never used to size or place an order — only to order a
read-only shortlist.
Consequences: once PR #53 merges, swap `scan_symbol`'s ranking/target/stop
for the real strategy's entry/stop/target. The filter / shortlist /
backtest machinery around it does not need to change.

**ADR-0033 (2026-11-16): shortlist persistence reuses `state_db.py`; it is list membership, not strategy promotion.**
Context: `docs/STRATEGIES.md` §6/§8 already uses "promotion" for moving a
*strategy version* to live. P4 needed a different kind of promotion: which
*symbols* the scanner currently likes.
Decision: added one table, `scanner_shortlist`, to the existing shared
schema in `src/trading/storage/state_db.py` rather than a new DB file.
`shortlist_store.apply_scan()` is the only writer: one call per day's scan,
upserts today's ideas as `active`, demotes anything previously `active` but
absent from today's run to `removed` (never deleted, so history survives).
Consequences: shortlist history is queryable for as long as the state DB
lives. If multiple scans ever run per day, "per day" degrades to "per
call" — fine for P4's cadence, would need a `run_date` column if that
changes.

**ADR-0034 (2026-11-16): scanner backtest is forward-outcome replay, not a fill simulator.**
Context: `src/trading/backtest/` already simulates fills/fees/P&L for a
*strategy*. P4's "scanner backtest" is a different question — "what
happened after the scanner would have shortlisted this symbol" — and
reusing the strategy backtester for it would conflate the two.
Decision: `scanner/backtest.py`'s `replay()` reruns `run_scan` per
historical session date (decisions see only candles strictly before that
date, enforced by `filters.py`'s window) and measures the close
`horizon_days` later. No fills, fees, or positions are modeled.
Consequences: results are a sanity check on the scanner's filter/ranking
logic, not a P&L claim — the lesson for this phase says so explicitly so
the owner doesn't read "hit rate" as "trading edge."

**Note (2026-11-16, resolved during rebase onto `main`): `dashboard/_data.py` duplication with PR #56 resolved.**
PR #56 merged to `main` first with its own copy of `dashboard/_data.py`.
This PR's byte-identical copy was dropped during its rebase onto `main`
(same file, same content, per the note below before this resolution) --
no functional change, just removing the now-redundant duplicate.

---

**ADR-0029 · 2026-11-16 · accepted · Reconciliation mismatch has no tolerance
band; any difference engages the kill switch.** Context: P7 go-live
readiness needs a rule for what counts as a reconciliation mismatch between
our SQLite-recorded positions and a broker's reported positions, and what
happens when one is found. A tolerance band (e.g. "off by one share is
fine") was considered, to avoid false alarms from a broker's rounding or
lot-size display quirks. Decision: no tolerance band — any quantity
difference, or a position present on only one side, is a mismatch, and it
unconditionally engages the kill switch (`src/trading/reconciliation/
reconcile.py::run_drill`), which blocks new entries (not existing stops)
until a human investigates and explicitly releases it. Consequences: this
can produce an avoidable halt from a benign broker quirk (e.g. a
not-yet-settled corporate action adjusting a displayed quantity); the
alternative — guessing at a tolerance threshold — risks silently trading
through a real discrepancy, which AGENTS.md §4.2 (fail closed) and §4.9 (do
not weaken a check to make something pass) both rule out. If a specific
broker's benign quirk causes repeated false halts, record that broker's
exact behaviour here and adjust with evidence, not a guessed number.

**ADR-0030 · 2026-11-16 · proposed · Cloud VM provider for the static IP
requirement.** Context: Indian brokers require IP whitelisting for API
access, which needs a cloud VM with a provider-guaranteed static/reserved
IP, not a laptop's changing home IP. Low budget is a hard constraint
(AGENTS.md §2). Decision: no VM has been provisioned yet — this ADR records
the *criteria*, not a committed provider, pending the owner's choice:
pick whichever has (a) a reserved/static IP available free or at near-zero
marginal cost, (b) a free-tier or sub-$5/month always-on instance (not a
function/serverless product, which won't hold a stable long-running
process or a consistent outbound IP), and (c) a region close to India for
latency to NSE-adjacent services. Candidates to compare before deciding:
Oracle Cloud's Always Free tier (includes a reserved public IP at no
charge), a low-cost AWS/GCP/DigitalOcean/Linode "lightsail"-class VM
($4-6/month) with an elastic/reserved IP add-on, or a cheap Indian VPS
provider. Consequences: this is a **needs-human** decision — see the P7
handoff note; nothing in this PR provisions, configures, or connects to
any VM.

**ADR-0035 · 2026-11-16 · accepted · P5 market profiles extend `MarketId`, don't fork it; strategy instances are configured, not reimplemented**

Context: P5 (`docs/BUILD_ORDER.md`) asks for market profiles for crypto/US
plus T1/T2/momentum strategy instances against them. `docs/MARKETS.md` §8
and `config/markets.example.yaml` already define what a market profile
needs (calendar, timezone, session, costs); `core/enums.py` already has
`MarketId` as the one sleeve identifier the rest of the system (risk engine,
paper broker, candle store) keys everything by. T2 and a dedicated
"momentum" rule are not implemented on `main` — they live in the strategy
library on open, unmerged PR #53 (`codex/p1-build`).

Decision: `src/trading/core/market_profile.py` adds one `MarketProfile`
Pydantic model loaded from `config/markets.yaml`, keyed by the existing
`MarketId` (via an explicit `MarketId -> yaml key` map, since the two
vocabularies don't line up 1:1 — `MCX_COMMODITY` vs. `commodities_mcx`).
No parallel market-identity concept. `src/trading/strategies/instances.py`
configures the two rules that already exist in `phase1.py` (`t1_donchian`,
`t4_rsi_pullback`) against a small crypto Tier A (BTC/USDT, ETH/USDT) and US
Tier A (AAPL, MSFT, QQQ) — not new strategy math. T2/true-momentum are
explicitly deferred to whenever PR #53 merges; `STRATEGY_ID -> callable` in
that module is the extension point. Funding-rate ingestion (perp carry) is
deferred outright: the crypto sleeve here is spot paper trading only, and a
perpetual-funding sleeve doesn't exist yet to consume it (YAGNI — building
unused plumbing contradicts AGENTS.md §6's "small modules" guidance).

Consequences: crypto/US sleeves get real, typed market-hours knowledge
(`is_24x7` short-circuits any assumption that the session-based scheduler in
`candles/scheduler.py` applies to crypto) and two working strategy instances
each, reusing proven signal math. The alternative — writing new
momentum/T2 math now — was rejected: it would either duplicate or conflict
with PR #53's eventual strategy library, and the task brief's own instruction
was to scope down rather than block, same call P4 made for its ranking
placeholder. Funding data stays a one-line deferral until a derivatives
sleeve is actually built (`docs/MARKETS.md` §4 already flags "Perp funding
rates for carry strategies" as future work, not current scope).

**ADR-0034 · 2026-11-16 · accepted · P8 expansion: MCX/currency instances reuse P5's pattern; gold/bond filter is one line; memecoin gate is in code not config; ML ranker scoped to ranking pre-registered candidates only; options deferred**

Context: P8 (`docs/BUILD_ORDER.md`) is "MCX commodities and NSE currencies;
ML ranker (walk-forward, champion/challenger); options (defined-risk only,
after dedicated learning); memecoin sleeve (paper-only until forward record
justifies); gold/bond ETF filter" — every item explicitly gated. The data
layer for MCX/NSE currency already exists, unmerged, on PR #54
(`trading.storage.mcx_universe`, `trading.storage.nse_currency_universe`,
`trading.adapters.upstox_history` reused verbatim, `trading.adapters.mcx_roll`
for continuous-series stitching). P5 (PR #58) already established the
pattern for turning a fixed universe into strategy instances.

Decisions, one per sub-item:

1. **MCX/NSE currency sleeves**: `strategies/instances.py` gets
   `mcx_instances()` / `nse_currency_instances()` that configure the
   existing `t1_donchian`/`t4_rsi_pullback` rules against the fixed
   five-commodity / four-tenor universes from PR #54. No new strategy math,
   no new data adapter — same reuse call as ADR-0033. `market_profile.py`'s
   `MarketId -> yaml key` map gains `NSE_CURRENCY: "nse_currency"`
   (`MCX_COMMODITY` was already mapped); `config/markets.example.yaml` gains
   an `nse_currency` block (09:00-17:00 IST, differs from equity).

2. **Gold/bond ETF filter**: turned out to be exactly what the brief
   predicted — a near-one-line addition. `GLD` and `BND` were added to
   `US_TIER_A` in `strategies/instances.py`. No new filter subsystem; P4's
   `scanner/filters.py` liquidity/staleness filters are a Tier-B stock-
   scanner concern and don't apply here (this is a fixed Tier-A ETF list,
   not a scanned universe). Rejected a separate `filters/etf.py` module as
   speculative (YAGNI, AGENTS.md §6).

3. **ML ranker**: scoped strictly to *ranking candidates P1 already
   pre-registered and scored*, never to searching for or re-evaluating new
   candidates. Built in `src/trading/research/ml_ranker.py` as an advisory,
   non-execution tool (same posture as the Brain, AGENTS.md §4.6): it takes
   each pre-registered candidate's existing `Scorecard`s across walk-forward
   folds and only decides champion vs. challenger — a challenger must beat
   the champion's `expectancy` in every one of the last 3 consecutive folds
   to take over (a config constant, not tuned on data). It never touches raw
   candles, never invents a signal, and never runs if a candidate isn't
   already in the P1b library. This was the single highest-risk item in the
   phase: a ranker that re-opens free-form search on backtest results is
   exactly the overfitting failure mode P1 was restructured to prevent
   (`docs/BUILD_ORDER.md` P1 intro). Rejected: any ranker that scores
   candidates directly from price data or tunes its own parameters against
   history — that would duplicate/bypass P1b-d.

4. **Memecoin sleeve**: paper-only is enforced in *code*, not only
   `config/risk.yaml`. `risk/engine.py`'s `ModeGate` gained
   `PAPER_ONLY_SLEEVES = frozenset({"memecoin"})` and an optional `sleeve`
   kwarg on `route()` — when `sleeve == "memecoin"`, the route is forced to
   `Route.PAPER` regardless of the configured mode or any human approval
   action. `strategies/instances.py` gets `memecoin_instances()` (DOGE/USDT,
   SHIB/USDT — two names, per AGENTS.md §10 "a small memecoin sleeve") on
   the same CCXT-class spot exchange P5's crypto sleeve already uses; no DEX
   aggregator, no scraping. `tests/strategies/test_instances.py` has a test
   that proves the gate holds even if `sleeve_mode` is passed as
   `Mode.AUTO` with `human_action="approve"`. Escalating this sleeve past
   paper needs a code change plus a fresh ADR, not a config edit — a
   deliberately higher bar given §10's "paper-only until forward record
   justifies" language.

5. **Options**: NOT implemented. Per the task brief's own reasoning
   (defined-risk options still carry asymmetric payoff/margin/assignment
   risk that an equities risk engine does not model, and
   `docs/BUILD_ORDER.md` explicitly requires "dedicated learning" before any
   code), this PR only adds `docs/specs/OPTIONS_LEARNING_PLAN.md` and a
   `needs-human` handoff note. No options strategy, no options risk model,
   no Greeks code. Writing a "simple" defined-risk-only options module now
   would be the single most dangerous thing in this phase to get wrong —
   treating it as a copy of the equities path is exactly the mistake the
   brief warned against.

Consequences: four of five P8 items ship in this PR; options is explicitly
and permanently blocked behind an owner decision recorded in
`docs/decisions.md` (see the follow-up entry once the owner makes that
call) plus the learning plan. The ML ranker has no production call site yet
(same situation P6's Brain A/B harness is in per note 0039) — it is a
library the activation layer can call once P1e's real regime-gated
activation runs on real data, which is itself still gated (see STATUS.md).

---
<!-- Add new ADRs below. Template:
**ADR-00NN · YYYY-MM-DD · proposed|accepted|superseded · Title**
Context: ...
Decision: ...
Consequences: ...
-->
