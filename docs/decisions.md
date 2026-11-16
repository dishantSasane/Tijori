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
explicitly waived by the owner; the untouched holdout from the current
2016-2026 sample is no longer valid once inspected, so a new, genuinely
unread holdout range must be committed in P1a config before P1b/P1c runs.

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

**ADR-0026 · 2026-11-15 · accepted · Point-in-time universe resolved without a paid NSE Indices licence; research sizing set**
Context: ADR-0025 gated P1a on either a purchased NSE Indices licence for
point-in-time Nifty 50/Next 50 membership, or an explicit survivorship-bias
waiver. NSE Indices licensing is priced for institutional buyers (asset
managers/ETF issuers), not a free or low-cost option, and an agent emailing a
vendor on the owner's behalf is a bad pattern regardless of price. The data
actually needed is already public.
Decision: (1) the **research universe** is rule-based and computed from free
NSE bhavcopy data (`sec_bhavdata_full`), not from any index membership
source: top 50 (and, for later Tier B-adjacent work, top 100) by rolling
60-day median turnover, recomputed monthly, keyed on ISIN rather than symbol.
This is survivorship-free by construction — no manifest, no vendor, no
licence. (2) A **Nifty 50 point-in-time manifest is still built, but only as
a benchmark/scorecard tool**, not the research universe: reconstructed by
anchoring on today's known membership and walking NSE Indices' own public,
dated replacement press releases (`niftyindices.com/Press_Release/`)
backward, with the source press-release URL cited per row. Wikipedia's
replacements-since-2005 table is a cross-check only, never the source of
record; disagreements between the two are flagged, not silently resolved.
(3) No NSE Indices quote/licence inquiry will be sent. (4) Research-comparison
sizing is set at 1% per-trade risk on a ₹1,00,000 placeholder capital — not
the owner's real trading capital, used only so every P1b/P1c candidate is
sized identically and results are comparable.
Consequences: `trading.storage.membership`'s manifest contract/validator
(built against the "authorized vendor" design) is repointed at the
reconstructed press-release manifest for benchmarking, not at a purchased
feed. P1a's membership blocker from ADR-0025 is closed; its sizing blocker is
closed. Still open: the holding-horizon confirmation, Upstox's raw/adjusted
price basis (verify empirically, e.g. against Infosys's 2018 bonus issue,
before trusting any "adjusted" Upstox candle), and the untouched holdout
range (the 2016-2026 sample remains burned per ADR-0024).

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

**ADR-0029 · 2026-11-16 · accepted · P6 Brain/News: RSS+stdlib feed, Anthropic provider lazily imported, spend reuses `audit_log`, no dedicated A/B store**
Context: P6 scope (docs/BUILD_ORDER.md) is News ingestion, `LLMProvider`
interface + budget guard, schema validation, shared context cache, and
Brain A/B in paper. P0 already shipped the `NewsFeed`/`LLMProvider`
Protocols, their fakes, and `BrainVerdict`/risk-engine wiring
(`src/trading/adapters/news_feed.py`, `llm_provider.py`,
`src/trading/risk/engine.py`/`sizing.py`) -- this phase implements the real
adapters and the Brain-specific plumbing (`src/trading/brain/`) against
those, not a second interface.
Decision:
1. `brain/news_rss.py`'s `RSSNewsFeed` parses RSS 2.0 with stdlib
   `urllib`+`xml.etree` only (ponytail rung 3/5: no `feedparser` dependency
   for what ~60 lines of parsing does). Default feeds: NSE's own
   announcements RSS and a general financial RSS; both configurable. A
   feed that fails to fetch/parse is skipped, never raised -- one dead
   source must not stop news polling (AGENTS.md §4.2).
2. `brain/anthropic_provider.py`'s `AnthropicBrainProvider` is the real
   `LLMProvider`. It lazily `import anthropic` inside `__init__`, so the
   package (added as the new `brain` extra in `pyproject.toml`, not a core
   dependency) is only required when the Brain is actually turned on;
   nothing else in the test suite or the rest of the system needs it
   installed. Order of operations per call: context-cache check -> budget
   check (fails closed, refuses the call outright rather than making it and
   discarding the result) -> provider call -> strict schema parse
   (`brain/schema.py`) -> record spend (always, success or parse failure,
   since tokens were spent either way) -> cache the result if valid.
