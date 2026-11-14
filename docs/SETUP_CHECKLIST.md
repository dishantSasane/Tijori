# SETUP CHECKLIST (for the owner — about 30-45 minutes)

Do this **today**: the Claude Pro window is short (ends ~2026-11-16). Nothing here costs money.

## A. Create the repo and load the files

1. On GitHub: create a **private** repo (suggested name: `trading-system`). Do not add a README/licence from GitHub.
2. Unzip the delivered `trading-system.zip`. Move the folder `_handoffs_branch_seed/` somewhere temporary (outside the repo folder; you will use it in step C).
3. In the unzipped project folder:
   ```bash
   git init -b main
   git add -A
   git commit -m "chore: initial planning scaffold"
   git remote add origin https://github.com/<you>/trading-system.git
   git push -u origin main
   ```
   (Optional: keep `_handoffs_branch_seed/` out of `main` by adding it to `.gitignore`, or delete it from `main` after step C.)

## B. Protect `main`

GitHub -> repo -> Settings -> Branches (or Rules -> Rulesets) -> add rule for `main`:
- Require a pull request before merging; **1 approval required**.
- Require status checks to pass (select the `test` job after the first CI run).
- Block force pushes; block deletion.
- (Optional) CODEOWNERS later for `src/trading/risk/`, `execution/`, `backtest/`, `config/`.

Do **not** protect the `handoffs` branch.

## C. Create the `handoffs` branch (agents' message board)

```bash
git switch --orphan handoffs
git rm -rf . 2>/dev/null || true
cp -r /path/to/_handoffs_branch_seed/* .
git add -A
git commit -m "handoff: seed message board"
git push -u origin handoffs
git switch main
```

Check on GitHub that the `handoffs` branch has `README.md`, `STATUS.md`, `TEMPLATE.md`, and `notes/0001...`, `notes/0002...`.

## D. Accounts and keys (free; do later if you are short on time)

- Telegram bot via @BotFather (note token and your chat id) — for alerts.
- Free Indian market-data account (Angel One SmartAPI or Fyers). You do not need to fund it.
- Alpaca paper account (free) for US paper trading.
- Do **not** create live-trading keys now. When you do later: read-only where possible; crypto keys with withdrawals disabled.
- Put real values only in `.env` (git-ignored). Never paste keys into chats or notes.

## E. Start the agents

**Claude Code (first; time-critical).** In the repo folder, start Claude Code and paste:

> Read AGENTS.md, then docs/MASTER_PLAN.md, docs/BUILD_ORDER.md, docs/MODEL_ROLES.md and docs/decisions.md. Then fetch the `handoffs` branch, set up the worktree as described in docs/HANDOFFS.md, and read notes/0001-planning-to-claude-kickoff.md. Execute the P0 Foundation Sprint in priority order. Work on claude/* branches and open PRs; I approve merges. Commit and push often, and before you stop write a handoff note with the exact stopping point. Use the strongest model only for the items marked Fable in docs/BUILD_ORDER.md.

**Codex (CLI >= 0.153.0 if you want Astra).** In the repo folder, start Codex and paste:

> Read AGENTS.md, then docs/MASTER_PLAN.md, docs/BUILD_ORDER.md, docs/MODEL_ROLES.md, docs/TESTING.md and docs/decisions.md. Fetch the `handoffs` branch, set up the worktree per docs/HANDOFFS.md, and read notes/0002-planning-to-codex-kickoff.md. Do the pre-P0 tasks listed there, then wait for Claude's P0 handoff before starting P1. Work on codex/* branches and open PRs; I approve merges. Before you stop, write a handoff note with the exact stopping point.

## F. Your regular routine

1. Open the `handoffs` branch `STATUS.md` to see where things are.
2. Review PRs: read the "Plain-language summary" and "Needs human decision" first. Merge only when CI is green and the other agent has reviewed.
3. Answer `needs-human` notes (edit the note or reply in the PR).

## G. Before going live (much later)

Follow `docs/TESTING.md` §6 and `docs/COMPLIANCE_INDIA.md` §3. In particular: static IP on a cloud VM, a Claude audit of the risk engine (buy one month of Claude Pro or API credit for this), and tiny sizes in approval mode first.

## H. Questions only you can answer (the agents will ask via notes)

Starting capital, which free data broker, crypto exchange, cloud VM provider, sleeve allocations, and risk limits (see `docs/MASTER_PLAN.md` §13).
