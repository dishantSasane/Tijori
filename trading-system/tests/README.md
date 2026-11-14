# tests

Layout follows `docs/TESTING.md` §2. Create these folders as the corresponding components land:

`unit/`, `blind/` (written from specs by a different model than the author), `property/` (hypothesis), `equivalence/`, `lookahead/`, `backtest_known/`, `adapters/`, `failure/`, `adversarial/`, `replay/`, `fixtures/` (tiny files only).

Rules: no real network, no real orders, deterministic clock, seeded randomness. Tests needing large data are marked `slow`.
