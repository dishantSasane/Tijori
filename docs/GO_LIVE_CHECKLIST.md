# GO-LIVE CHECKLIST (P7)

**No code in this repository can place a real order or requires real
secrets. Going live is a manual action the owner (Dishant) takes himself,
outside any agent session, after every box below is checked and a separate
Claude audit pass (`docs/LIVE_AUDIT_CHECKLIST.md`) is done.** This file
operationalizes `docs/TESTING.md` §6 ("Go-live gates") as an ordered,
walk-through checklist. Do these in order; each depends on the one before it.

If any box can't be checked, stop. Do not go live partway through this list.

## 0. Before you start

- [ ] You have read `docs/learn/` on risk and kill switches (see the new P7
  lesson for reconciliation and IP whitelisting) and understand what each
  term means.
- [ ] You accept that the first live sleeve can lose its entire allocated
  capital. Size it so that loss is acceptable (`TESTING.md` §6 last item).

## 1. Cloud VM with a reserved (static) IP

**Why:** most Indian brokers (and many exchanges) require you to register
the IP address your orders will come from — "IP whitelisting" — so a
stolen API key alone can't be used from an attacker's machine. Your laptop's
IP changes (different wifi, mobile hotspot, ISP reassigns it), so the system
needs to run from a machine with an IP that never changes.

- [ ] Pick a cheap VM provider with a free or near-free tier and an easy
  static/reserved IP option. Cost-conscious recommendation and why: see
  `docs/decisions.md` ADR for this phase.
- [ ] Provision the VM, confirm the IP is marked "static"/"reserved" (not
  "dynamic" or "ephemeral") in the provider's console.
- [ ] `ssh` in once and note the IP in your own private notes — **not** in
  git. (`docs/decisions.md` records the provider choice, never the IP or
  credentials.)
- [ ] Set up unattended-upgrades or an equivalent patching cadence — a VM
  that holds API keys is now a target.

## 2. Broker account, KYC, and API keys

- [ ] Complete KYC with your chosen broker(s) for the market(s) going live
  first (start with exactly one sleeve, one market).
- [ ] Generate API keys scoped as narrowly as the broker allows:
  - Crypto exchanges: **withdrawal permission disabled** on the key (AGENTS.md
    §4.3 — non-negotiable). Trading-only, no withdrawal, no transfer.
  - Everywhere: prefer a **read-only** key for anything that doesn't need to
    place orders (e.g. a dashboard or reconciliation job should use a
    read-only key, not the order-placing key).
- [ ] Register the VM's static IP in the broker's IP-whitelisting UI (exact
  flow is broker-specific — follow their docs; this is pure point-and-click,
  nothing to build).
- [ ] Confirm the key works against the broker's **sandbox/paper** endpoint
  first, if one exists, before touching the live endpoint.

## 3. Secrets handling

- [ ] Real keys live only in `.env` on the VM, which is `.gitignore`d. Confirm
  with `git check-ignore -v .env` on the VM that it is in fact ignored.
- [ ] Run `git log --all -- .env` and grep history for the literal key
  strings (`git log -p -S'<first few chars of a key>'`) to confirm no key
  was ever committed, including on a branch or in an old commit.
- [ ] Confirm nothing in `src/trading/` logs, prints, or includes a secret in
  an audit-log payload (`AGENTS.md` §4.3 — audit payloads are `dict[str,
  Any]` written verbatim; never pass a credential object into one).
- [ ] If a key is ever exposed (committed, logged, pasted anywhere public):
  rotate it immediately at the broker and tell the owner — do not wait.

## 4. Kill switch drill (paper)

- [ ] Run the kill-switch test suite (`tests/risk/test_kill_switch.py` and
  `tests/risk/test_engine.py`'s kill-switch cases) and confirm green.
- [ ] Manually engage the kill switch against the **paper** broker while a
  position is open; confirm new signals are rejected
  (`ReasonCode.KILL_SWITCH_ENGAGED`) and the existing position's protective
  stop is untouched. Release it and confirm signals flow again.
- [ ] Repeat the same drill against the broker **sandbox**, if the broker
  offers one, before going live.

## 5. Reconciliation drill

**Why:** the system's own record of what it holds (SQLite `state_db.py`)
and the broker's record of what you actually hold can drift apart — a fill
notification missed on a dropped connection, a manual order placed outside
the system, a bug. If they disagree, the system must stop opening new
positions until a human figures out why, rather than trade on a number it
isn't sure is right (AGENTS.md §4.2, fail closed).

- [ ] Run `tests/reconciliation/test_reconcile.py` and confirm green — it
  proves the comparison logic and that a mismatch engages the kill switch,
  using a fake position source, never a real broker.
- [ ] Before going live, run one real reconciliation drill against the
  broker's **sandbox**: open a tiny paper/sandbox position, then
  deliberately make local state disagree (e.g. edit a local qty), run
  `trading.reconciliation.reconcile.run_drill`, and confirm the kill switch
  engaged and the audit log recorded it (`event_type="reconciliation_drill"`).
- [ ] Schedule `run_drill` to run automatically (e.g. hourly during market
  hours) once live money is at risk — decide the cadence in
  `docs/decisions.md` before going live.

## 6. Mode and risk-engine confirmation

- [ ] Confirm the sleeve's config has `mode: approval`, **never** `auto`,
  for the first live period (AGENTS.md §4.1).
- [ ] Confirm `tests/risk/test_engine.py::test_route_approval_mode_awaits_human`
  passes — it proves `ModeGate.route()` returns `Route.NONE` for an
  `approval`-mode signal unless the human action is exactly `"approve"`,
  and this check lives inside `src/trading/risk/engine.py`, not in the
  Telegram bot — a UI bug cannot bypass it.
- [ ] Run risk checks 1–17 (`docs/specs/RISK_ENGINE_SPEC.md` §2) in a **dry
  run** against the live account's real but tiny balance: fetch the real
  equity number, feed it through `RiskEngine.check()` with a synthetic
  signal, and confirm every check evaluates sanely (no crash, no surprising
  `allowed=True` on a check that should have failed) before any real signal
  is allowed through.
- [ ] Confirm the kill switch is **off** (released) at the moment you flip
  to live — a drill in step 4 may have left it engaged.

## 7. Independent audit

- [ ] A Claude model has completed the review in
  `docs/LIVE_AUDIT_CHECKLIST.md` as a **separate, dedicated pass** after all
  code above is believed ready (not the same session that wrote the code —
  AGENTS.md §5, author != reviewer, applies doubly here).
- [ ] All blocking findings from that audit are resolved and re-checked.

## 8. First live order

- [ ] Sleeve mode is `approval`. Size is tiny (step 0). Kill switch is off.
  Reconciliation drill passed in the last 24h. Audit (step 7) is signed off.
- [ ] The owner personally clicks "Approve" on the first live signal. No
  agent session does this step.
- [ ] Immediately after the first fill: run the reconciliation drill once
  more against the real account, by hand, and confirm it's clean.