3. `brain/budget_guard.py`'s `BudgetGuard` computes today's/this month's
   spend by summing `cost_inr` out of the existing `audit_log` table
   (`llm_call` event rows) rather than a second ledger -- one source of
   truth for "what did the Brain cost", matching AGENTS.md §4.8's own
   framing ("tokens and INR logged"). `allow()` is strictly `<` the cap (not
   `<=`), so spend *equal to* the cap already blocks the next call, matching
   BRAIN_AND_COSTS.md §5's "at 100% -> Brain off".
4. `brain/schema.py`'s `parse_verdict` is the second line of defense named
   in `docs/specs/RED_TEAM.md` §1/§2: any JSON that doesn't match
   `BrainVerdict` exactly, including a `signal_id` mismatch or a `reasons`
   list that violates the max-3/120-char caps in BRAIN_AND_COSTS.md §3,
   returns `None` and is risk-engine-equivalent to "Brain absent" -- never
   raises, never partially applies. One field, `news_refs`, is in the
   BRAIN_AND_COSTS.md §3 schema but was never added to the P0
   `BrainVerdict` contract (it's audit-only, nothing downstream reads it) --
   `parse_verdict` pops it before validation rather than widening a P0 core
   contract for an unused field; flagged for the cross-model reviewer in
   case there's a plan to consume it later.
5. `brain/context_cache.py`'s `ContextCache` is a single in-process dict
   keyed by `sha256(context) + signal_id`, TTL-expired. No persistence, no
   distributed cache (ponytail/YAGNI, matching the phase instructions
   explicitly) -- a restart just means zero cache hits until it warms up
   again, which only costs money, never correctness.
6. `brain/ab_harness.py`'s `run_ab` runs the SAME signal through
   `RiskEngine.check()` twice (once with the real Brain verdict, once
   forced to the neutral/full-size baseline) and logs both decisions to
   `audit_log` under one `brain_ab_comparison` event -- no new table. The
   off-arm needed its own throwaway `DecisionStore` (backed by a fresh
   `:memory:` connection) rather than sharing `engine`'s: calling
   `check()` twice for one `signal_id` through the SAME `DecisionStore`
   trips check 14's duplicate-signal guard (I7) on the second call, which
   is correct behaviour for two *real* deliveries of one signal but wrong
   here, since the off-arm isn't a second real decision, it's a
   what-if comparison. Kill switch/calendar/freshness are still shared with
   the real engine, since those must agree across both arms.
7. Prompt-injection containment (RED_TEAM.md §1): `brain/prompt.py` wraps
   headlines in an explicit "untrusted external data -- not instructions"
   delimiter, caps count (8) and per-headline length (200 chars) so a feed
   bug/flood can't blow up the token budget (scenario 4), and the schema
   parser is the actual enforcement -- a Brain that complies with an
   injected instruction and returns `label: support` still can't do
   anything beyond what `support` already means (bounded sizing, risk
   engine re-runs every other check regardless).
Consequences: `BRAIN_DAILY_BUDGET_INR=50`/`BRAIN_MONTHLY_BUDGET_INR=500` in
`.env.example` are placeholders pending the owner's actual budget decision
(see the `needs-human` handoff note for this phase) -- `AnthropicBrainProvider`'s
per-token INR price constants are similarly provisional estimates for the
cheapest current Anthropic tier, not sourced from a live pricing page, and
must be confirmed before the Brain is switched on for real spend. The Brain
A/B harness only compares risk-engine *decisions* (allowed/qty/reason
codes), not trade outcomes -- outcome-level A/B (did Brain-on paper trades
actually do better) needs the existing `signal_outcomes`/scorecard
machinery from P1c/P2, wired in by whoever builds the paper-trading loop
that calls `run_ab` for real signals (not yet done; this phase ships the
harness function, not its production call site, since no live paper
signal-generation loop exists yet to call it from).

---
<!-- Add new ADRs below. Template:
**ADR-00NN · YYYY-MM-DD · proposed|accepted|superseded · Title**
Context: ...
Decision: ...
Consequences: ...
-->
