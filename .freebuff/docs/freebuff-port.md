# FBGS port notes — what changed from Claude Code

The CCGS `.claude` tree was migrated mechanically by `scripts/fbgs.py`. This
file lists every known difference so a role does not assume a feature that
Freebuff Desktop 0.0.180 does not have.

## Discovery

| CCGS / Claude Code | FBGS |
|---|---|
| `.claude/skills/<name>/SKILL.md` | `.freebuff/skills/<name>/SKILL.md`, linked as `.agents/skills` |
| `.claude/agents/<name>.md` subagents | `.freebuff/skills/<name>/SKILL.md` role skills; the original files are kept in `.freebuff/agents/` for reference and tooling |
| Project `CLAUDE.md` | `AGENTS.md` (auto-loaded) + `FBGS.md` (guide) |
| `/command` slash commands | the skill named `command`; write `/command` or `command` in a message |
| `${CLAUDE_SKILL_DIR}` shell substitution | `<skill-dir>` in text; the `skill` tool loads by name |
| `${CLAUDE_PROJECT_DIR}` | `$FREEBUFF_PROJECT_DIR`, set by the ported shell scripts |

### The fork still ships `.claude/`

This repo keeps upstream CCGS in `.claude/`, so Freebuff's loader reads
`{cwd}/.claude/skills` first and `{cwd}/.agents/skills` second, the later
directory winning per name. That is harmless today — every one of the 74
`.claude/skills` names also exists in `.freebuff/skills` (49 role skills + 74
workflow skills + `fbgs` = 124), so the ported copy always wins — but it means
a skill added upstream is briefly visible in its unported form until
`scripts/fbgs.py sync` runs. Sync after every upstream merge.

Freebuff's skill parser accepts `name`, `description`, `license`,
`disable-model-invocation`, and `metadata`. Other frontmatter keys in the
migrated files (`argument-hint`, `allowed-tools`, `model`, `user-invocable`,
`tools`, `maxTurns`, `memory`, `isolation`, `skills`) are preserved for
reference and ignored at runtime. `disable-model-invocation` was removed because
Freebuff has no user-only invocation path — a hidden skill would be unreachable.

## Tools

| CCGS name | Freebuff equivalent |
|---|---|
| `Read` | `read_files` |
| `Glob` | `glob` |
| `Grep` | `code_search` |
| `Write` / `Edit` | `write_file` / `str_replace` |
| `Bash` | `run_terminal_command` |
| `WebSearch` | `web_search` |
| `AskUserQuestion` | `ask_questions`, or a plain question in prose |
| `Agent(...)` / `Task(...)` | `spawn_agents` (Desktop exposes `researcher-web` only) |
| `Skill(name)` | `skill` tool with `{ "name": ... }` |

The migrated text still names the Claude tools. Read them as the Freebuff
equivalent above; do not claim a tool that is not in the current tool set.

## Behavior gaps

1. **No shell preprocessing.** A CCGS skill beginning with
   ``!`bash ...` `` had that command executed before the model saw the skill.
   Freebuff does not do this. The line was rewritten to
   **Run first in Freebuff:** — run it yourself and use the output.
2. **No automatic hooks.** `.freebuff/settings.json` is a reference copy.
   Session-start, pre/post-tool, subagent and stop hooks do not fire. The
   `.freebuff/hooks/` scripts still run when a skill or a person calls them.
3. **No permission settings.** Freebuff's own approval flow applies;
   `.freebuff/settings.json` permissions are inert.
4. **No isolated role contexts.** A role skill runs in the main conversation.
   Roles are sequential handoffs, not parallel workers, and they share context.
   Only `researcher-web` is spawnable as a true subagent in Desktop 0.0.180.
5. **No per-agent model or tool grant.** `model: opus`, `tools:`,
   `maxTurns:`, `memory:` and `isolation:` are informational. The session model
   and tool set apply.
6. **No user-only skills.** `disable-model-invocation` was removed; every skill
   is model-invocable.
7. **Agent fan-out in the workflow is advisory.** Director-gate and team skills
   describe multiple specialists reviewing in parallel. In FBGS, load those role
   skills one after another, or state which reviews were skipped and why. Do not
   fake a multi-agent verdict.
8. **New skills appear in new conversations.** Session state is built when a
   conversation starts. In an existing conversation, name the skill and the
   agent can still load it from disk; otherwise start a new conversation.

## What did not change

- `project.yaml`, `production/`, `design/` and the artifact conventions.
- `resolve_config` and the `.freebuff/hooks`/`.freebuff/scripts` helpers; they
  run under bash and Python 3 exactly as before.
- CCGS coding rules in `.freebuff/rules/` and the standards in
  `.freebuff/docs/`.
- The collaboration model: options first, user decides, ask before writes.

## Maintenance

`scripts/fbgs.py sync` is idempotent: it re-copies CCGS content, regenerates
role skills, and rewrites paths. It leaves hand-written `fbgs`, `FBGS.md`,
`AGENTS.md`, and this file alone. With no `--source` it reads this repo's own
`.claude/`, so the fork is self-contained.

`scripts/fbgs.py check` validates the loader contract: frontmatter,
name/directory match, description length, no stale `.claude` paths, referenced
helper files, and roster coverage. It also re-runs the whole sync pipeline into
a scratch directory and diffs the result, so `check` fails on any `.freebuff`
file that is stale, missing, or orphaned relative to `.claude`.
