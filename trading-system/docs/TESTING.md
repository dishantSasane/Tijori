# TESTING

Goal: leave no logic open and no cracks, as far as engineering can. No one can promise zero bugs, so we use **layers of defence** plus a **fail-closed** design: when something unexpected happens, trading stops and the owner is alerted.

Evidence behind this: studies of real retail algos show backtest scores explain very little of live results and extra tweaking widens the gap; AI-written trading code often leaks the future (e.g., a moving-average filter that includes today). So tests are first-class work, assigned to a **different model** than the author.

## 1. Principles

1. **Author != tester.** Tests for a component are written by a different model from the spec, **without seeing the implementation** ("blind tests"). Critical modules also get an Astra review.
2. **Specs first.** Every critical component has a spec (`docs/specs/`, `RISK_SPEC.md`, `STRATEGIES.md`). Tests trace to spec lines.
3. **Determinism.** Injected clock, seeded randomness, recorded data; same input -> same output.
4. **Never touch real money in tests.** Fakes/recordings/sandboxes only.
5. **Fail closed** is itself tested.

## 2. Layers

| # | Layer | What | Where |
|---|---|---|---|
| 1 | Unit tests | Pure functions: indicators, sizing, calendars, candle builder | `tests/unit/` |
| 2 | Blind tests | Written from the spec by a different model than the author | `tests/blind/` |
| 3 | Invariant/property tests | `hypothesis` for RISK_SPEC I1-I13, order state machine, candle aggregation, money math | `tests/property/` |
| 4 | Equivalence tests | Incremental indicators == batch indicators; vectorised backtester == second slow, simple reference backtester on the same data | `tests/equivalence/` |
| 5 | Look-ahead tests | Results at time t identical with or without future data; signals lagged one extra bar still show the claimed edge; truncation tests | `tests/lookahead/` |
| 6 | Known-answer backtests | Tiny hand-calculated datasets with exact expected P&L including costs and the "stop first" rule | `tests/backtest_known/` |
| 7 | Adapter contract tests | Recorded API responses; sandbox/paper endpoints; same contract suite run against every adapter and the fake | `tests/adapters/` |
| 8 | Failure injection | Dropped WebSocket, partial/duplicate/out-of-order fills, expired tokens, rate limits, market closes mid-order, process kill + restart reconciliation, clock jumps, DST/holidays | `tests/failure/` |
| 9 | Adversarial/red-team | Try to bypass risk: malformed/hostile Brain JSON, prompt injection in news text, NaN/inf/negative values, huge quantities, mode-escalation attempts | `tests/adversarial/` |
| 10 | Replay tests | A recorded market day replayed through the whole system must produce identical orders/ledger every run | `tests/replay/` |
| 11 | Mutation testing | Plant bugs in `risk` and `execution` (e.g., `mutmut`); tests must catch them | CI nightly or manual |
| 12 | Soak | Weeks of paper trading comparing live vs expected | operational |

## 3. CI gates (GitHub Actions)

On every PR: `ruff`, `ruff format --check`, `mypy`, full `pytest`. `main` is protected: PR + owner approval + green checks + reviewer comment. Coverage gate on critical modules (`risk`, `execution`, `backtest`): start at 90% line coverage and require every RISK_SPEC invariant to map to a named test (`test_invariant_I4_...`).

## 4. Backtester validation (the most error-prone component)

- Known-answer cases (hand-calculated) for: entry at next open, costs, slippage, stop-first rule, gaps through stops, partial exposure, dividends/splits adjustments.
- A second, deliberately simple, slow loop-based backtester written by a different model; results must match to the paisa on test datasets.
- Survivorship: tests assert delisted instruments appear in history and can be traded in the test universe.
- Walk-forward and out-of-sample splits are produced by library code with tests, not by hand, so nobody can accidentally tune on the hold-out.

## 5. Brain tests

- Schema validation fuzzing; budget guard enforced; provider swap works; output can only reduce size or veto.
- Prompt-injection corpus in headlines ("ignore previous instructions...") must not change behaviour.
- Brain value is **not** testable on history (training-data leakage); measure only by forward paper A/B (Brain on vs off).

## 6. Go-live gates (all must be true before any real order, in `approval` mode and tiny size)

- [ ] All invariants I1-I13 tested and passing; mutation score reviewed for `risk` and `execution`.
- [ ] Reconciliation and kill-switch drills executed on the paper broker and on the broker sandbox where available.
- [ ] Strategy instance passed all promotion gates (`STRATEGIES.md` §6) and has weeks of paper record within expectations.
- [ ] Static IP registered and verified with the order broker; keys scoped (no withdrawal for crypto).
- [ ] Independent audit of `risk` + `execution` by a model from the *other* company than the author (see `MODEL_ROLES.md`: arrange a Claude audit before first live money).
- [ ] Owner has read the lesson for risk and kill switches and has run the kill-switch drill.
- [ ] Budget caps set; alerts verified end to end (Telegram test).
- [ ] First live sizes are small enough that a total loss of the live sleeve is acceptable to the owner.

## 7. Test data

Small synthetic and recorded fixtures committed under `tests/fixtures/` (tiny files only). Large historical data stays out of git; tests that need it are marked `slow` and run locally/nightly.

## 8. Bug policy

Every bug gets a failing test first. Fixes without a regression test are rejected in review.
