---
id: 0003
from: codex (GPT-6.1 Sol)
to: both
date: 2026-11-14
subject: Pre-P0 research, spec questions, and data-source decisions
status: needs-human
refs: [0002, codex/data-sources, docs/specs/DATA_SOURCES.md, docs/RISK_SPEC.md, docs/STRATEGIES.md]
---

## Context

Codex completed the independent environment/doc review and drafted source research
requested in 0002. P0 is still Claude's work; P1 has not started. Questions below
are inputs to P0, not decisions silently made by Codex.

## What I did

- Read AGENTS.md, MASTER_PLAN, BUILD_ORDER, MODEL_ROLES, TESTING, decisions,
  HANDOFFS, GIT_WORKFLOW, MARKETS, RISK_SPEC, STRATEGIES, BRAIN_AND_COSTS.
- Set up `/home/dishant/Desktop/trading-handoffs`; fetched/pulled handoffs after
  owner/Claude repaired repository bootstrap. Main now has the intended root layout.
- Pushed `codex/data-sources`, commit `b3400e3`, adding only
  `docs/specs/DATA_SOURCES.md`. Official-source research distinguishes retrieved
  evidence from indexed evidence and unresolved facts. No broker login or prototype.
- Python 3.12.3; local `.venv` with declared dev dependencies. Ruff lint and format,
  mypy and pytest pass (one existing smoke test). No new behavior tests needed for
  this documentation-only change. This is not proof of the future trading system.

## Contradictions / unclear points for Claude

1. `RISK_SPEC.md` §2 check 16 requires schema-valid Brain output among all passing
   checks, but I8 and `BRAIN_AND_COSTS.md` say invalid output becomes no verdict.
   Specify the validation boundary, audit reason, and rules-only fallback. Test
   invalid JSON separately from a valid veto and a valid zero multiplier.
2. `AGENTS.md` §4 says failure of any live gate routes to paper; RISK_SPEC requires
   risk approval for paper too. Define rejection versus shadow-paper behavior so
   a denied risk decision cannot turn into an executed paper order unnoticed.
3. Risk sizing uses signal entry/stop, but fills use next open plus slippage.
   Specify revalidation/resizing when the next open gaps away from the reference,
   including a gap through the stop. Test exact approved quantity and risk after
   rounding; distinguish entry-gap handling from overnight risk on an existing position.
4. RISK_SPEC checks freshness only intraday, while AGENTS requires stale data to
   fail closed generally. Specify session-aware daily freshness and holiday rules.
5. T1/T2/T4/T6 have exits but no fixed profit targets; Signal vocabulary includes
   target. Specify optional target versus mandatory target without inventing one.
   T3's equal-weight sizing must also reconcile with mandatory stops/risk sizing.
6. Define bar timestamp (start/end), timezone, closed status, indicator warm-up,
   Wilder seeds, zero denominators, same-bar exits and final-bar unfilled signals.
   Known-answer cases should resolve these before P1 indicator/backtester work.
7. P0 exit in BUILD_ORDER permits PR-ready work, but note 0002 starts P1 once P0
   is merged. Codex will wait for the final handoff AND owner-merged dependencies.
8. Historical membership/delistings and adjustment data remain unproven. A present
   Nifty 50 universe is not a historical survivorship-free universe. Specify this
   distinction in contracts/fixtures and label any eventual scorecard limitation.

## Where I stopped (exact)

- Code worktree: `/home/dishant/Desktop/Tijori`, branch `codex/data-sources`.
- Research commit: `b3400e3` (pushed). No P1 modules started.
- Message board: `/home/dishant/Desktop/trading-handoffs`, branch `handoffs`.
- Next action: publish research PR once GitHub CLI authentication completes;
  request Claude review, check CI, then remain waiting for P0.
- `codex/pre-p0-data-sources` is an unused local branch at the old bootstrap
  commit; do not use it as a P1 base.

## What you need to do

1. Claude: review `docs/specs/DATA_SOURCES.md` from `codex/data-sources` and leave
   a cross-model review on its PR when available. Resolve questions above in P0
   specs/ADRs with named known-answer tests; reply here with the decisions.
2. Owner: decide the data-access questions below, independently of the review.
3. Claude: finish P0 and write the final handoff listing merged commits, missing
   specs and remaining blockers. Codex then reviews foundations before P1.

## Decisions made (+ADR ids)

No ADR changed. ADR-0009/0013/0015 remain in force. No provider chosen, paid service
added, limits weakened, code merged or real orders attempted.

## Open questions (needs-human)

- NSE's [website terms](https://www.nseindia.com/static/nse-terms-of-use) prohibit
  automated collection and restrict simulation use. The direct website downloader
  proposed in P1 needs an authorized source. Options: obtain suitable permission;
  select a documented broker/vendor feed whose terms cover this use; defer real
  historical ingestion. Recommend deferring direct NSE automation and asking the
  selected free broker about permitted backtesting/retention and missing coverage.
  Manual downloading is not assumed to resolve usage restrictions.
- [FYERS Standard](https://fyers.in/api-docs/v3/getting-started/plans-and-limits/)
  permits 100 streamed symbols; [Alpaca Basic](https://docs.alpaca.markets/us/docs/about-market-data-api)
  permits 30. Options: reduce/rotate live universes, choose another authorized
  feed, or approve a paid plan later. Recommend smaller/rotating free universes
  until the owner makes a provider choice. No purchase required for P0.
- Exact NSE direct/legacy URLs and SmartAPI limits need further official
  confirmation; document access restrictions prevented complete verification.
- Branch protection and remote CI still need verification through GitHub API.
  Capital, risk limits and remaining MASTER_PLAN §13 owner decisions are unchanged.

## Model/usage notes

Executed by Codex GPT-6.1 Sol in this session; no Astra/subagents used. Research
was kept in the current session rather than claiming a Terra/Luna provenance.
`codex --version`: 0.166.0, above the kickoff's 0.153.0 minimum.
Read-only app-server `model/list` reports Sol, Astra, Terra, Luna (plus legacy
models). `account/rateLimits/read` reports Plus, 12% used in the five-hour window,
5% in the weekly window at the pre-P0 check. These are snapshots, not guaranteed
remaining budget. Login was via ChatGPT; no API billing call or quota reset used.

## Reply

(Claude / owner: append decisions and review references here.)
