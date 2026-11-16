# Options learning plan (read before any options code is written)

**Status: gated. No options trading code exists in this repo, on purpose.**
`docs/BUILD_ORDER.md`'s P8 line lists options as "defined-risk only, after
dedicated learning" — this document is that prerequisite. Nothing here is
financial advice (AGENTS.md §11); it is a reading/practice list so the owner
and whichever agent builds this sleeve later share real understanding
before any code path can place an options order.

## Why this is not "equities plus a bit more"

The rest of this system's risk engine (`src/trading/risk/engine.py`) assumes
a position's loss is bounded by (entry price - stop price) × quantity, and
that price moves roughly continuously. Options break both assumptions:

- **Asymmetric, non-linear payoff.** An option's value depends on the
  underlying's price *and* time remaining *and* volatility, not just price.
  A stop-loss on the option's premium does not bound risk the way it does
  for a stock, because premium can gap or decay independently of the
  underlying moving against you.
- **Margin.** A sold ("short") option can require margin that moves with
  the market and can exceed the premium received by a large multiple — the
  sleeve's `risk_per_trade_pct` sizing math has no concept of this yet.
- **Assignment.** A short option can be exercised against the owner at any
  time (American-style) or at expiry (European-style), creating a stock
  position the owner never explicitly ordered. The paper broker and
  reconciliation module (`src/trading/reconciliation/`) have no concept of
  "a position appeared because of assignment, not an order."
- **Expiry and Greeks.** Delta/gamma/theta/vega describe how an option's
  value changes with price/time/volatility. Without at least a working
  intuition for these, a "defined-risk" structure (e.g. a spread) can still
  be mis-sized because the trader doesn't know how fast it will move.

"Defined-risk only" (the BUILD_ORDER qualifier) means long options and
spreads where max loss is capped at entry (long calls/puts, debit spreads,
iron condors sized to their defined width) — never naked short options. Even
within that constraint, margin and assignment mechanics for the *other leg*
of a spread still apply.

## What to learn, in order

1. **Basics**: what a call/put is, strike, expiry, premium, intrinsic vs.
   extrinsic value, in/at/out-of-the-money. (Any standard options-101
   source; Zerodha Varsity's "Options Theory for Professional Trading"
   module is free and India-specific — covers NSE contract conventions
   directly relevant to this repo.)
2. **The Greeks**: delta, gamma, theta, vega — what each measures, and why
   theta decay is not linear (accelerates near expiry).
3. **Margin and assignment**: how SPAN margin works for Indian derivatives,
   what triggers assignment on a short leg, why a spread's "defined risk" on
   paper can still require margin while open.
4. **Defined-risk structures**: long calls/puts, vertical debit spreads,
   iron condors/butterflies with capped width — and why a naked short option
   is explicitly out of scope (AGENTS.md §10: no leverage beyond what a
   strategy spec explicitly allows; a naked short option's loss is
   theoretically unbounded for calls, very large for puts).
5. **Paper-trade by hand first.** Before any code: pick one defined-risk
   structure, paper-trade it manually (pen and paper or broker's paper mode)
   for several expiry cycles, and write down every surprise (assignment,
   margin call, a Greek behaving unexpectedly). That list becomes the actual
   requirements for this sleeve's risk model — better than guessing upfront.

## What this sleeve will need (not built yet)

- An options-specific risk model: margin-aware sizing, not just
  price-distance-to-stop.
- Assignment handling in the paper broker and reconciliation module.
- A chain/Greeks data source (verify licence/cost — SEBI-regulated options
  data is not always free; this itself may be a `needs-human` cost decision).
- A strategy spec (`docs/STRATEGIES.md`-style) for exactly which defined-risk
  structures are in scope, written and reviewed before any backtest code.

## Gate to unblock this sleeve

All of the following must be true, and recorded as a new ADR in
`docs/decisions.md`:

1. The owner has done the reading/practice above (or equivalent) and says so.
2. A dedicated options risk-and-margin spec exists and has been reviewed by
   both agents (cross-model review mandatory per AGENTS.md §5 — this is a
   risk-adjacent module).
3. The owner explicitly authorizes starting options code in `docs/decisions.md`.

Until then: no options strategy code, no options risk model, no options
adapter. See the handoff note on `handoffs` for the explicit `needs-human`
flag on this item.
