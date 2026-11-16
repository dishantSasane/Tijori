# LIVE AUDIT CHECKLIST (for the dedicated Claude audit pass, P7)

This is **not** performed by whichever agent wrote the code (AGENTS.md §5,
author != reviewer — applies with extra weight here because real money
follows). The owner buys brief Claude Pro/API access specifically for this
pass, after `docs/GO_LIVE_CHECKLIST.md` steps 1–6 are believed complete, and
runs through every item below against the actual code on `main` at that
commit. Record the commit hash and date at the top of the audit's write-up.

Answer every question. "Looks fine" is not an answer — point to the file and
line, or the test, that proves it.

## 1. Mode gate / approval-mode correctness

- Does `ModeGate.route()` (`src/trading/risk/engine.py`) return `Route.NONE`
  for every `Mode.APPROVAL` signal where `human_action != "approve"`? Read
  the function, don't just trust the docstring.
- Is there any code path — Telegram handler, scheduler, CLI — that can call
  a real `Broker.place_order()` (or whatever the live adapter's execute
  method is named) **without** going through `RiskEngine.check()` followed
  by `ModeGate.route()` returning `Route.LIVE`? Grep every caller of
  `place_order` (or the live adapter's equivalent) across `src/trading/`.
- Is `Mode.AUTO` set anywhere in a real (non-`.example.`) config file? It
  must not be, for the first live period (`GO_LIVE_CHECKLIST.md` §6).

## 2. Risk engine completeness

- Walk `docs/specs/RISK_ENGINE_SPEC.md` §2's check list (1–17) against
  `RiskEngine.check()`'s actual code, in order. Confirm each check is
  present, in the stated order, and that `check_fail_closed()` really
  catches unexpected exceptions and converts them to
  `ReasonCode.INTERNAL_ERROR_FAIL_CLOSED` rather than letting one propagate.
- Confirm the kill switch is read **fresh** on every `check()` call (no
  caching across calls that could serve a stale "released" answer).
- Confirm `RiskDecision(allowed=True, qty=0)` is impossible (Pydantic
  validator in `core/models.py` — invariant I9) — an approval can never
  carry a zero quantity.

## 3. Reconciliation

- Does `run_drill()` (`src/trading/reconciliation/reconcile.py`) engage the
  kill switch on **any** mismatch (qty difference, extra position on either
  side), with no tolerance band? Confirm by reading the code, not the
  tests alone.
- Is a reconciliation mismatch actually wired to block new entries — i.e.
  does `KillSwitch.is_engaged("global")` (or whatever scope `run_drill` used)
  get checked by `RiskEngine.check()` before any new signal is approved?
  Trace the call path.
- Has a reconciliation drill against the broker's real sandbox (not just the
  fake in tests) been run and recorded, per `GO_LIVE_CHECKLIST.md` §5?

## 4. Kill switch coverage

- Confirm kill switch scopes (`global`, `sleeve:<name>`,
  `instance:<strategy_id>:<market>`) are all checked, in that order, by
  `RiskEngine.check()`'s check 1.
- Confirm engaging a kill switch never auto-releases (no TTL, no "re-engage
  only" bug) — release must be an explicit, separately-audited call
  (invariant I10).
- Confirm an engaged kill switch does not touch existing protective stops —
  it blocks new entries only (AGENTS.md §4.2).

## 5. Secrets hygiene

- `git log --all -p | grep` (or GitHub's secret-scanning alerts) for any
  committed key material, in any branch, at any point in history — not just
  the tip of `main`.
- Confirm no `print`, `logging`, or `AuditLog.write()` call anywhere in
  `src/trading/` can include a credential value (grep for where API keys /
  tokens are read and trace every place that variable is subsequently
  logged or written to an audit payload).
- Confirm `.env` and any real (non-`.example.`) `config/*.yaml` are
  `.gitignore`d and were never committed.
- Confirm crypto keys in use have withdrawal disabled (this is a broker
  console setting the audit can only ask the owner to confirm screenshot-
  style evidence of, not verify from code).

## 6. Known open gaps (pull from `STATUS.md` at audit time)

- List every "needs-human" and "blocked" item on the `handoffs` branch
  `STATUS.md` as of the audit commit. For each: does it block going live,
  or is it orthogonal (e.g. a data-layer gap for a market not yet going
  live)? State explicitly which gaps are acceptable to go live with and
  which are not.
- Confirm the strategy instance going live has passed its promotion gates
  (`docs/STRATEGIES.md` §6) and has a paper record — this audit does not
  re-run that evaluation, only confirms it happened and where the record is.

## 7. Sign-off

- [ ] All items above answered with a file/line/test pointer, not a guess.
- [ ] Every blocking finding has a linked fix commit, re-checked by this
  same audit pass before sign-off.
- [ ] This audit's conclusion (go / no-go, and why) is written back to a
  handoff note and `STATUS.md`. The owner makes the final call regardless
  of the audit's conclusion — this is advisory, like the Brain (AGENTS.md
  §4.6's spirit applied to the audit itself: it cannot authorize anything,
  it can only inform the human who does).
