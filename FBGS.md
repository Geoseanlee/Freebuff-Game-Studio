# FreeBuff Game Studio (FBGS)

This repository runs the [Claude Code Game Studios](https://github.com/Donchitos/Claude-Code-Game-Studios)
(CCGS) game-development workflow on Freebuff. The studio's 49 agents and 74
workflow skills from CCGS live in `.freebuff/`, and Freebuff loads them as
project skills in every conversation.

Say **`FBGS: <role>`** (or just ask naturally) to put a role to work:

```
FBGS: producer 帮我把这个里程碑拆成 sprint
FBGS: gameplay-programmer 实现二段跳，遵守项目编码规范
FBGS: gate-check 我们能不能进入 production？
/fbgs 我想做一个类吸血鬼幸存者的原型
```

## How the port works

This repo is a **fork of CCGS**, so it carries two layers:

| Layer | Path | Role |
|---|---|---|
| Upstream | `.claude/` | Byte-for-byte CCGS. Never hand-edited here; it is what `git merge upstream/main` updates. |
| Freebuff | `.freebuff/` | Generated from `.claude/` by `python3 scripts/fbgs.py sync`. This is what runs. |

Freebuff discovers project skills in `.agents/skills/<name>/SKILL.md`, so the
generated tree is linked into that path:

```
.freebuff/skills  <--  .agents/skills      (symlink)
```

Never edit `.freebuff/` by hand: edit `.claude/` (or `FBGS.md`, `AGENTS.md`,
the `fbgs` skill, and `.freebuff/docs/freebuff-port.md`, which `sync` leaves
alone) and re-run sync. `python3 scripts/fbgs.py check` fails when the generated
tree has drifted from `.claude/`.

Every skill is a directory with a `SKILL.md`; Freebuff injects each skill's
name and description into the conversation, and the agent loads the full file
on demand with the `skill` tool. That is why a new conversation immediately
knows the whole studio.

**Two deliberate mappings:**

1. **CCGS agents → role skills.** Freebuff Desktop 0.0.180 passes its own
   agent roster into the runtime and never loads repo `.agents/*.ts` agent
   definitions (only the `freebuff --trust-agents` CLI does). So each of the 49
   CCGS agents is ported to a skill with the same name — `producer`,
   `gameplay-programmer`, `ue-gas-specialist`, and so on. The full role prompt
   is preserved, and the original CCGS files also stay as reference copies in
   `.freebuff/agents/` so the ported studio tooling still finds them.
2. **CCGS `/commands` → skill names.** Freebuff has no slash-command registry;
   `/code-review` in a message is a convention that names the `code-review`
   skill. Write it with or without the leading slash.

## The two layers

**Roles — who does the work** (49). Load a role skill before doing that role's
work; the reply should say which role is acting.

| Group | Roles |
|---|---|
| Leadership | `creative-director` `technical-director` `producer` |
| Department leads | `game-designer` `lead-programmer` `art-director` `audio-director` `narrative-director` `qa-lead` `release-manager` `localization-lead` |
| Design | `systems-designer` `level-designer` `economy-designer` `ux-designer` `world-builder` `writer` `live-ops-designer` `accessibility-specialist` |
| Programming | `gameplay-programmer` `engine-programmer` `ai-programmer` `network-programmer` `tools-programmer` `ui-programmer` `technical-artist` `prototyper` `security-engineer` `devops-engineer` `analytics-engineer` `performance-analyst` |
| Production / QA / community | `qa-tester` `sound-designer` `community-manager` |
| Engine leads | `godot-specialist` `unity-specialist` `unreal-specialist` |
| Godot specialists | `godot-gdscript-specialist` `godot-csharp-specialist` `godot-shader-specialist` `godot-gdextension-specialist` |
| Unity specialists | `unity-dots-specialist` `unity-shader-specialist` `unity-addressables-specialist` `unity-ui-specialist` |
| Unreal specialists | `ue-gas-specialist` `ue-blueprint-specialist` `ue-replication-specialist` `ue-umg-specialist` |

**Workflow skills — what to do next** (74). The phase ladder, from
`.freebuff/docs/workflow-catalog.yaml`:

| Phase | Typical skills |
|---|---|
| Concept | `brainstorm` `quick-design` `project-stage-detect` `scope-check` |
| Systems Design | `map-systems` `design-system` `design-review` `review-all-gdds` `consistency-check` `art-bible` |
| Technical Setup | `setup-engine` `create-architecture` `architecture-decision` `architecture-review` `create-control-manifest` `test-setup` |
| Pre-Production | `prototype` `vertical-slice` `create-epics` `create-stories` `sprint-plan` `ux-design` `ux-review` `asset-spec` |
| Production | `story-readiness` `dev-story` `code-review` `story-done` `qa-plan` `bug-report` `sprint-status` `retrospective` `estimate` `tech-debt` |
| Polish | `perf-profile` `balance-check` `asset-audit` `playtest-report` `team-polish` `security-audit` `test-flakiness` `regression-suite` |
| Release | `localize` `release-checklist` `changelog` `patch-notes` `launch-checklist` `team-release` `hotfix` `day-one-patch` |
| Always available | `help` `start` `onboard` `settings` `adopt` `gate-check` `milestone-review` `localize` `skill-improve` `skill-test` |

`help` is the cheapest way to orient: it reads `project.yaml`,
`production/stage.txt` and the workflow catalog and says what comes next.

## Working rules for a session

1. Load `fbgs` first for a studio-wide request, or the named role skill for a
   role request. Load the phase skill too when the task is a gate, review,
   sprint, or release step.
2. Announce the role(s) in one line, then work. Chain roles sequentially for a
   large task (for example `game-designer` → `systems-designer` →
   `gameplay-programmer` → `code-review`), handing each one a short brief.
3. Roles share this conversation, not separate contexts. Only `researcher-web`
   is a true spawnable subagent in Freebuff Desktop; use it for external
   research and do everything else yourself.
4. Ask before writing files when a role protocol says to ask. The studio's
   collaboration rules still apply.
5. Skills that need project config start with a **Run first in Freebuff** line
   (Freebuff has no shell preprocessing). Run that command with
   `run_terminal_command` and use its output.
6. Verdicts such as `PASS / CONCERNS / NOT ASSESSED / FAIL` are advisory; the
   user decides.

## Files

| Path | What it is |
|---|---|
| `AGENTS.md` | Always-loaded entry point; routes a request to `fbgs` |
| `FBGS.md` | This guide |
| `.claude/` | Upstream CCGS, untouched; the source `sync` reads |
| `.freebuff/skills/` | 49 role skills + 74 workflow skills + `fbgs` (generated) |
| `.freebuff/agents/` | Original CCGS agent files (reference; runtime uses the role skills) |
| `.freebuff/docs/` | CCGS docs (roster, workflow catalog, coding standards, rules reference, …) |
| `.freebuff/rules/` | CCGS coding rules by domain |
| `.freebuff/hooks/`, `.freebuff/scripts/` | CCGS helpers, callable on demand |
| `.freebuff/settings.json` | Reference copy of CCGS settings; Freebuff does not run Claude hooks |
| `.freebuff/docs/freebuff-port.md` | Every known difference from Claude Code |
| `scripts/fbgs.py` | Sync from a CCGS checkout and validate the port |

## Refresh from upstream CCGS

Upstream changes arrive through `.claude/`, then get ported:

```bash
git fetch upstream
git merge upstream/main          # resolve conflicts in .claude/ only
python3 scripts/fbgs.py sync     # regenerate .freebuff from .claude
python3 scripts/fbgs.py check    # frontmatter + roster + drift
```

A port from any other checkout works too, without merging:

```bash
python3 scripts/fbgs.py sync --source /path/to/Claude-Code-Game-Studios
```

`sync` rewrites `.claude/` paths to `.freebuff/`, converts agent definitions to
role skills, and recreates the `.agents/skills` symlink. It never overwrites the
hand-written `fbgs` skill, this guide, or `AGENTS.md`. Because the fork keeps
`.claude/` in the tree, `sync` with no `--source` reads it directly.

## Limits worth knowing

- New skills are listed from a **new conversation** onward (the session state is
  built when a conversation starts). In an existing conversation the agent can
  still load one by name if you name it.
- Claude Code features with no Freebuff equivalent are documented rather than
  emulated: automatic hooks, `settings.json` permissions, per-agent
  `model`/`tools`/`maxTurns`/`memory`, `AskUserQuestion` UI, and isolated
  subagent context. See `.freebuff/docs/freebuff-port.md`.
- `.freebuff/` and `.agents/` must be committed and not gitignored, or the
  studio disappears for every other checkout. If a host cannot follow the
  `.agents/skills` symlink (some sandboxes), replace it with a real copy of
  `.freebuff/skills` and re-run `scripts/fbgs.py check`.
