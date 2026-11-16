"""The Brain: optional, advisory LLM layer (docs/BRAIN_AND_COSTS.md).

Never in the hot path, never places orders. `RiskEngine` already treats a
missing/invalid `BrainVerdict` as neutral/full-size (AGENTS.md §4.6,
`trading.risk.engine.default_absent_verdict`) — everything here only
produces a `BrainVerdict | None` for that existing contract, it does not
re-implement the fail-closed logic.
"""
