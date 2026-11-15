# P1a pilot dataset manifest

Status: **pilot-complete** for the bounded five-symbol daily AND intraday
(M1/M5) datasets; see
"Remaining limitations" for what this does and does not cover. This is a
frozen description of one specific, reproducible data acquisition -- not a
claim that P1a's broader-universe objective (Top-50, point-in-time
membership) is satisfied. That remains a tracked follow-up pending a
permitted complete membership source (see `DATA_ACCESS.md` and the research
findings in `communication/`).

## 1. Source and entitlements

- Provider: Upstox V3 historical-candle API only. No automated NSE/
  NiftyIndices collection was performed or attempted.
- Credential: a fresh runtime access token, supplied interactively by the
  owner directly into `.env` (`UPSTOX_ACCESS_TOKEN`), used only for this
  collection. The token was never printed, logged, or committed; it is read
  from `.env` at runtime and discarded from memory immediately after use.
- Universe: the five bounded pilot symbols (`RELIANCE`, `INFY`, `TCS`,
  `HDFCBANK`, `ICICIBANK`), per the owner/Codex-agreed pilot scope
  (`P1_CANDIDATES.md`).

## 2. Candle collection

- **Daily (1d)**: complete, 2010-01-01 through 2026-11-14, all five symbols.
  Fetched in three resumable chunks per symbol (2010-2015, 2016-2022,
  2023-2026) to stay within Upstox's documented request bounds. Raw response
  bytes preserved exactly as returned, in `data/p1/raw/` (git-ignored, local
  only), one file + one checksum-bound manifest per request.
- **Intraday (1-minute, 5-minute)**: **complete**, January 2022 through
  2026-11-14 (the documented provider floor for minute history; no earlier
  data assumed), all five symbols, both intervals -- 590 of 590 expected
  (symbol x timeframe x month) chunks present (5 symbols x 2 timeframes x
  59 months), month-chunked and resumable via `collect_pilot_intraday`
  (Codex) and, for the chunks that function could not survive,
  `p1_resilient_intraday_fetch` (this module -- see §3). All 590 response
  checksums independently re-verified before hashing (below).

### Candle snapshot identity (daily)

Computed via `candle_snapshot.candle_snapshot_sha256` (Codex) over all 15
daily response manifests (5 symbols x 3 chunks), which re-verifies every
response's checksum before hashing:

```
timeframe: 1d
window: 2010-01-01 to 2026-11-14
candle_snapshot_sha256: 74d334595083e445c1c1301293abc03884d27bc5d91604d8bb7514b87cf80942
```

### Candle snapshot identity (intraday)

Computed the same way (sorted bundle of request/response identity records,
hashed after independently re-verifying every checksum), over all 590
M1/M5 response manifests:

```
timeframes: 1m, 5m
window: 2022-01-01 to 2026-11-14
records: 590 (5 symbols x 2 timeframes x 59 months)
intraday_candle_snapshot_sha256: b10ef77572a455c9dcccc45abf5ae421a39a03a8cd2291e0ce039a97aa86b1c0
```

Both hashes change if any symbol's raw response, request window, or parser
version changes -- they are each series' tamper-evident identity. The combined
evaluation manifest now binds these candle identities to the action-register
and calendar hashes (candle identity and action coverage identity are
deliberately separate hashes -- see
`communication/2026-11-15-codex-snapshot-hash-clarification.md` -- avoiding
a circular dependency between the two).

### Combined evaluation manifest identity

Generated offline with
`PYTHONPATH=src .venv/bin/python -m trading.storage.freeze_p1a_manifest --reviewed-on 2026-11-16`.
The canonical action register includes the observed provider action records
and explicit per-symbol/timeframe coverage rows. Its hash and the complete
manifest hash are:

```
action_register_sha256: f0abc42ed748a87d444431193a3a9c9322ca5b263ae082b580ba031a1949256b
evaluation_manifest_sha256: aa1c0a786f78cf321c2fb4f042413d0c47c276e74063b45dfb8944ce58e60e55
artifact: docs/specs/P1A_EVALUATION_MANIFEST.json
```

The artifact explicitly records `action_coverage_status: unverified`. This
closes the manifest-assembly/hash deliverable; it does not claim complete
historical corporate-action coverage. The backtest action preflight remains
fail-closed and real-data replay is not cleared by this manifest alone.

## 3. Known data-quality defect and its resolution

Four malformed rows were found across the full intraday backfill, all four
in the same month (June 2024) -- suggesting a provider-side feed anomaly on
that specific window rather than a symbol-specific defect:

| Symbol | Timeframe | Bar | Defect |
|---|---|---|---|
| HDFCBANK | 1m | 2024-06-25T09:15:00+05:30 | `open` (835.6) below `low` (837.4) |
| ICICIBANK | 1m | June 2024 chunk | same class of invalid OHLC |
| HDFCBANK | 5m | June 2024 chunk | same class of invalid OHLC |
| ICICIBANK | 5m | June 2024 chunk | same class of invalid OHLC |

