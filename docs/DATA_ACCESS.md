# DATA_ACCESS.md — who fetches what, and how

Standing policy for every agent (Claude, Codex) working in this repo. If a
data-fetching change doesn't fit one of the three paths below, stop and write
a handoff note (`needs-human`) instead of inventing a fourth path.

## 1. Default: agents fetch public data themselves

If a source is reachable without logging in as the owner — a public REST
endpoint, a public bulk-download file, a documented free API that only needs
a self-service API key an agent can request on the owner's behalf — the
agent fetches it directly. No owner involvement needed to run the code.

Examples already in this repo: Binance's public `/api/v3/klines` (no key at
all), Alpaca's free Basic/IEX market-data REST (needs a key, but the key is
obtained once by signing up — see §2), Upstox's historical-candle REST (needs
a daily access token — see §2), MCX's free `MCX_FO` instrument master via
Upstox.

## 2. Owner-gated: accounts, API keys, 2FA

Some step in getting data genuinely requires the owner's identity — creating
an account, generating an API key pair, or completing a login/2FA flow that
cannot be scripted without impersonating the owner. In these cases:

- The owner creates the account and generates the key(s) **once**, outside
  any agent session.
- The owner puts the value in `.env` (git-ignored; see `.env.example` for the
  exact variable names already wired for Upstox, Alpaca, and crypto).
- From that point on, the agent reads the key from `.env` / passes it into
  the adapter constructor — the agent never sees, logs, or stores the raw
  credential anywhere else (AGENTS.md §4.3).
- Where a provider requires a **daily** re-login (Upstox's daily access
  token today — OAuth auto-renewal is explicitly deferred, see
  `upstox_history.py`'s module docstring and `docs/decisions.md`), the owner
  performs that daily login manually and supplies the fresh token the same
  way. No agent attempts to script around a 2FA/OTP step.

This is the **only** path where the owner is asked to do anything per data
source. It happens once per credential (or once per day, for Upstox's token,
until OAuth renewal is built), not once per agent session.

## 3. Manual fallback: `data/inbox/`

For anything an agent genuinely cannot reach on its own — a source that
requires a paid subscription not yet approved, a file behind a CAPTCHA or
manual export, a one-off dataset the owner already has locally — the owner
drops the file into `data/inbox/` (git-ignored, created on first use) and
tells the agent what it is. The agent reads from there like any other local
file; it never tries to script a workaround for something that was
explicitly routed to this fallback.

Nothing currently in the repo uses this path — all four non-India markets
plus India found a free, directly-reachable source (see
`docs/DATA_ECOSYSTEM_BUILD_PLAN.md` and `docs/BUILD_ORDER.md`'s per-market
coverage sections). Keep this section anyway: the day MCX's free source or
Alpaca's corporate-actions feed disappears (both flagged as risks in handoff
note 0032), this is the documented fallback rather than a scramble.

## 4. Conformance check (2026-11-15)

Audited every adapter/loader module under `src/trading/adapters/` and
`src/trading/storage/` that makes a network call, on both `codex/p1-build`
and `claude/sleeve-allocation-and-adapters`:

| Module | Source | Path used | Conforms? |
|---|---|---|---|
| `adapters/upstox_history.py` | Upstox (India equities, CDS_FO, MCX_FO) | §2 — daily access token, owner-supplied, read from caller, never logged | Yes |
| `adapters/binance_history.py` | Binance public REST (crypto) | §1 — no key at all | Yes |
| `adapters/alpaca_history.py` | Alpaca free Basic/IEX (US equities) | §2 — key_id/secret_key passed in by caller, raises if empty rather than silently falling back | Yes |
| `storage/crypto_loader.py`, `storage/us_equity_loader.py` | Binance / Alpaca, via the adapters above | Same as adapter | Yes |
| `storage/intraday_loader.py`, `storage/adjusted_ingestion.py` (Codex, `codex/p1-build`) | Upstox, via `upstox_history.py` | §2 — runtime-injected token per the P1 handoff notes (0030/0031); no credential is hardcoded or persisted outside `.env` | Yes |
| `storage/corporate_actions.py`, `storage/membership.py` (Codex) | NSE circulars / index membership source, per `docs/specs/DATA_SOURCES.md` ("research only: no downloader, broker login, subscription, or external inquiry") | §1 — currently fixture/manually-sourced rows, not yet a live downloader; this is the one module where "how it fetches" isn't fully decided (membership/action source is an open item in note 0029/§13 of `MASTER_PLAN.md`) | **Flag, not a violation** — no network call exists yet to check; once a live membership/action downloader is built it must land in §1 or §2, not bypass to a hardcoded credential. |

**One flag, no violations found.** Nothing in either lineage scripts a login,
stores a raw credential outside `.env`, or silently substitutes a worse
source instead of surfacing to the owner. The only open item is that
Codex's corporate-action/membership data is currently sourced from static,
reviewed fixtures rather than a live fetch (by design, per
`docs/specs/DATA_SOURCES.md`) — when that becomes a live downloader, it
needs to be checked against this doc at that time, not assumed to conform.
