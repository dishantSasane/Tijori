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

Rule: if code and spec disagree, the spec is right until a PR changes both.
