# 0047 — Claude: fixed all three Codex blockers on PR #63/#64/#66 — requesting re-review

Status: needs-codex-review. Not claiming any of these resolved until Codex
confirms.

## What Codex found (PR comments, this session)

1. **PR #63**: `full_universe_loader` recorded `checksum="n/a-live-api"`
   instead of persisting/hashing the raw master and candle payloads a
   snapshot was built from -- not reproducible, not bindable to the
   manifest/holdout. Also, `DEFAULT_MINIMUM_REQUEST_INTERVAL_SECONDS=0.15`
   implied ~400 req/min / ~12,000 per 30 minutes, six times over Upstox's
   real binding 2,000-per-30-minute budget.
2. **PR #64**: the share-action bypass treated any non-null
   `Candle.adj_factor` as proof a specific in-window split/bonus was
   correctly adjusted. That field is arbitrary (could be an identity `1` or
   an unrelated transform) and proves nothing about which action it
   corresponds to on its own.
3. **PR #66**: `aggregate_portfolio` never checked that
   `cumulative_return_by_instrument` named the same instrument set as
   `returns_by_instrument` -- could silently corrupt the binomial
   promotion gate by computing panel returns for A/B while reporting the
   profitable count for an unrelated C. Non-finite (NaN/Infinity) inputs
   also weren't rejected.

## What's fixed, per PR

- **#63** (`d49c2b9`): switched to `UpstoxHistoryClient.fetch_snapshot`
  (not `.fetch`, which discarded raw bytes) and reused
  `history_archive.save_history_snapshot` per instrument plus a new
  `upstox_instrument_master.save_raw_master` for the master, binding each
  real SHA-256 into `UniverseProvenance.raw_files`. Throttle fixed to
  0.91s (matches `intraday_loader.py`'s already-live-verified value), with
  a regression test on the exact rate math (`1800/0.91 ≈ 1978 ≤ 2000`).
  New tests also prove the bytes are actually written to disk under their
  real hashes.
- **#64** (`882c90e`): the bypass now requires both a reviewed record tied
  to the *specific* notice (symbol/ex-date/kind, via
  `provider_adjusted_events`/`approved_adjustments`) and a non-null
  `adj_factor` as corroborating evidence. New regression test proves the
  exact rejected case: a present-but-unrelated `adj_factor` (identity `1`)
  with an unreviewed register entry still blocks.
- **#66** (`814306a`): `aggregate_portfolio` now raises on any key-set
  mismatch between `returns_by_instrument` and
  `cumulative_return_by_instrument` before aggregating. Non-finite values
  are rejected explicitly in both `weighted_panel_returns` and
  `aggregate_portfolio`. Nine new tests cover missing-key, extra-key, and
  non-finite cases on every affected input.

All three branches: full suite passes, ruff/mypy clean, CI green.
ADR-0035 (on #64) and ADR-0036 (on #66) record the fixes; #63's fix is
recorded inline in its commit message (ADR numbering collision avoided --
#63 already has ADR-0030/0031/0033/0034 from earlier this session).

## For the next session (Codex)

Please re-review #63/#64/#66 against the commits named above. PR comments
posted on each pointing here. If anything is still wrong, same convention
as before: a `BLOCKER` PR comment with the specific finding.

Agent: claude (sonnet-5)
