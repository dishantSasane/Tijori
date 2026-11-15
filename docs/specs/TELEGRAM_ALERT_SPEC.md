# TELEGRAM ALERT SPEC

Status: P2 deliverable (`docs/BUILD_ORDER.md`). Written ahead of implementation
so Codex isn't guessing at the Approve/Paper-test/Reject wiring. Extends
`PAGES.md` §2 (card format) and §3 (API) and `RISK_SPEC.md` §2A (tiered
execution mode and pre-market batch approval). Does not change any risk rule —
this spec is the delivery/UI layer sitting on top of a `RiskDecision` that
already exists; it never computes a decision itself.

## 1. Why a separate spec

`PAGES.md` §2 fixed the card's *text*. `RISK_SPEC.md` §2A fixed *when* a
trade needs approval vs. auto-executes vs. is batched pre-market. Neither
file says what state a signal is in between "risk engine approved it" and
"a human (or timeout) resolved it," what happens if two Telegram taps race,
or how a batch of N signals becomes N independent decisions instead of one
blob. That is this spec.

## 2. Per-signal state machine

Every signal that reaches this layer already has `RiskDecision.allowed=True`
(a rejected decision never reaches Telegram as an actionable card — it still
gets a notification per `RISK_SPEC.md` §2A's table, but with no buttons).

```
            risk-approved signal
                    |
                    v
              +-----------+
              |  PENDING  |  <-- card sent (individually or in a batch)
              +-----------+
               |    |    |
      approve  |    |    | reject
               v    |    v
         +--------+ |  +--------+
         |APPROVED| |  |REJECTED|
         +--------+ |  +--------+
                     | paper test
                     v
               +-----------+
               |PAPER_TESTED|
               +-----------+

   PENDING, with no human action before expiry --v
                    +-----------+
                    |  EXPIRED  |
                    +-----------+
```

- `PENDING -> APPROVED`: routes per `RISK_SPEC.md` §2A (still gated by sleeve
  mode, AGENTS.md §4 rule 1 — Approve on a `paper` sleeve is not offered at
  all, per `PAGES.md` §2's existing rule, so this transition cannot occur
  there).
- `PENDING -> PAPER_TESTED`: always available regardless of sleeve mode;
  produces a `Fill(ledger_source=USER_PAPER)` through the paper broker's fill
  model (`PAPER_BROKER_SPEC.md` §2), never a real order.
- `PENDING -> REJECTED`: produces a `SignalOutcome` via the shadow tracker
  (`PAPER_BROKER_SPEC.md` §5) if `auto_paper_shadow=True` for that sleeve,
  exactly as for a risk-engine rejection — a human reject and a risk reject
  are scored identically, never distinguished in the shadow ledger.
- `PENDING -> EXPIRED`: the signal's own session-end timeout fires
  (`PAPER_BROKER_SPEC.md` §2.1) before any human action. `EXPIRED` is a
  terminal state distinct from `REJECTED` — it answers "nobody looked at
  this," not "somebody said no" — and is shadow-scored the same way.
- `APPROVED`, `PAPER_TESTED`, `REJECTED`, `EXPIRED` are all terminal. No
  transition leaves any of them; a second tap on an already-resolved card
  (see §4) is a no-op, never a re-decision.

This state lives in SQLite alongside the paper broker's tables
(`PAPER_BROKER_SPEC.md` §4) as a `telegram_decisions` table:

| Column | Notes |
|---|---|
| `signal_id` (PK) | matches `RiskDecision.signal_id` |
| `state` | one of the five states above |
| `batch_id` | `NULL` for an individual intraday card, else the pre-market batch it belongs to (§3) |
| `message_id` | Telegram message id, so a late/duplicate callback can be matched and ignored if the card was already edited to a terminal state |
| `decided_by` | `telegram` or `dashboard` — both surfaces write to the same table (`PAGES.md` §3's `POST /signals/{id}/decision`) |
| `decided_ts` | from the injected clock, never `datetime.now()` (AGENTS.md §6) |

## 3. Pre-market batch approval wiring

`RISK_SPEC.md` §2A already specifies *that* approval-routed signals are shown
as a batch before session open. This section specifies the mechanics:

1. At a configured pre-market time (`config/markets.yaml`, per market —
   e.g. 08:45 IST for NSE), the scheduler collects every `PENDING` signal
   with `decided_ts IS NULL` and `route=APPROVAL` for sleeves whose market
   opens that session, and assigns them a shared `batch_id`.
2. One Telegram message per signal is still sent (Telegram's inline-keyboard
   limit makes one giant multi-signal message unworkable for N buttons) but
   all N are sent back-to-back with a header message
   `"Pre-market batch: N signals for review before open"` carrying no buttons
   of its own — it is a label, not an action.
3. Each signal's card keeps its own Approve/Paper test/Reject row. Approving
   one card never approves, rejects, or otherwise touches any other card in
   the same `batch_id` — `RISK_SPEC.md` §2A is explicit that batch review is
   "reviewed batch decision," not "blanket approval," and that holds per
   button tap, not just per the word "batch."
4. A signal that arrives **after** the pre-market batch has already been sent
   (an intraday signal on an approval-routed strategy) is sent as an
   individual card immediately, with `batch_id=NULL` — it does not wait for
   tomorrow's batch.
5. If the pre-market cutoff time arrives while a signal from the *previous*
   session is still `PENDING`, that signal is first forced to `EXPIRED`
   (§2) — a batch never silently inherits a stale signal from before the
   session it was built for.

## 4. Concurrency and idempotency

Two failure modes this must survive, because a phone and a dashboard tab can
both be open on the same card:

- **Double-tap on one surface.** Telegram redelivers a callback if the bot's
  ack is slow. The handler must check `telegram_decisions.state` before
  acting: if already terminal, answer the callback (so the Telegram UI stops
  spinning) but perform no state change and write no second `AuditEvent`.
  This is the same "exactly once" discipline as `RISK_SPEC.md` invariant I7
  for signal submission, applied to the decision instead of the signal.
- **Race between Telegram and the dashboard.** Both write through the same
  `POST /signals/{id}/decision` path (`PAGES.md` §3) and the same SQLite row,
  guarded by the row's current `state`: a transition is only committed if the
  row is still `PENDING` at write time (optimistic check, not a lock) — the
  loser's request gets an "already decided via {other surface}" response
  instead of applying. Exactly one terminal state per signal, chosen by
  whichever surface's request reached the database first.
- Every transition in §2, successful or rejected-as-already-decided, is an
  `AuditEvent` (AGENTS.md §6) — "who decided what, when, from where" must be
  reconstructable without trusting Telegram's own history.

## 5. Card edit behaviour

Once a card leaves `PENDING`, its Telegram message is edited (not replaced or
left stale) to show the resolution inline, e.g. appending
`"-> Approved at 09:14 IST"` or `"-> Expired (session ended unfilled)"` below
the original card text, and the inline keyboard is removed. A card that still
shows buttons is always still `PENDING` — the owner must never be able to tap
a button whose decision already happened elsewhere.

## 6. Non-goals

- Does not define the bot's command surface beyond the alert card
  (`/status`, `/killswitch`, etc. are out of scope here if they exist at all
  — not yet specced).
- Does not re-derive routing rules — those are `RISK_SPEC.md` §2A, imported
  as-is.
- Does not cover the dashboard's own rendering of the same state beyond
  noting it shares the table and API path; `PAGES.md` owns dashboard layout.
