---
id: 0005
from: codex (GPT-6.1 Sol)
to: both
date: 2026-11-14
subject: Pre-P0 stopping point and browser PR fallback
status: needs-human
refs: [0002, 0003, codex/data-sources, b3400e3]
---

## Context

Environment checks, documentation review and official-source research are recorded
in note 0003 and `docs/specs/DATA_SOURCES.md`. P1 has not started. GitHub SSH pushes
work, but the owner could not complete the GitHub CLI device authorization and
asked for an alternative. No authenticated GitHub API/browser tool is available.

## What I did

- Pushed research commit `b3400e3` on `codex/data-sources`.
- Pushed findings/status acknowledgment in handoffs commit `69f71d0`.
- Installed GitHub CLI locally at
  `/home/dishant/.local/share/tijori-gh/usr/bin/gh` (Ubuntu package 2.45.0).
- Cancelled the pending device-login process after the owner reported difficulty.
- Prepared the complete PR title/body below and a prefilled browser link.
- Read Claude's in-progress reply to 0003; remaining risk/spec questions are still
  open. Did not stage or change Claude's reply. Note 0004 was reserved by Claude.

## Where I stopped (exact)

- Worktree `/home/dishant/Desktop/Tijori`, branch `codex/data-sources`, HEAD
  `b3400e3a9f60934bd16b0ab8b9e231d58de7f5ae`; branch is pushed, tree clean.
- Handoff worktree `/home/dishant/Desktop/trading-handoffs`, branch `handoffs`.
- No PR has been created by Codex. Remote CI and branch protection are unverified.
- Local checks passed: `.venv/bin/ruff check .`, `.venv/bin/ruff format --check .`,
  `.venv/bin/mypy src`, `.venv/bin/pytest` (one smoke test), `git diff --check`.
- Next concrete step: open the link below while logged into GitHub normally and
  create the research PR. This opens a review request; it does not merge anything.
- After PR creation: record its number here, get Claude's cross-model review
  comment, confirm CI, then await the owner's merge decision.
- P1 remains gated on Claude's P0 handoff, review of the foundation, and owner-
  merged dependencies. Missing risk/backtest specs must not be guessed around.

## What you need to do

Owner: create the prepared PR using normal browser login (CLI OAuth is optional).
Claude: review that PR and carry unresolved note 0003 questions into P0 specs.
Next Codex session: fetch main/handoffs, read new notes, verify PR/review/CI state;
start with the candle store only after the P0 gate is satisfied.

## Decisions made (+ADR ids)

No ADR changed; no runtime code, provider choice, purchase or merge.

## Open questions

Note 0003 still records the data-source/access and live-universe choices. The
only immediate publication blocker is GitHub API authorization; recommended
alternative is this normal browser PR creation, not sharing credentials in chat.

## Model/usage notes

GPT-6.1 Sol. Environment/usage snapshot is in STATUS.md and note 0003. No new
model session, paid API invocation or quota reset was used.

## Prepared PR

Title: `docs(data): record free-feed limits and unresolved access gates`

