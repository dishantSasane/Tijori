# docs/specs

Detailed, implementable specs. Written by Claude during the P0 Foundation Sprint (`docs/BUILD_ORDER.md`), extended by whoever changes the behaviour. A spec is the contract that blind tests are written from, so keep it precise, with examples and numbers.

| File | Owner (P0) | Purpose |
|---|---|---|
| `CONTRACTS.md` | Claude Opus | Fields, types, invariants of every cross-module model (`Candle`, `Signal`, `OrderRequest`, `Order`, `Fill`, `Position`, `RiskDecision`, `BrainVerdict`, `SignalOutcome`, `AuditEvent`) |
| `ADAPTERS.md` | Claude Opus | `DataFeed`, `Broker`, `NewsFeed`, `LLMProvider` protocols; error model; contract-test suite |
| `RISK_ENGINE_SPEC.md` | Claude Fable | Check order, reason-code catalogue, order and kill-switch state machines, edge cases (extends `docs/RISK_SPEC.md`) |
| `RED_TEAM.md` | Claude Fable | Adversarial scenarios and prompt-injection corpus |
| `TEST_SPEC_RISK.md`, `TEST_SPEC_BACKTEST.md`, `TEST_SPEC_CANDLES.md`, `TEST_SPEC_ADAPTERS.md`, `TEST_SPEC_STRATEGIES.md` | Claude Opus | What must be tested, with hand-calculated known-answer cases |
| `STRATEGY_SPEC.md` | Claude Sonnet | Pseudo-code and test vectors for T1-T6 and F1 |
| `DATA_SOURCES.md` | Codex (Terra/Luna) | Verified data sources, URL formats, limits, terms (official docs only) |
| `PAPER_BROKER_SPEC.md` | Claude Sonnet (P2) | Live fill model (vs. backtest's stored-array model), SQLite state schema backing I12, outcome tracker for shadow/rejected signals, kill-switch drill procedure |

P1/P2/P3 additions (written ahead of each phase's implementation, same discipline):

| File | Owner | Purpose |
|---|---|---|
| `CORPORATE_ACTIONS.md`, `INDEX_MEMBERSHIP.md`, `RESEARCH_UNIVERSE.md` | Codex | Point-in-time universe and corporate-action contracts (P1) |
| `PAPER_BROKER_SPEC.md` | Claude Sonnet | Live fill model, SQLite state/restart, outcome tracker, kill-switch drill (P2) |
| `TELEGRAM_ALERT_SPEC.md` | Claude Sonnet | Per-signal approve/paper-test/reject state machine, pre-market batch wiring, concurrency (P2; extends `PAGES.md` §2, `RISK_SPEC.md` §2A) |
| `CANDLE_BUILDER_AND_SCHEDULER_SPEC.md` | Claude Sonnet | Live tick->candle builder internals, multi-timeframe derivation, market-session state machine (P3; extends `ADAPTERS.md` §1) |

Rule: if code and spec disagree, the spec is right until a PR changes both.
