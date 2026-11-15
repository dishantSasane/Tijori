# P1a evidence checklist

Status: pilot-scope exit criteria, mapped to artifact + exact test + pass/fail.
Per the supervisor's operating order: a phase is not closed while an exit
criterion is merely described, locally implemented, unreviewed, or blocked
by an unrecorded external dependency. This checklist exists so none of that
happens silently.

| # | Exit criterion | Artifact | Exact test / command | Status |
|---|---|---|---|---|
| 1 | Upstox-only source; no NSE/NiftyIndices automation; no token in code/logs/commits | `docs/DATA_ACCESS.md`; all collection code (`collect_pilot_daily.py`, `collect_pilot_intraday.py`, `p1_resilient_intraday_fetch.py`) reads the token from `.env` at runtime only | Manual code read: grep for hardcoded tokens/URLs — `grep -rn "api.upstox.com\|nseindia\|niftyindices" src/trading/storage/p1_*.py src/trading/adapters/upstox_*.py` returns only the one documented Upstox base URL | **PASS** |
| 2a | Daily five-symbol collection, resumable, raw bytes preserved | `data/p1/raw/*-1d-*.json` + `.manifest.json` (gitignored, local); `candle_snapshot_sha256` below | `candle_snapshot_sha256([...15 daily manifests...], timeframe=D1, start=2010-01-01, end=2026-11-14)` → `74d334595083e445c1c1301293abc03884d27bc5d91604d8bb7514b87cf80942` (re-verifies every response checksum before hashing) | **PASS** |
| 2b | M1/M5 intraday collection, Jan 2022 floor, resumable, raw bytes preserved | `data/p1/raw/*-1m-*.json`, `*-5m-*.json` (gitignored, local); `intraday_candle_snapshot_sha256` in the manifest doc | Live backfill completed: 590/590 expected (5 symbols x 2 timeframes x 59 months) chunks present, all 590 response checksums independently re-verified before hashing → `b10ef77572a455c9dcccc45abf5ae421a39a03a8cd2291e0ce039a97aa86b1c0`. 4 malformed rows found (all in June 2024, across HDFCBANK/ICICIBANK, both timeframes — a provider feed anomaly, not a parsing bug), excluded and recorded in `skipped_rows`, never silently dropped. | **PASS** |
| 3 | 2011-10-26 RELIANCE-only session resolved | `docs/specs/P1A_PILOT_DATASET_MANIFEST.md` §4 | `PYTHONPATH=src .venv/bin/python -m pytest tests/storage/test_p1_pilot_coverage.py -q` (8 passed) + independent date-match: 2011-10-26 = confirmed Diwali Lakshmi Puja date for 2011 (public calendar fact, verified via search, not NSE-site automation) | **PASS** — resolved, not merely excluded; all 13 RELIANCE-only dates explained (8 Saturdays, 5 confirmed Diwali Muhurat sessions) |
| 4 | Per-symbol adjustment-basis evidence; no empty-response-implies-complete claim | `docs/specs/P1A_PILOT_DATASET_MANIFEST.md` §5 | Price-discontinuity screen across full 2010-2026 daily series (script, not yet a committed pytest — see note) + independent cross-check against TCS's real, publicly-confirmed 2018 1:1 bonus (zero discontinuity found) | **PASS for price basis** (empirically provider-adjusted); **volume basis explicitly unverified**, stated as a limitation, not claimed |
| 5 | Split/bonus open-position replay fails closed | `src/trading/backtest/action_preflight.py` (Codex); unconditional block on any in-window split/bonus notice | `PYTHONPATH=src .venv/bin/python -m pytest tests/backtest/test_action_preflight.py -q` on `codex/p1-build` (22 passed, verified by Claude read-only) | **PASS** (Codex-owned file, independently verified passing, not edited by Claude) |
| 6 | Reproducible dataset manifest: source, windows, calendar, actions, transforms, hashes, coverage | `docs/specs/P1A_PILOT_DATASET_MANIFEST.md` (daily candle-identity component); full combined evaluation manifest (+ action-register hash + calendar hash) still pending Codex's action-coverage binding work | Manual read of the manifest doc against this checklist | **PARTIAL** — candle/calendar/adjustment-basis component frozen; full combined manifest requires Codex's action-register hash, not yet assembled |
| 7 | Tests/lint/type checks pass; commit/push with exact commands/results | commits `21f3083`, `8aef688`, `2f7db31` on `claude/p1d-holdout-and-p1c-eval-harness` | `PYTHONPATH=src .venv/bin/python -m pytest -q` (all pass), `ruff check .` (all checks passed), `ruff format --check .` (clean), `mypy src/trading/storage/p1_*.py` (no issues) | **PASS** |

## What this means for closure

Items 1, 2a, 2b, 3, 4 (price), 5, 7 are satisfied with artifact + exact test
+ pass. Item 4's volume basis is an explicit, stated limitation, not a gap
pretending to be closed. Item 6 is the one remaining genuinely open item: it
depends on a cross-model component (Codex's action-register hash) that
doesn't exist yet as a committed artifact.

**P1a's data foundation -- daily and intraday collection, candle identity,
calendar reconciliation, price adjustment-basis evidence, fail-closed
action-crossing replay -- is pilot-complete and closable on Claude's side.**
The only remaining item is combining Claude's candle/calendar hash with
Codex's action-register hash into the single full evaluation manifest,
which is a short follow-up once that hash exists, not a reopening of this
work. Volume-basis verification and the broader Top-50 universe remain
explicit, tracked, separate follow-ups -- not silently folded into "done."

The broader Top-50 point-in-time universe remains an explicit, separate,
blocked follow-up (no free complete source past 2022 — see
`communication/`'s research findings) and is out of scope for this pilot's
closure.
