# HANDOFFS — how Claude Code and Codex talk to each other

Two agents, no shared memory, sessions that end without warning. The `handoffs` branch is the **message board** and the **single source of status truth**. Code never goes there. The owner approves code merges to `main`; the agents push to `handoffs` freely.

## 1. Channels

1. **Commit messages** (see `GIT_WORKFLOW.md`): short signals via trailers (`Handoff:`, `Needs-human:`).
2. **PR comments**: review feedback, questions about specific code.
3. **Handoff notes** on the `handoffs` branch: anything another agent must act on, plus end-of-session state. This is the main channel.

## 2. Layout of the `handoffs` branch (orphan branch; no code)

```
README.md          # this protocol (short)
STATUS.md          # living status board: phases, owners, blockers, last update
TEMPLATE.md        # copy for new notes
notes/
  0001-planning-to-claude-kickoff.md
  0002-planning-to-codex-kickoff.md
  NNNN-<from>-to-<to>-<subject>.md
```

The seed content for this branch ships in the repo as `_handoffs_branch_seed/`; the owner creates the branch from it (`SETUP_CHECKLIST.md`).

## 3. Getting access (each agent, once per environment)

```bash
git fetch origin handoffs
git worktree add ../trading-handoffs handoffs      # a second folder holding the handoffs branch
```

Read before work: `cd ../trading-handoffs && git pull --rebase origin handoffs`, then open `STATUS.md` and notes addressed to you (`to: claude` / `to: codex` / `to: both`).

Write a note:

```bash
cd ../trading-handoffs
cp TEMPLATE.md notes/NNNN-<from>-to-<to>-<subject>.md   # NNNN = next number
# edit it, update STATUS.md if needed
git add -A
git commit -m "handoff(<from>-><to>): <subject>"
git pull --rebase origin handoffs && git push origin handoffs   # retry on conflict
```

If your environment cannot use worktrees, clone the branch separately (`git clone --branch handoffs --single-branch <repo-url> ../trading-handoffs`).

## 4. Note format

Front matter (required): `id, from, to, date, subject, status, refs`.
Statuses: `open` -> `acknowledged` -> `done`, or `needs-human` (owner decision required), `blocked`, `superseded`.
The receiver changes `status` and appends a "Reply" section (do not rewrite the sender's text).
Body sections: **Context**, **What I did**, **Where I stopped (exact)**, **What you need to do**, **Decisions made (+ADR ids)**, **Open questions**, **Model/usage notes**.

## 5. Rules

- Write a note when: you finish a milestone, you are blocked, you found a bug in the other agent's area, a spec is missing/contradictory, your session or plan limit is near its end, or you need an owner decision.
- Assume the reader has **no memory**; be concrete (file paths, commands, branch names, PR numbers).
- Keep `STATUS.md` current: phase, who is doing what, next 3 actions, blockers, date of last update.
- Never put secrets, keys, or personal data in notes.
- `needs-human` notes must state the decision, the options, and your recommendation. The owner answers in the note or via the PR; the agent records the answer in `decisions.md` through a PR.
- Do not use handoff notes to bypass review: code changes still go through PRs.

## 6. Conflict handling

If two notes conflict, the newer one wins unless it says it is superseding an ADR (ADRs need an owner-approved PR). If you disagree with the other agent's decision, reply in the note with your reasoning and a proposed test or experiment; do not silently override it.