These are provider data defects, not parsing bugs. Each is excluded from its
parsed candle series for that one bar and recorded explicitly in that
chunk's manifest `skipped_rows` field -- never silently dropped or clamped.
`p1_resilient_intraday_fetch.py` was built specifically so a bad row doesn't
lose an entire chunk's raw evidence or halt the resumable collection run; it
proved itself across the real backfill, not just HDFCBANK's first occurrence.

## 4. Session-coverage audit (calendar)

`p1_pilot_coverage.audit_session_coverage`, run against the complete daily
dataset (2010-01-01 to 2026-11-14), all five symbols:

- **4,172 common sessions** -- every date all five symbols traded on. This
  is the verified, cross-confirmed daily calendar for this pilot and window,
  and the only session set safe to use for synchronized multi-symbol
  portfolio-return construction (P1_EVALUATION.md's "one value per verified
  exchange session").
- **RELIANCE has 13 extra dates**, not shared by the other four. All 13 are
  now resolved, not merely flagged:
  - **8 are Saturdays** (2010-02-06, 2012-01-07, 2012-03-03, 2012-04-28,
    2012-09-08, 2013-05-11, 2014-03-22, 2015-02-28) -- consistent with NSE's
    historically-documented practice of periodic special/test Saturday live
    trading sessions.
  - **5 are confirmed Diwali Muhurat trading sessions** (2011-10-26,
    2013-11-03, 2016-10-30, 2017-10-19, 2018-11-07) -- each date matches the
    publicly known Diwali Lakshmi Puja date for that year exactly (verified
    independently per year, not inferred from the pattern alone). NSE holds
    a short special Muhurat session every Diwali regardless of weekday.
  - **No unexplained dates remain.**
- **Decision**: use the 4,172-session common set as the verified daily
  calendar for any cross-symbol calculation (portfolio returns, the
  bootstrap's "one value per session" vector, Pareto comparisons). RELIANCE's
  13 extra sessions stay in RELIANCE's own standalone series -- excluded
  only from calculations that require all five symbols synchronized, per
  the fail-closed principle of flagging rather than silently merging.

## 5. Adjustment basis (price)

No formal per-event `ActionRegister` entries exist for these five symbols
(nothing to register -- see below), but the price series was independently
screened for split/bonus-scale discontinuities:

- Overnight-return screen across the full 2010-2026 daily series, all five
  symbols: **zero discontinuities** matching a split/bonus ratio pattern
  (checked at both a 35% and a 15% overnight-move threshold).
- Three large moves were flagged at the 15% threshold and independently
  verified as **not** corporate actions: INFY 2013-04-12 (~21% drop, the
  widely-reported Q4 FY13 earnings-disappointment crash), INFY 2019-10-22
  (~16% drop, the Infosys whistleblower-complaint crash), ICICIBANK
  2020-03-23 (~18% drop, the global COVID-19 market crash). All three are
  real, publicly documented market-news events, not actions.
- **Positive confirmation**: TCS's real 1:1 bonus issue (record date
  2018-06-02) produced **zero price discontinuity** around its ex-date in
  this series (price continuous ~1740-1800 through 2018-05-28 to 2018-06-08)
  -- a 1:1 bonus would halve an unadjusted price. This directly confirms
  Upstox's daily OHLC for TCS is adjusted through this known real event, not
  merely free of detected gaps by coincidence.
- **Working conclusion**: Upstox's daily OHLC for these five pilot symbols
  is **provider-adjusted** for splits/bonuses, consistent with the earlier
  independent NESTLEIND finding (`BUILD_ORDER.md`, note 0031). `price_basis`
  for this dataset: `provider_adjusted` (empirically determined, not
  assumed).
- **Volume basis: still unverified** -- the screen above only checked price
  continuity. A bonus/split typically also moves volume inversely; this
  dataset does not yet confirm volume is adjusted consistently. Flagged as
  a remaining limitation, not claimed.

## 6. Position/share-count replay

No split/bonus event needs replay handling for this dataset: §5 found none
to replay. The existing fail-closed design (`action_preflight.py`: any
split/bonus notice inside a replay window unconditionally blocks that
replay, regardless of any `handled_action_keys`) remains the correct
behavior if a future window (e.g. extending past 2026, or a different
symbol) does contain one -- this manifest does not relax that gate.

## 7. Remaining limitations (explicit, not silently left open)

- **Volume-basis unverified** (§5) -- price confirmed provider-adjusted;
  volume is not.
- **Intraday adjustment basis not separately checked** -- §5's screen used
  only daily data. If an intraday candidate's window ever needs to cross a
  real corporate-action date, this must be re-verified for the 1m/5m series
  specifically before that replay runs.
- **Top-50 point-in-time universe remains unresolved** -- this manifest
  covers only the five-symbol pilot, by explicit, documented scope decision
  (`communication/2026-11-15-claude-unblock-p1a-proposal.md`,
  `2026-11-15-codex-reply-pilot-scope.md`). Not a silent substitution.
- **Action coverage remains unverified.** The combined manifest binds the
  current action-register snapshot, but available Upstox evidence does not
  establish complete historical action coverage for every symbol/window.
  Keep action preflight fail-closed and do not interpret the hash as coverage
  certification.
