# CLAUDE.md

@AGENTS.md

(If your tool does not expand `@` imports, open `AGENTS.md` and read it fully first. It contains the project rules.)

## Claude-specific notes

- Model routing and plan limits: `docs/MODEL_ROLES.md`. Use `/model` to choose. Use the strongest model only for the items marked "Fable" in `docs/BUILD_ORDER.md`; it drains usage limits fast.
- **Time-boxed start:** the owner's Claude Pro plan is short-lived (it ends around 2026-11-16; Fable 5.2 inclusion ends 2026-11-16 11:59 pm PT, about 1:30 pm IST on 2026-11-17). Your first job is the **P0 Foundation Sprint** in `docs/BUILD_ORDER.md` and handoff note `0001`. Produce specs, contracts, scaffolding and test specifications that the OpenAI models (Codex) can implement against after Claude access ends.
- Write down decisions in `docs/decisions.md` as you go. After this sprint nobody can ask you "why".
- Finish every session by pushing your branch and writing a handoff note.
- When writing lessons for the owner, keep the tone of a patient teacher for a smart beginner.
