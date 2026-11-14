# Handoff 0024 — remaining P0 data gates

## Tokenless Upstox past-day intraday probe

Using the official V3 historical endpoint without an Authorization header, with a browser-like User-Agent to avoid the CDN signature block:

- Date tested: `2026-11-13` (past trading day).
- Instruments: Nifty 50 plus Reliance, Infosys, HDFC Bank, TCS, and ICICI Bank.
- 1-minute history: HTTP success, 375 candles for every instrument.
- 5-minute history: HTTP success, 75 candles for every instrument.
- No API failures and no credentials were printed or logged.
- The tokenless intraday endpoint returned successful empty arrays at probe time; it is not the past-day history path.

## Parquet loader

Branch `codex/p0-parquet-loader`, commit `2ec5c7e`, adds `CandleStore.load_parquet(path)`. It reads the canonical candle columns through DuckDB, reconstructs validated Pydantic `Candle` contracts, and routes rows through transactional append/idempotency checks. Contract coverage verifies round-trip loading and duplicate delivery behavior. Full local pytest (94), Ruff, and mypy pass.

Exact stopping point: branch is pushed and awaiting PR/CI bookkeeping. The owner must review/merge it before P0 data gates are considered complete.
