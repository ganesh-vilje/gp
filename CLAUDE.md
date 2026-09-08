# panchayat-complaint-tracker

This project is run by the **AI Engineering Organization** installed in
`~/.claude` (agents, skills, hooks). Project-specific state lives in `.ai/`.

## Start of every session
1. Read `.ai/project-state/project-state.md` — `current_phase` and
   `gates_passed` decide what you are allowed to do.
2. Read `.claude/project-config.md` for stack, commands and environments.
3. Do not read the rest of `.ai/` wholesale — each phase skill tells you what to load.

## Non-negotiable rules
- Application code is written only after `GATE_6`. A hook enforces this; do not
  try to work around it.
- Reviewers return verdicts; they never edit. Producers never approve their own work.
- Every claim of "works / passes / secure" cites evidence (test output, file:line).
- Human gates are presented in one message, per `~/.claude/ai-org/references/gates.md`.
- No secrets in any file. No force-push, history rewrite, destructive SQL, or
  production deploy — the human does those.

## Commands
`/status` · `/requirements` · `/tech-stack` · `/ux` · `/architecture` · `/plan`
· `/build` · `/test-app` `/smoke-test` `/regression-test` (app-qa skill) ·
`/release`
