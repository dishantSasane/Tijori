# 0044 — Claude: full-universe turnover selector (real data) + Angel One/Fyers cross-validation — PR #63

Status: needs-codex-review (add to the queue in note 0043, highest priority
of the batch — see why below).

## What this covers

Owner resolved two open decisions from the Stage 4 audit (`docs/
STATUS_AUDIT.md` items 2/14): the full-universe point-in-time universe
problem, and a second live-data source for cross-validation.

1. **Full-universe turnover selector against real data**, built against
   Upstox's own official historical-candle API + its own published
   instrument master (`https://assets.upstox.com/.../complete.json.gz`) —
   not NSE's site, not bhavcopy. Sidesteps the `docs/specs/
   RESEARCH_UNIVERSE.md` "Source gate" entirely since every request is a
   licensed Upstox call under ADR-0023, just at full-universe scope.
   `trading.storage.upstox_instrument_master` parses the master filtered to
   `NSE_EQ`/`EQ`; `trading.storage.full_universe_loader` loops the existing
   `UpstoxHistoryClient` across it and feeds the **unchanged** pure
   `research_universe.build_snapshot` selector — ranking logic itself did
   not change, only real data now flows into it.
   **Smoke-tested against real live Upstox data during review** (not just
   fixtures): downloaded the real complete instrument master (2,763 real
   NSE_EQ/EQ rows), and ran a real 5-symbol fetch+rank over a real
   61-session window — RELIANCE/INFY/TCS/HDFCBANK/ICICIBANK ranked
   correctly by real turnover, top-3 selected.
   **Named methodology assumption (ADR-0030):** Upstox's basic candle has no
   official "value traded" field, so turnover is proxied as `close *
   volume`. This is the standard approximation, not identical to NSE's own
   reported traded value — please check this is an acceptable proxy, it's
   the single biggest judgment call in this PR.
2. **Angel One SmartAPI + Fyers historical-candle adapters**
   (`trading.adapters.angelone_history` / `fyers_history`), same raw-urllib
   pattern as `upstox_history.py`, used only as a cross-validation second
   source — never a sole feed for any sleeve.
3. **`trading.adapters.cross_validated_feed.detect_discrepancies`**: pure,
   source-agnostic comparator. Given any two candle lists, flags a
   close-price divergence beyond a tolerance (default 50 bps) only on
   timestamps both feeds report; a candle on only one side isn't itself a
   discrepancy. Never feeds the risk engine or sizing — audit/data-integrity
   signal only.

ADR-0030/0031 in `docs/decisions.md` record both decisions in full,
including the one real caveat worth your attention:

## Please check this first

**ADR-0031 flags, explicitly, that I could not independently verify Angel
One SmartAPI's or Fyers' exact REST endpoint/header shape against their own
docs this session** — both are JS-rendered apps my environment's web-fetch
tool could not crawl to the byte-for-byte spec. The request-parameter names
(`exchange`/`symboltoken`/`interval`/`fromdate`/`todate` for Angel One;
`symbol`/`resolution`/`date_format`/`range_from`/`range_to` for Fyers) are
confirmed from each API's own published parameter reference. The base
URL/path and exact header names (`apiconnect.angelbroking.com` + `/rest/
secure/angelbroking/historical/v1/getCandleData` + `X-PrivateKey`/
`X-UserType`/`X-SourceID` for Angel One; `api-t1.fyers.in/data/history` +
`Authorization: "<app_id>:<access_token>"` for Fyers) are the best-known,
stable, documented shape for each API, but **neither has been exercised
against a live sandbox call with real credentials**. If you have a way to
verify these (your own docs access, or a sandbox key), please do before
either adapter is trusted for a real cross-check call. This is unlike the
Upstox full-universe work above, which I did verify against live data with
real network calls during this session.

## For the next session (either agent)

- Add PR #63 to the review queue from note 0043, at the **top** — it's a
  new PR (not yet in that queue) and the real-data correctness of the
  turnover proxy matters for P1a's eventual broad-universe follow-up.
- `collect_full_universe_snapshot.py` is the CLI entry point for an actual
  monthly run (~2,763 instruments, ~5-10 min at the self-throttled rate) —
  this PR does not run that for real; it's meant to be run deliberately by
  whoever has a verified session calendar and wants a real snapshot.
- Which of Angel One/Fyers (or something else) becomes the *primary* live
  feed is still open (`MASTER_PLAN.md` §13.2) — this PR only adds both as
  the cross-check option.

Agent: claude (sonnet-5)
