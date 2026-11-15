# Data sources — provider research and P1 boundaries

Checked 2026-11-14, with the membership-source follow-up checked 2026-11-15.
Research only: no downloader, broker login, subscription, or external inquiry.
Limits are provider documentation snapshots, not measured account entitlements.
Recheck before bulk ingestion. A bhavcopy is an exchange's end-of-day market
file.

## India: selected P1 historical candle source

ADR-0023 selects the existing Upstox historical-candle adapter as the **only
P1 India candle source**. Use it for the P1 daily and intraday research candles;
do not mix another broker/vendor candle feed into this sample. Preserve the raw
provider response or fixture, request parameters, ingestion timestamp, and
candle provenance as required by ADR-0023. This selection does not settle the
separate point-in-time index-membership or corporate-action sources below, and
does not choose the P3 live feed or execution broker. Confirm Upstox terms and
the account's allowed historical use before bulk ingestion.

The alternatives below are pre-P1 research notes. They are not additional
P1 candle sources under ADR-0023.

## India: other free API candidates (not selected for P1)

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

### Upstox corporate-actions endpoint (selected P1 source)

Upstox documents the authenticated
[`GET /v2/fundamentals/{isin}/corporate-actions` endpoint](https://upstox.com/developer/api-documentation/get-corporate-actions/).
It returns event names, effective/ex-dates, amounts, ratios, and details for
dividends, bonuses, splits, and rights issues. Use this documented API for P1
action records; do not automate requests to NSE/NSE Indices websites. Fetch by
ISIN from the pinned Tier A instrument list, retain the unmodified response,
request date, ISIN, response checksum, and parser version. Refresh periodically
and retain revisions rather than replacing old evidence.

The API documentation does not state that its event list is exhaustive over a
given history range, and does not explicitly list demergers. A successful empty
response is therefore not proof of no actions. Demergers and unknown action
types need human-reviewed records from a permitted source; rights issues are
detected but remain unadjusted. Preserve API ratios as reported until an event
specific test establishes their direction and meaning. Do not use them to
adjust prices or quantities by guessing.

An authenticated live probe on 2026-11-15 was denied by Cloudflare with HTTP
403 `browser_signature_banned`; the response instructed the client not to
retry. The token was present but was not exposed. No data was acquired or
saved, and no alternate user-agent or access-control workaround was attempted.
The adapter is implemented against the published response schema and has
fixture-based tests. Bulk acquisition, data persistence, and event coverage
remain unverified until a permitted request succeeds.

### Point-in-time Nifty 50 / Next 50 membership

The official [NSE Indices data-subscription page](https://www.niftyindices.com/offerings/data-subscription)
says its data products include ongoing and historical index information and
constituent data with company names, identifiers, market capitalization,
weights, and prices. It explicitly lists quantitative research as an intended
use and directs requests for end-of-day constituent data to `indices@nseids.co.in`.
This is the strongest direct route found. The page does not publish price,
exact historical coverage, whether membership is daily or only at rebalances,
delisted-identifier coverage, or a specific licence for this project's
backtests. Those details must be obtained before acquisition or ingestion; no
paid purchase is authorized by this research.

Prepared inquiry (not sent): request Nifty 50 and Nifty Next 50 historical
constituents from the earliest date the provider supports through the latest
completed session; effective dates for every inclusion, exclusion, and ad-hoc
change; stable identifiers including ISIN and historical symbols; coverage of
delisted/renamed companies; file format and update/revision policy; research and
backtesting licence terms; one-time and recurring fees; and sample files for
validation against dated official notices. Ask whether the delivered records
are daily snapshots or event intervals. A response should be saved with the
dataset manifest before ingestion is approved.

NSE Indices also publishes an [index reconstitution calendar](https://niftyindices.com/resources/index-rebalancing-schedule)
and a dated [press-release archive](https://www.niftyindices.com/press-release).
The calendar lists Nifty 50 and Nifty Next 50 as semi-annual reconstitutions
effective on the last working day of March and September, while noting that
additional changes may occur for schemes of arrangement, suspension, and
delisting. The official [equity-index methodology](https://www.niftyindices.com/Methodology/Method_NIFTY_Equity_Indices.pdf)
describes ad-hoc events and effective-date treatment. These sources make a
manual, event-based reconstruction plausible, but a calendar alone is not the
membership history: every ordinary and ad-hoc inclusion/exclusion notice must
be accounted for and checked against a starting constituent snapshot. The
press-release archive contains mixed notices (including corporate adjustments
and launches), so it cannot be treated as a clean membership file without
review.

If reconstruction is required, the auditable output should be an interval
table keyed by stable company identity (ISIN where available), with at least
`index_id`, `isin`, `symbol_at_time`, `company_name_at_time`,
`effective_from`, `effective_to`, `source_notice_url`, `source_notice_date`,
`review_status`, and `notes`. Each record should cite its official notice;
symbol/name changes must be separate identity-mapping events, not guessed from
similar names. Validation should assert 50 members per normal Nifty 50 interval
and 50 per normal Next 50 interval, reconcile every notice's before/after
counts, investigate special-event exceptions, and compare selected dated
snapshots to official constituent reports. Completeness should not be claimed
for any interval with an unexplained event or unresolved identity.
The manifest schema and fail-closed validation rules are specified in
[`INDEX_MEMBERSHIP.md`](INDEX_MEMBERSHIP.md); they validate a supplied dataset,
not the source's license or completeness claim.

Commercial data vendors are another possible route, but the source, coverage,
research-use licence, and cost must be verified with the vendor. Community
GitHub reconstructions may be useful as cross-checks only; they are not a
substitute for source notices and validation.

The official [NSE corporate-actions page](https://www.nseindia.com/companies-listing/corporate-filings-actions)
offers date/company filters and CSV downloads. It is a source-discovery reference,
not a documented public ingestion API or evidence of a complete historical feed.
The same website terms above apply.

P1 corporate-action adjustment requirements:

- Distinguish raw prices from prices adjusted for splits/bonuses and other events;
  preserve the original file, provider, acquisition time, and adjustment version.
- Specify treatment of dividends and rights separately. Do not infer factors from
  free-text corporate-action descriptions without validated, known-answer cases.
- Detect demerger, rights, dividend, and unrecognized corporate-action purposes
  in each backtest window. Exclude affected symbols or require event-level human
  review; never silently leave the event in returns, and do not auto-adjust
  demergers or rights issues.
- The split/bonus transformer and known-answer tests are specified in
  [`CORPORATE_ACTIONS.md`](CORPORATE_ACTIONS.md). A real NESTLEIND 10:1 event
  indicates Upstox's daily candles are already adjusted across that split;
  never apply the transform again to those candles. Treat other symbols and
  action types as unverified until checked. P1 backtests must also account for
  share-count changes on held positions before adjusted data can support
  promotion.
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
  limits, Alpaca Basic limits, NSE corporate-actions UI and website restrictions,
  NSE Indices' historical constituent-data offering for quantitative research,
  its reconstitution calendar, and its press-release archive.
- Indexed evidence only: NSE current bhavcopy filename/cutover and SmartAPI limits.
- Unresolved: stable bhavcopy URL formats, source permissions for intended use,
  selected provider/account entitlements, adjusted data and delisted coverage,
  historical constituent-data price/licence/coverage, and whether notices alone
  permit a complete reconstruction for the required dates.
- This section preserves pre-P1 alternatives and access research; ADR-0023 and
  the selected-source section above govern P1 candle ingestion.
- Owner decisions belong in an approved ADR PR, not an implicit adapter choice.
