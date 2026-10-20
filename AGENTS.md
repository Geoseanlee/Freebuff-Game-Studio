# FreeBuff Game Studio

This repo is a game studio that runs the CCGS workflow on Freebuff. Read
[`FBGS.md`](FBGS.md) for the full guide.

- **Roles** are skills named after the CCGS agents: `producer`,
  `creative-director`, `game-designer`, `lead-programmer`,
  `gameplay-programmer`, `qa-lead`, engine specialists, and 40 more.
- **Workflow steps** are skills named after the CCGS commands: `brainstorm`,
  `design-system`, `gate-check`, `dev-story`, `code-review`, `perf-profile`,
  `release-checklist`, and so on.
- All of them live in `.freebuff/skills/` and are exposed to Freebuff through
  `.agents/skills/`.

When the user writes `FBGS: <role>` or `/fbgs`, names a role
(`FBGS: gameplay-programmer ...`), or asks for studio work:

1. Load the `fbgs` skill with the `skill` tool (or the named role skill
   directly) before replying.
2. Then follow that skill's instructions and `FBGS.md`.

Example: `FBGS: producer 帮我排下个 sprint` means load the `producer` skill
and the `sprint-plan` workflow skill, then act as the producer.

This repo is a fork of CCGS: `.claude/` is upstream and untouched, `.freebuff/`
is generated from it. After merging upstream, run
`python3 scripts/fbgs.py sync` (never hand-edit `.freebuff/`).

Do not invent studio process from memory: the CCGS docs in `.freebuff/docs/`
are authoritative. `project.yaml` is the project's configuration; when a skill
says to resolve config, run
`bash .freebuff/hooks/yaml-helper.sh resolve_config --keys <keys>`.

Only `researcher-web` is spawnable as a true subagent in Freebuff Desktop.
Everything else is done by loading the relevant role or workflow skill.
