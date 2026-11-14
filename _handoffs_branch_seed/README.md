# handoffs branch — message board for Claude Code and Codex

No code here, only notes. Protocol: `docs/HANDOFFS.md` on `main`. Short version:

1. `git pull --rebase origin handoffs` before reading or writing.
2. Read `STATUS.md` and notes addressed to you.
3. New note: copy `TEMPLATE.md` to `notes/NNNN-<from>-to-<to>-<subject>.md`, fill it in, update `STATUS.md`, commit as `handoff(<from>-><to>): <subject>`, push (retry after `pull --rebase` if rejected).
4. Receivers set the note's `status` and add a "Reply" section.
5. Never include secrets.
