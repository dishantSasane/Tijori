# 0041 — Claude: P7 go-live readiness (checklists + reconciliation drill)

- Status: **needs-human** on two items (below); otherwise ready for cross-model review.
- From: Claude (Sonnet 5)
- To: both agents, owner

## What shipped

PR #60, branch `claude/p7-go-live-readiness`, against `main`:

1. `docs/GO_LIVE_CHECKLIST.md` — ordered, owner-walkthrough checklist
   operationalizing `docs/TESTING.md` §6 ("Go-live gates"): cloud VM +
   static IP, broker KYC + API key scoping (withdrawal disabled for crypto,
   read-only preferred), `.env`/secrets review, kill-switch drill,
   reconciliation drill, mode + risk-engine dry run against the real
   account balance, independent audit, first live order procedure.
2. `docs/LIVE_AUDIT_CHECKLIST.md` — what the dedicated Claude audit pass
   (a separate session, after all code is believed ready — not this one)
   needs to check: mode-gate correctness, risk-engine completeness,
   reconciliation wiring, kill-switch coverage, secrets hygiene, and known
   open gaps pulled from `STATUS.md` at audit time.
3. `src/trading/reconciliation/reconcile.py` (+ 5 tests) — pure
   `reconcile()` compares our recorded positions against a broker's
   reported positions; `run_drill()` logs the result to the audit table
   and engages the kill switch on **any** mismatch (no tolerance band,
   ADR-0029). Tested only against a fake position source — never a real
   broker (AGENTS.md §4.4). It never calls `place_order`; it only reads
   positions and may block new ones via the kill switch.
4. Verified (did not duplicate) that the approval-mode gate is already
   defense-in-depth: `ModeGate.route()` in `src/trading/risk/engine.py`
   returns `Route.NONE` for `Mode.APPROVAL` unless `human_action ==
   "approve"`, and this is already exercised end to end by
   `tests/risk/test_engine.py::test_route_approval_mode_awaits_human`. This
   logic lives in the risk engine, not the Telegram bot, so a UI bug
   cannot bypass it.
5. `docs/decisions.md`: ADR-0029 (reconciliation mismatch has no tolerance
   band) and ADR-0030 (cloud VM provider criteria — decision deferred to
   owner, not committed).
6. `docs/learn/04-going-live-reconciliation-and-ip-whitelisting.md` — plain-
   language lesson on both concepts.

**No code in this PR can place a real order or requires a real secret.
Going live is a manual action the owner takes himself, outside any agent
session, after the checklist above and a separate dedicated audit pass —
this PR does not flip any switch and does not change any default mode.**

## Verification

Full suite 414 tests pass locally; `ruff check`/`ruff format --check`
clean on the whole repo; `mypy src/trading/reconciliation` clean (the only
repo-wide mypy finding is a pre-existing, unrelated `types-PyYAML` stub gap
in `core/config.py`, not touched by this PR).

## Cross-model review required

This PR touches reconciliation (execution-adjacent) and reconfirms
mode-gate logic (risk-adjacent) — AGENTS.md §5 makes review by the other
company's model mandatory before owner merge. Please check in particular:
does `run_drill()`'s kill-switch engagement actually get consulted by
`RiskEngine.check()` before any new signal is approved (trace the call
path, don't just trust the docstring), and is there any path anywhere in
`src/trading/` that reaches a real broker's order-placing method without
going through `RiskEngine.check()` + `ModeGate.route()` returning
`Route.LIVE`?

## needs-human

1. **Cloud VM provider** for the static/reserved IP (ADR-0030 lists
   criteria — Oracle Cloud Always Free's reserved IP looks like the
   cheapest fit, but no commitment made). Owner's call, low-budget
   preference per AGENTS.md §2.
2. **Broker/exchange account** for the actual first live sleeve (which
   market goes live first, which broker, and confirmation of that
   broker's API key-scoping options) — this is upstream of everything in
   `GO_LIVE_CHECKLIST.md` §2.
3. Confirmation the owner understands going live is still fully manual
   after this PR: the checklist and audit scaffold exist, but nobody has
   provisioned a VM, generated a real key, or run a live drill yet.

## Next actions

- Either agent: review PR #60 (cross-model requirement above).
- Owner: decide VM provider and broker/exchange (items 1-2 above) whenever
  ready — not blocking any other in-flight phase (P1-P6 all independent of
  this).
- Whoever picks up P7 next: once a VM/broker exist, actually run
  `GO_LIVE_CHECKLIST.md` §§1-6 for real (this PR only built the checklist
  and the one piece of drill tooling that doesn't need a live account —
  the reconciliation comparison logic itself).
