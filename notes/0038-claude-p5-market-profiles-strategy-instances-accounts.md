# 0038 — Claude: P5 market profiles, crypto/US strategy instances, Accounts page v1

Status: needs-human (one item below), otherwise ready for cross-model review.

## What I did
Picked up P5 (`docs/BUILD_ORDER.md`) where `claude/sleeve-allocation-and-adapters`
(PR #54, data-layer-only per note 0032) left off. Branch
`claude/p5-crypto-us-sleeves`, based on `origin/claude/sleeve-allocation-and-adapters`
(not `main` — PR #54 isn't merged yet; see base note in the PR body), PR
**#58**: https://github.com/dishantSasane/Tijori/pull/58

- `src/trading/core/market_profile.py`: `MarketProfile` keyed on the existing
  `MarketId` enum (no parallel concept), loaded from `config/markets.yaml`.
  `is_24x7` is the load-bearing field — it's how crypto tells callers it has
  no exchange session, so nothing wrongly assumes the India-equity session
  scheduler (`candles/scheduler.py`) applies to it.
- `src/trading/strategies/instances.py`: configures the existing T1
  (`t1_donchian`) and T4 (`t4_rsi_pullback`) rules from `phase1.py` against
  crypto (BTC/USDT, ETH/USDT) and US (AAPL, MSFT, QQQ) Tier A. **T2 and a
  dedicated "momentum" rule are not on `main` anywhere** — they're in the
  strategy library on open, unmerged PR #53 (`codex/p1-build`). I scoped
  down rather than block or re-derive new strategy math that would diverge
  from #53 — same call the P4 agent made for its ranking placeholder (note
  0037). `STRATEGY_ID -> callable` in `instances.py` is the extension point
  for whoever finishes #53.
- `src/trading/reporting/accounts.py` + `dashboard/pages/4_Accounts.py`:
  read-only per-sleeve balances (starting capital from
  `risk.yaml`'s `allocation_pct`, cost basis locked in open paper positions,
  capital available) over the paper broker's existing SQLite `positions`
  table. **Not a P&L statement** — `fills` doesn't record buy/sell side per
  fill, so a signed realized-P&L series isn't reliably derivable from what's
  stored today; building a real trade ledger felt like scope creep past
  "balances, read-only, v1." Flagging this as a real P6/P7-ish gap: whoever
  eventually wants performance reporting (Sharpe, win rate, equity curve)
  will need PaperBroker to record fill side, or a separate ledger table.
- `dashboard/` doesn't exist on `main` or on `claude/sleeve-allocation-and-adapters`
  yet — PR #56 (P3) and PR #57 (P4) each add their own `dashboard/` tree,
  both open. I wrote this page standalone (doesn't import either PR's
  helpers) to avoid depending on an unmerged layout, but this is now a
  **third** parallel `dashboard/` addition. Whichever of #56/#57/#58 merges
  first should absorb the other two pages into one app — don't let this
  rot into three permanently-separate dashboards.
- Funding-rate (perp) ingestion: deferred outright, documented in
  ADR-0033. The crypto sleeve here is spot paper trading only; nothing
  consumes funding data yet, so building the ingestion now would be unused
  plumbing (AGENTS.md §6 "small modules"/YAGNI).
- ADR-0033 in `docs/decisions.md`; lesson
  `docs/learn/04-market-profiles-and-24x7-crypto.md` (what a market profile
  is, why crypto breaks a session-based scheduler's assumptions).

## Checks
43/43 tests pass locally (11 new), `ruff check` + `ruff format --check`
clean, `mypy` clean on the three new source modules. No risk/execution/broker
code touched — cross-model review welcome per AGENTS.md §5 but not strictly
mandatory for this PR's module set.

## needs-human
Which crypto exchange/account the owner actually wants for paper trading.
`claude/sleeve-allocation-and-adapters` picked Binance's free public
endpoints for market *data* (reasonable, free-first). But CCXT supports
many exchanges, and *order routing* (even paper) will eventually need to
pick one real account/sandbox to shadow. Don't let a later agent default to
"whatever Binance's sandbox does" without the owner explicitly choosing it
— crypto exchange choice has real tax/compliance weight for an Indian
resident per AGENTS.md §10/`docs/COMPLIANCE_INDIA.md`, which is the owner's
call with a CA, not an agent's.

## Next
- Owner/Codex: decide merge order for #54/#56/#57/#58 (data adapters,
  P3 dashboard, P4 dashboard, P5 dashboard+strategy-instances) — all four
  are open and some touch overlapping ground (`dashboard/`).
- Whoever picks up P5 further: wire `instances.py`'s instances into an
  actual live-paper loop (candle feed -> signal -> risk engine -> paper
  broker) the way P3's intent was for India — this PR only configures the
  instances, it doesn't run them yet (same "data/config exists, execution
  wiring open" shape as #54 itself).
