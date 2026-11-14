# Data sources — pre-P0 research

Checked 2026-11-14. Research only: no downloader, broker login, subscription, or
provider selection. This supports ADR-0009; it does not change it. Limits are
provider documentation snapshots, not measured account entitlements. Recheck
before implementing an adapter. A bhavcopy is an exchange's end-of-day market file.

## India: free API candidates

| Provider | Official evidence | Constraints for this project |
|---|---|---|
| Angel One SmartAPI | [Angel One introduction](https://www.angelone.in/knowledge-center/smartapi/detailed-introduction-to-smartapi) explicitly offers free historical data for backtesting and live market feeds. | Requires the owner's account/app setup. Documentation access was restricted in this research session; history depth, current subscription limits, adjustment policy, and delisted coverage remain unconfirmed. |
| FYERS Standard | [Plans and limits](https://fyers.in/api-docs/v3/getting-started/plans-and-limits/) lists a free Standard plan. Data API limits: 5 requests/second, 50/minute, 5,000/day. Daily history: rolling five years; intraday: rolling one year. | Data Socket permits 100 symbols per user across connections. Quotes permit 50 symbols/request. No seconds data on Standard. A 100-name core leaves no room for extra shortlisted names or index subscriptions; explicitly replace names or reduce the core. |

FYERS' [older announcement](https://fyers.in/notice-board/discontinuation-of-truedata-support-from-26th-december-2025)
advertises longer free history. Use the current plan table for planning; do not
assume Prime history is free. Account eligibility and retention/use rights must be
confirmed for the selected provider. The owner still chooses Angel One or FYERS.

The indexed official [SmartAPI rate-limit table](https://smartapi.angelone.in/docs/MarketData)
reports `getCandleData` at 3 requests/second, 180/minute, 5,000/hour. Direct opening
returned an authorization restriction, so these are **provisional indexed values**,
not confirmed adapter settings. Do not work around access controls. The
[historical API documentation](https://smartapi.angelone.in/docs/Historical)
also needs rechecking before implementation, including interval-specific maximum
request spans and timestamp semantics.

## NSE bhavcopy: formats and access gate

The official [All Reports page](https://www.nseindia.com/all-reports) search index
lists **CM-UDiFF Common Bhavcopy Final (zip)**, for example
`BhavCopy_NSE_CM_0_0_0_20261111_F_0000.csv.zip`, and marks legacy CM bhavcopy
discontinued from 2024-07-08. UDiFF is the newer exchange file format.

The date-bearing filename pattern is
`BhavCopy_NSE_CM_0_0_0_<YYYYMMDD>_F_0000.csv.zip`. The report page could not be
fully retrieved during this check. A stable direct archive URL and legacy URL
template were **not confirmed from retrievable official documentation**. Do not
turn a guessed archive path or an undocumented website endpoint into a contract.
Resolve these with the approved data provider before implementing the downloader.

More importantly, [NSE's website terms](https://www.nseindia.com/static/nse-terms-of-use)
prohibit systematic/automated collection and contain restrictions on virtual
trading/simulation use. Public availability of a download is not sufficient
evidence of permission for this project's automated ingestion and backtesting.
Under `AGENTS.md` §10, the planned direct website downloader is **blocked pending
an authorized source/access arrangement**. This also applies to corporate actions.
Manual download alone does not resolve the intended-use restriction.

Recommended next step: ask the owner to obtain suitable provider permission or
choose a documented, licensed broker/vendor feed. No paid alternative is approved
by this research. Continue only synthetic-data work after the P0 gate until the
data-source issue is resolved. Do not scrape, replay browser cookies, or bypass
anti-bot challenges.

## Corporate actions and historical membership

The official [NSE corporate-actions page](https://www.nseindia.com/companies-listing/corporate-filings-actions)
offers date/company filters and CSV downloads. It is a source-discovery reference,
not a documented public ingestion API or evidence of a complete historical feed.
The same website terms above apply.

Open requirements for Claude's P0 contracts/test specs:

- Distinguish raw prices from prices adjusted for splits/bonuses and other events;
  preserve the original file, provider, acquisition time, and adjustment version.
- Specify treatment of dividends and rights separately. Do not infer factors from
  free-text corporate-action descriptions without validated, known-answer cases.
- Obtain historical instrument identifiers, symbol changes, delistings, and
  point-in-time index membership. Today's Nifty 50 list cannot prove a
  survivorship-free historical Nifty 50 result.
- Define missing-day, duplicate-file, revised-file and format-transition behavior.
  Missing data must not silently become a zero-volume candle.

These are engineering requirements inferred from `MASTER_PLAN.md`, `TESTING.md`,
and `STRATEGIES.md`; none of the sources checked establishes that a free feed
fully satisfies them. Do not claim complete adjusted/delisted coverage yet.

## Alpaca: free Basic equities data

The official [market-data plan table](https://docs.alpaca.markets/us/docs/about-market-data-api)
lists Basic as free for US stocks/ETFs, with real-time **IEX** coverage (one
exchange, not the consolidated US market), 30 WebSocket symbols, history since
2016, 200 historical API requests/minute, and a latest-15-minute historical
restriction. Specify and verify the feed/entitlement on each endpoint; do not
interpret Basic as unrestricted real-time consolidated data. US equities data
requires authentication; use paper account credentials when integration begins.

Implications: the proposed Nasdaq 100 plus ETFs cannot all be streamed on Basic.
The owner must approve a smaller live universe or another data arrangement.
Daily research may be viable with delayed history, but full-market coverage,
pagination, historical inactive assets and corporate-action adjustment semantics
still need adapter-level verification. IEX volume must not be presented as
whole-market volume. Do not infer unlimited daily usage from a forum post.

## Verification boundary and follow-up

- Official pages only; no authenticated market-data calls or downloaded datasets.
- Confirmed by retrieved pages: Angel One's free historical offer, FYERS Standard
  limits, Alpaca Basic limits, NSE corporate-actions UI and website restrictions.
- Indexed evidence only: NSE current bhavcopy filename/cutover and SmartAPI limits.
- Unresolved: stable bhavcopy URL formats, source permissions for intended use,
  selected provider/account entitlements, adjusted data and delisted coverage.
- Claude: reconcile these constraints in P0 specs and review this document in its
  PR. Owner decisions belong in an approved ADR PR, not an implicit adapter choice.
- Codex: wait for Claude's P0 handoff and merged foundation before P1.
