# 04 — The risk engine and the kill switch

## What this is

The **risk engine** is a gatekeeper. Every time a strategy wants to buy or
sell something, its request goes through the risk engine first. The risk
engine runs 16 small yes/no checks, in a fixed order, and the moment one of
them says "no," the whole request is rejected — the later checks never even
run. If every check says "yes," the risk engine also decides *how many
shares/units* to buy (this is called "sizing").

The **kill switch** is a big red button (manual or automatic) that says "stop
opening new positions right now." It can be pulled for the whole system
(global), for one market like Indian equities (sleeve), or for one strategy
(instance). It never touches positions you already have open — your existing
stop-losses keep working even with the kill switch on.

## Why it exists

Without a risk engine, a bug in a strategy (or a weird market event) could
place an order for far more money than you meant to risk, or place the same
order twice, or keep trading after you've already lost more than you're
willing to lose today. The risk engine is where "never let a single mistake
cost more than X%" actually gets enforced in code, not just in your head.

The kill switch exists because sometimes the right answer to "something looks
wrong" is "stop everything, right now, and let a human look," not "keep going
and hope." AGENTS.md calls this "fail closed" — when in doubt, do less, not
more.

## Tiny example

Say your account (one "sleeve") has ₹10,00,000, and you've told the system
"never risk more than 0.5% of the sleeve on one trade."

- A strategy says: buy RELIANCE at ₹2,500, with a stop-loss at ₹2,450.
- Risk per share = ₹2,500 − ₹2,450 = ₹50.
- Risk budget = 0.5% of ₹10,00,000 = ₹5,000.
- Quantity = ₹5,000 ÷ ₹50 = 100 shares. (Always rounded **down** — never up,
  because rounding up would mean risking more than you said you would.)

If an AI "Brain" module later says "I'm only 60% confident in this," the
quantity gets multiplied by 0.6 → 60 shares. The Brain can only ever shrink
the trade or veto it outright — it is never allowed to make a trade bigger
than the risk engine already decided (see `docs/decisions.md` ADR-0008).

## How to run it in this repo

```bash
# Run just the risk-engine and paper-broker tests:
pytest tests/risk tests/execution -q

# Run the kill-switch drill specifically — it's a full end-to-end rehearsal:
pytest tests/execution/test_kill_switch_drill.py -v
```

Reading `tests/execution/test_kill_switch_drill.py::test_kill_switch_drill_full_six_steps`
top to bottom is itself a lesson: it opens a position, engages the kill
switch, proves new trades are blocked, proves the open position's stop still
fires, restarts the whole program, proves the block survived the restart,
then releases the kill switch and proves trading resumes — all with an
audit-log entry for every step.

## Common mistakes

- **Thinking "kill switch" means "flatten everything."** It doesn't. It only
  blocks *new* entries. Protective stops on positions you already hold stay
  live on purpose — selling in a panic is often worse than letting a
  pre-planned stop do its job.
- **Letting the kill switch turn itself back on.** Time passing, a restart,
  or a mode change never un-engages it — only a person explicitly calling
  "release" does. This is deliberate (invariant I10 in the spec): automatic
  systems may only make things *safer*, never *looser*, on their own.
- **Rounding a trade size up "just this once."** The code floors every
  rounding step. If a trade rounds down to zero shares, the trade is
  rejected, not bumped up to one share "to not waste the signal."

## Check yourself

1. If a strategy's stop-loss is missing, which check rejects it, and why does
   that check run *before* the risk-per-trade check?
2. Why does a reject from the risk engine never produce a "shadow" paper
   trade, while a human tapping "reject" in Telegram sometimes does?
3. The kill switch has three scopes (global, sleeve, instance). Give an
   example of a situation where you'd want to pull the sleeve-level one but
   not the global one.

## Words used in this lesson

- **sleeve**: one market/account bucket (e.g. "Indian equities") with its own
  risk limits, separate from the others.
- **sizing**: deciding how many shares/units to buy, from the risk budget and
  the stop-loss distance.
- **kill switch**: a stop-new-trades control, scoped global/sleeve/instance.
- **invariant**: a rule that must always hold, tested directly in code (e.g.
  "quantity never rounds up").
- **shadow trade**: a paper trade recorded only to see "what would have
  happened," never a real order.
