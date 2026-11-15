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

**ADR-0028 · 2026-11-16 · proposed · P2: risk engine, paper broker, kill switch implementation choices**
Context: Implementing P2 (`docs/BUILD_ORDER.md`) against the already-written
`docs/specs/RISK_ENGINE_SPEC.md`, `PAPER_BROKER_SPEC.md`, `TELEGRAM_ALERT_SPEC.md`,
and `TEST_SPEC_RISK.md`. A few things those specs leave as implementation
judgment calls, resolved here:
Decision: (1) `PortfolioState`/`RiskConfig`/`SleeveConfig`/`InstanceState`
(`src/trading/risk/config.py`) are plain Pydantic `BaseModel`s, not frozen
`Contract`s from `core/models.py` — they are the risk engine's own runtime
input, not a cross-module fact, matching RISK_ENGINE_SPEC.md §1's framing.
(2) Check 17 ("no open position already occupies this symbol slot") uses the
newly-appended `ReasonCode.CONCURRENT_POSITION_EXISTS` per RISK_ENGINE_SPEC.md
§9.3, placed between checks 12 and 13 to match RISK_SPEC.md's own numbering
(the spec's check-order table stops at 16 and treats 17 as an addendum).
(3) `RiskEngine.check()`'s market-session and data-freshness dependencies are
small `Protocol`-like dataclasses (`MarketSession`, `DataFreshnessCheck`)
rather than importing a real calendar library yet — no real adapter exists
to wire them to, and a fake lambda is enough for every test in
`TEST_SPEC_RISK.md`; wiring a real `exchange_calendars` adapter is P3+ work,
not blocking P2. (4) The paper broker's SQLite layer (`StateStore`) is one
hand-written file with plain SQL, not an ORM — the schema in
`PAPER_BROKER_SPEC.md` §4 already *is* the contract; an ORM would just be a
second description of the same seven tables to keep in sync (YAGNI). (5) The
kill-switch drill (`tests/execution/test_kill_switch_drill.py`) is a single
long-form test that runs all six steps from `PAPER_BROKER_SPEC.md` §6 against
a real `StateStore`/`KillSwitch`/`PaperBroker`, including a real restart
(construct a second `StateStore` against the same file) — not a mocked
restart — because the exit criterion explicitly asks for "a real demonstrated
run," not a unit test of one function. (6) The Telegram wiring
(`src/trading/adapters/telegram_alert.py`) ships the `TelegramAlerts` Protocol,
a `FakeTelegramAlerts` with zero network code, and the `telegram_decisions`
state machine from `TELEGRAM_ALERT_SPEC.md` §2/§4 — the real
`python-telegram-bot` adapter (reading `TELEGRAM_BOT_TOKEN` from `.env`) is
left for the next session, since nothing in the P2 exit criteria requires a
live bot token to exist, and AGENTS.md §4.4 forbids tests that could touch a
real network service anyway.
Consequences: Codex (or the next Claude session) can wire a real
`python-telegram-bot` adapter behind `TelegramAlerts` without touching the
state machine or risk engine. The real calendar/session adapter
(`exchange_calendars`) and the pre-market batch scheduler
(`TELEGRAM_ALERT_SPEC.md` §3) are explicitly not built yet — flagged in the
handoff note, not silently assumed done. This PR is authored solely by
Claude; per AGENTS.md §5, cross-model review (Codex/Astra) on `risk` and
`execution` is still required before the owner merges.

---
<!-- Add new ADRs below. Template:
**ADR-00NN · YYYY-MM-DD · proposed|accepted|superseded · Title**
Context: ...
Decision: ...
Consequences: ...
-->