[Open prefilled PR in GitHub](https://github.com/dishantSasane/Tijori/compare/main...codex/data-sources?quick_pull=1&title=docs%28data%29%3A+record+free-feed+limits+and+unresolved+access+gates&body=%23%23+Plain-language+summary%0AFree+data+feeds+have+limits+that+affect+the+planned+watchlists+and+backtests.+This+research+records+what+official+sources+establish+and+what+still+needs+confirmation+before+we+build+a+downloader.%0A%0A%23%23+What+changed%0A-+Added+%60docs%2Fspecs%2FDATA_SOURCES.md%60%3A+Angel+One%2FFYERS%2C+NSE+bhavcopy+and+corporate+actions%2C+Alpaca+Basic.%0A-+Flagged+NSE+website+access%2Fuse+restrictions%2C+live+subscription+limits%2C+historical+coverage+gaps%2C+and+unconfirmed+archive+URLs.%0A-+Kept+provider+selection+and+all+implementation+gated%3B+no+broker+login+or+runtime+changes.%0A%0A%23%23+Spec+%2F+phase%0APre-P0+independent+research+from+handoff+0002%3B+supports+ADR-0009.+P1+has+not+started.%0A%0A%23%23+Author+model+%2F+reviewer+model%0A-+Author%3A+Codex+GPT-6.1+Sol.%0A-+Reviewer%3A+Claude+requested+via+handoff+0003%3B+pending.+Please+check+evidence+quality%2C+access+gates+and+P0+implications.%0A%0A%23%23+Safety+checklist+%28AGENTS.md+%C2%A74%29%0A-+%5Bx%5D+No+real-order+path+reachable+in+paper+mode+or+from+tests+%28documentation+only%29%0A-+%5Bx%5D+No+secrets%2C+keys%2C+or+personal+data%0A-+%5Bx%5D+No+runtime+change+to+fail-closed+behavior%0A-+%5Bx%5D+No+runtime+change+to+closed-bar%2Fnext-open+semantics%0A-+%5Bx%5D+No+LLM+behavior+change%0A%0A%23%23+Tests%0A-+%5Bx%5D+Existing+unit%2Fsmoke+suite%3A+1+passed%0A-+%5Bx%5D+Ruff+lint+and+format+check%3B+mypy+src%3B+git+diff+--check%0A-+Property%2Fblind+tests%3A+N%2FA%2C+documentation+only.%0A-+CI%3A+pending+remote+run.%0A%0A%23%23+Lesson%0AN%2FA%3A+preparatory+research%2C+not+completion+of+a+build+milestone.%0A%0A%23%23+Needs+human+decision%0AChoose+an+authorized+historical-data+source%2Fuse+arrangement+before+direct+NSE+ingestion%3B+website+terms+restrict+automated+collection+and+simulation+use.+Confirm+smaller%2Frotating+free+live+universes+or+an+alternative+feed.+No+paid+plan+is+proposed+for+purchase+here.+See+handoff+0003+for+options+and+recommendation.%0A%0A%23%23+Handoff%0A-+%5Bx%5D+Note+0003+on+handoffs+contains+review+request%2C+spec+questions%2C+environment+facts+and+exact+stopping+point.%0A-+Wait+for+Claude%27s+final+P0+handoff+and+owner-merged+foundation+before+P1.%0A)

Body (also saved here in case the browser drops URL parameters):

## Plain-language summary
Free data feeds have limits that affect the planned watchlists and backtests. This research records what official sources establish and what still needs confirmation before we build a downloader.

## What changed
- Added `docs/specs/DATA_SOURCES.md`: Angel One/FYERS, NSE bhavcopy and corporate actions, Alpaca Basic.
- Flagged NSE website access/use restrictions, live subscription limits, historical coverage gaps, and unconfirmed archive URLs.
- Kept provider selection and all implementation gated; no broker login or runtime changes.

## Spec / phase
Pre-P0 independent research from handoff 0002; supports ADR-0009. P1 has not started.

## Author model / reviewer model
- Author: Codex GPT-6.1 Sol.
- Reviewer: Claude requested via handoff 0003; pending. Please check evidence quality, access gates and P0 implications.

## Safety checklist (AGENTS.md §4)
- [x] No real-order path reachable in paper mode or from tests (documentation only)
- [x] No secrets, keys, or personal data
- [x] No runtime change to fail-closed behavior
- [x] No runtime change to closed-bar/next-open semantics
- [x] No LLM behavior change

## Tests
- [x] Existing unit/smoke suite: 1 passed
- [x] Ruff lint and format check; mypy src; git diff --check
- Property/blind tests: N/A, documentation only.
- CI: pending remote run.

## Lesson
N/A: preparatory research, not completion of a build milestone.

## Needs human decision
Choose an authorized historical-data source/use arrangement before direct NSE ingestion; website terms restrict automated collection and simulation use. Confirm smaller/rotating free live universes or an alternative feed. No paid plan is proposed for purchase here. See handoff 0003 for options and recommendation.

## Handoff
- [x] Note 0003 on handoffs contains review request, spec questions, environment facts and exact stopping point.
- Wait for Claude's final P0 handoff and owner-merged foundation before P1.

## Reply

(Record PR URL, review and CI results here.)

Final checkpoint: read and acknowledged Claude progress handoff 0004. It explicitly
says Codex still waits on P0. Risk and test specs are missing; contracts are not
merged. P1 stays unstarted. Research and handoff branches are pushed.

## Continuation check (Codex, 2026-11-14)

After the original stop, `git ls-remote origin 'refs/pull/*/head'` showed PR refs
`#2` and `#4` at research commit `b3400e3`, and `#3` and `#5` at Claude's
foundation commit `a36dd03`. At least PR refs were created, so the earlier
statement that no PR exists is superseded. GitHub API access is unavailable for
this private repository (unauthenticated API returned 404), so open/closed state,
review comments and CI results are **unverified**. The owner should use the
GitHub Pull requests page to identify the active PR; duplicate PRs may exist.
P0's final handoff is still absent. No P1 work started.
