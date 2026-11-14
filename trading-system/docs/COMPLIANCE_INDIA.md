# COMPLIANCE (India) — practical notes

**Not legal or tax advice.** Facts below were gathered from broker and news pages on 2026-11-14 and must be re-checked with the chosen broker and a qualified professional. Rules differ by broker implementation.

## 1. SEBI retail algo framework (what applies to this project)

Timeline (as reported by broker explainers):
- Circular issued Feb 2025 ("Safer Participation of Retail Investors in Algorithmic Trading").
- 30 Nov 2025: exchange registration of retail algo products to be complete.
- 3 Jan 2026: brokers complete mock trading sessions.
- 5 Jan 2026: non-compliant brokers barred from onboarding new retail API clients.
- **1 Apr 2026: framework mandatory for all brokers and existing API users.**

Key requirements reported:
- **API keys bound to a static IPv4 address.** Orders from other addresses are rejected. A dynamic home IP does not qualify.
- Typically one primary static IP and an optional secondary; **changes limited (e.g., once every 7 days at some brokers)**; a new session may be needed after a change.
- Every automated order carries an exchange-assigned **Algo-ID** for traceability.
- Mandatory 2FA/OAuth-style login flows; audit trails; order-frequency controls.
- Reported at one broker: only one API key may run *unregistered* algos; others must run registered algos. Check your broker's rules for personal-use algos and any order-rate thresholds.

## 2. What this means for the project

| Activity | Affected? |
|---|---|
| Reading market data, backtests, paper trading | Not blocked by the static-IP rule (it targets **order placement**); confirm with the broker for data endpoints |
| Real India orders (approval/auto) | Yes: must originate from the registered static IP |
| Crypto/US orders | Different regimes; not covered by this SEBI rule (own exchange/broker rules apply) |

Design response:
1. Run research/paper on the laptop.
2. Before going live in India, run the **engine on a small cloud VM with a reserved static IPv4**, whitelist that IP with the order broker, keep it stable (IP changes are rate-limited).
3. Keep the order broker and data broker separate in code (`Broker`, `DataFeed` adapters).
4. Log every order with its strategy instance and version so each automated order is traceable to a strategy.
5. Keep kill switch and order-rate limits in the risk engine regardless of broker limits.

## 3. Pre-live checklist (India)

- [ ] Order broker's current algo/API terms read; static IP registered and tested with a harmless call.
- [ ] Algo registration requirement for personal-use algos confirmed with the broker in writing/support ticket.
- [ ] 2FA/token refresh flow automated safely (secrets in `.env`, never in git).
- [ ] Brokerage and statutory charges loaded into the market profile from a real contract note.
- [ ] Tax treatment per instrument discussed with a CA; rates entered in `config/tax.yaml` (template has TODOs on purpose).
- [ ] Only the owner's own account is used; no managing others' money or sharing signals for a fee.

## 4. Crypto and foreign markets (owner to decide with a professional)

Crypto exchange choice, legality, reporting and tax for an Indian resident; US stocks via the Liberalised Remittance Scheme (limits, TCS, reporting). The project provides engineering, not an opinion on these.

## 5. Why options are gated

A SEBI study, as cited in 2026 broker/news commentary, found the large majority of retail F&O traders lose money. Options stay in the last phase with defined-risk structures and small caps.

## 6. Sources (re-verify)

- SEBI rules explainers: https://dev.to/reyazk08/sebis-new-algo-trading-rules-for-retail-traders-what-changed-in-april-2026-4k04 , https://www.5paisa.com/news/sebi-tightens-algo-trading-rules-with-mandatory-2fa-and-audit-trails-from-april-1
- Broker implementations: https://www.kotakneo.com/platform/kotak-neo-trade-api/static-ip-details/ , https://www.angelone.in/news/market-updates/what-s-changing-in-angel-one-s-smartapi-access-from-april-1-2026 , https://support.fyers.in/portal/en/kb/articles/what-are-the-new-sebi-rules-for-retail-algo-trading-from-april-01-2026
