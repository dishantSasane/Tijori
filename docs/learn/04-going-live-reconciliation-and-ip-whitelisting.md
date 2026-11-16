# 04 — Going live: reconciliation and IP whitelisting

## What this is

Two safety habits every real trading system needs before it touches real
money: **reconciliation** (checking your own records against the broker's
records and refusing to trade if they disagree) and **IP whitelisting**
(telling your broker "only accept API requests from this one computer").

## Why it exists

Your system keeps its own notes about what it owns: "I bought 10 shares of
RELIANCE at ₹1,400." The broker keeps its own, separate notes about what you
actually own. These two sets of notes are *supposed* to always agree, but
they can drift apart — the internet connection drops right after you place
an order and you never hear back whether it filled, someone opens the
broker's app and places an order by hand outside the system, or there's a
bug. If your system doesn't know its own notes might be wrong, it will keep
trading on bad information — and could buy more of something you already
hold, or think a stop-loss is protecting a position that doesn't exist.
**Reconciliation** is the fix: periodically compare the two sets of notes,
and if they don't match exactly, stop opening new trades until a human looks.

IP whitelisting exists because an API key is just a password. If someone
steals your key but your broker only accepts requests from one specific
internet address (IP), the thief's request gets rejected even with a valid
key — one more lock on the door. Most Indian brokers require this for API
trading. The catch: your home/laptop internet address usually changes
(different wifi, a router restart, a new day). A cheap cloud server with a
"reserved" or "static" IP solves that — it's an address that never changes.

## Tiny example

Your system's records (`state_db.py`) say: `NSE, RELIANCE, qty=10`.
You call the broker's API and it says: `NSE, RELIANCE, qty=0`.

That's a mismatch. Maybe the order never actually filled and your system
just assumed it did. `src/trading/reconciliation/reconcile.py`'s
`reconcile()` function finds exactly this kind of difference — any quantity
that doesn't match exactly, on either side, counts — and `run_drill()` then
tells the kill switch to engage, which stops the risk engine from approving
any *new* trade until a human checks what actually happened and clears it.
Existing stop-losses are left alone; this only blocks new entries.

## How to run it in this repo

```bash
# the pure comparison, and the kill-switch side effect, both with fakes
pytest tests/reconciliation/test_reconcile.py -v

# a tiny manual self-check
python -m tests.reconciliation.test_reconcile
```

Before going live, `docs/GO_LIVE_CHECKLIST.md` §5 has you run the same
`run_drill()` once against the broker's real sandbox, not just a fake.

## Common mistakes

- Giving reconciliation a "tolerance band" ("it's fine if it's within 1
  share") — any difference at all means something unexpected happened, and
  the system can't tell on its own whether it's harmless or serious. A
  human decides that, not a threshold picked in advance.
- Treating IP whitelisting as optional because "it's just research/paper
  trading" — it only matters once a broker key that can place *real* orders
  exists. Paper trading can run from a laptop; nothing here changes that.
- Confusing "static IP" with "the IP I currently have" — a home ISP's IP
  looks static for weeks and then changes; only a provider-marked
  reserved/static IP (cloud VM) is guaranteed stable.

## Check yourself

1. If your system's records say you hold 5 shares and the broker says 5,
   is that clean or a mismatch? What if the broker says 7?
2. Why does a reconciliation mismatch stop *new* trades but leave existing
   stop-losses in place?
3. Why can't you just keep trading from your laptop's current IP and update
   the broker's whitelist by hand every time it changes?

## Words used in this lesson

- **reconciliation**: comparing your own records against an external
  source of truth (the broker) and treating any disagreement as a stop
  signal, not a rounding error.
- **IP whitelisting**: a broker-side rule that only accepts API requests
  from one or more pre-approved internet addresses.
- **static/reserved IP**: an internet address a cloud provider guarantees
  won't change, unlike a typical home internet address.
- **kill switch**: a flag the risk engine checks before approving any new
  trade; when engaged, it blocks new entries without touching existing
  positions' protective stops.
