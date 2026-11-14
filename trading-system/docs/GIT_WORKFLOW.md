# GIT WORKFLOW

## 1. Branches

| Branch | Who | Rule |
|---|---|---|
| `main` | nobody pushes directly | Protected. Merge only via PR with owner approval, green CI, and a cross-model review comment |
| `claude/<topic>` | Claude Code | Short-lived feature branches, e.g. `claude/core-contracts` |
| `codex/<topic>` | Codex | e.g. `codex/backtester-engine` |
| `handoffs` | both agents push **directly** | Message board: notes only, never code. See `HANDOFFS.md` |

Short-lived topic branches (not two long-running `claude` and `codex` branches) avoid painful merge conflicts. Delete branches after merge.

## 2. Pull requests

- Use `.github/pull_request_template.md`.
- One logical change per PR; keep PRs reviewable (a beginner owner must be able to understand the summary).
- **Author != reviewer.** The other agent reviews first. Critical modules (`risk`, `execution`, `backtest`, `brokers`): reviewer is a different model, ideally from the other company (see `MODEL_ROLES.md`).
- Reviewer leaves comments in the PR; blocking issues must be resolved before the owner is asked to approve.
- Owner approves and merges (squash merge recommended: one clean commit per PR).
- Never merge your own PR. Never force-push to shared branches. Rebase your own topic branch on `main` as needed.

## 3. Commit message convention (one of the agent-to-agent channels)

```
<type>(<scope>): <summary in imperative, <= 72 chars>

<body: what and why, wrapped at ~100 cols>

Agent: <claude|codex> (<model>)
Refs: <docs/... or issue/handoff id>
Handoff: <to=codex|to=claude|none> <short ask or note>   # optional
Needs-human: <question>                                  # optional
```

Types: `feat, fix, test, docs, refactor, chore, spec, lesson`. Examples:
`spec(risk): define check order and reason codes`, `test(backtest): add known-answer cases for stop-first rule`.

Rule: if you need the other agent to *act*, also write a handoff note; the trailer is only a pointer.

## 4. Branch protection (owner sets these on GitHub; see `SETUP_CHECKLIST.md`)

For `main`: require a pull request before merging; require 1 approval; require status checks to pass (CI); dismiss stale approvals on new commits; block force pushes; block deletions.
For `handoffs`: **no** protection (agents push directly).
Optional: CODEOWNERS entries requiring owner review for `src/trading/risk/`, `src/trading/execution/`, `src/trading/backtest/`, `config/`.

## 5. Tags and versions

- Strategy versions are recorded in the registry (`STRATEGIES.md` §8) and tagged in git when frozen: `strategy/<instance_id>/<version>`.
- App releases: `v0.x.y` tags by the owner.

## 6. Secrets hygiene

`.env` and real `config/*.yaml` are git-ignored. CI rejects obvious secret patterns. If a secret is ever committed, treat it as leaked: rotate it immediately and tell the owner via a `needs-human` handoff.
