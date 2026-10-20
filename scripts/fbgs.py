#!/usr/bin/env python3
"""Sync Claude-Code-Game-Studios (.claude) into this repo's .freebuff tree.

Usage:
  python3 scripts/fbgs.py sync                      # sync from this repo's .claude
  python3 scripts/fbgs.py sync --source /path/ccgs  # or from another CCGS checkout
  python3 scripts/fbgs.py check                     # validate + detect drift

Freebuff discovers project skills in .agents/skills (and .claude/skills), so
this repo keeps the source of truth in .freebuff/skills and links
.agents/skills -> ../.freebuff/skills. Freebuff Desktop 0.0.180 passes its own
agent definitions and never calls loadLocalAgents(), so repo .agents/*.ts
agents are ignored there; CCGS agents therefore ship as role skills, which the
model loads by name with the `skill` tool.
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEST = ROOT / ".freebuff"
CLAUDE = ROOT / ".claude"
SKILL_LINK = ROOT / ".agents" / "skills"

TEXT_SUFFIXES = {
    ".md", ".sh", ".json", ".yaml", ".yml", ".txt", ".gd", ".awk",
    ".py", ".toml", ".js", ".ts", ".css", ".html",
}
COPY_DIRS = ("agents", "skills", "docs", "hooks", "scripts", "rules")
COPY_FILES = ("settings.json", "statusline.sh")

# Hand-written FBGS files (relative to the .freebuff root): never rewritten by
# sync, so their mapping tables can still name the Claude originals.
KEEP_AS_IS = {
    Path("skills/fbgs/SKILL.md"),
    Path("docs/freebuff-port.md"),
}
# Runtime artifact written by Freebuff, not port source.
LOCAL_ONLY = {Path("project-id")}

NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
DESC_MAX = 1024

ROLE_NOTE = """> **FBGS role agent.** This role runs inside the current Freebuff conversation,
> not in an isolated subagent: you own this role's decisions and artifacts and
> hand back a short report when done. Ask the user before writing files when
> the role protocol below says so. In Freebuff Desktop the only spawnable
> helper is `researcher-web`; do everything else yourself. Tool-name and
> workflow differences are listed in `.freebuff/docs/freebuff-port.md`.
"""

PROJECT_VAR_LINE = (
    'FREEBUFF_PROJECT_DIR="${FREEBUFF_PROJECT_DIR:-'
    '$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"\n'
)


def transform(text: str, shell: bool) -> str:
    """Rewrite Claude-Code paths and shell preambles for Freebuff."""
    if shell and "FREEBUFF_PROJECT_DIR" not in text:
        match = re.match(r"^(#!.*\n)", text)
        if match:
            text = text[: match.end()] + PROJECT_VAR_LINE + text[match.end() :]
        else:
            text = PROJECT_VAR_LINE + text

    text = text.replace("${CLAUDE_SKILL_DIR}/../../hooks/", ".freebuff/hooks/")
    text = text.replace("${CLAUDE_SKILL_DIR}/../../scripts/", ".freebuff/scripts/")
    text = text.replace("${CLAUDE_SKILL_DIR}/../../", ".freebuff/")
    text = text.replace("${CLAUDE_PROJECT_DIR}", "$FREEBUFF_PROJECT_DIR")
    text = text.replace("$CLAUDE_PROJECT_DIR", "$FREEBUFF_PROJECT_DIR")
    text = text.replace("CLAUDE_PROJECT_DIR", "FREEBUFF_PROJECT_DIR")
    text = text.replace("${CLAUDE_SKILL_DIR}", "<skill-dir>")
    text = text.replace("$CLAUDE_SKILL_DIR", "<skill-dir>")
    text = text.replace("CLAUDE_SKILL_DIR", "<skill-dir>")
    text = text.replace(".claude/", ".freebuff/")
    text = text.replace(".claude", ".freebuff")
    text = text.replace("CLAUDE.md", "FBGS.md")
    # Tool names Freebuff does not have; map to the equivalents it does.
    text = text.replace("AskUserQuestion", "ask_questions")
    text = text.replace("WebSearch", "web_search")
    text = text.replace("$ARGUMENTS", "the user's request")

    lines = []
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("!`") and stripped.endswith("`"):
            command = stripped[2:-1]
            lines.append(
                "> **Run first in Freebuff:** `"
                + command
                + "` — use its output as-is. If it prints nothing, apply the "
                "defaults in `.freebuff/docs/config-resolution.md`."
            )
        else:
            lines.append(line)
    return "\n".join(lines)


def frontmatter_span(text: str) -> tuple[int, int] | None:
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---\n", 4)
    if end == -1:
        return None
    return 4, end


def parse_frontmatter(text: str) -> dict[str, str]:
    span = frontmatter_span(text)
    if span is None:
        return {}
    data: dict[str, str] = {}
    for line in text[span[0] : span[1]].splitlines():
        if not line or line[0].isspace() or ":" not in line:
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip().strip('"').strip("'")
    return data


def write_skill(path: Path, text: str) -> None:
    # Freebuff has no user-invocable slash commands, so hiding a skill from the
    # model would make it unreachable there.
    text = re.sub(r"^disable-model-invocation:\s*true\s*\n", "", text, flags=re.M)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def sync(source: Path, dest: Path = DEST, make_link: bool = True) -> None:
    claude = source / ".claude" if (source / ".claude").is_dir() else source
    if not (claude / "skills").is_dir():
        sys.exit(f"no skills directory under {claude}")

    for name in COPY_DIRS:
        src = claude / name
        if src.is_dir():
            shutil.copytree(src, dest / name, dirs_exist_ok=True)
    for name in COPY_FILES:
        src = claude / name
        if src.is_file():
            shutil.copy2(src, dest / name)

    # Rewrite every text file that came from CCGS. Hand-written FBGS files are
    # left alone: they never contain a .claude path to begin with.
    keep = {dest / rel for rel in KEEP_AS_IS}
    for path in dest.rglob("*"):
        if path in keep:
            continue
        if path.is_file() and path.suffix in TEXT_SUFFIXES:
            text = path.read_text(encoding="utf-8")
            rewritten = transform(text, shell=path.suffix == ".sh")
            if path.name == "SKILL.md":
                rewritten = re.sub(
                    r"^disable-model-invocation:\s*true\s*\n",
                    "",
                    rewritten,
                    flags=re.M,
                )
            if rewritten != text:
                path.write_text(rewritten, encoding="utf-8")

    # One role skill per CCGS agent definition.
    agents = sorted((claude / "agents").glob("*.md"))
    if not agents:
        sys.exit(f"no agent definitions under {claude / 'agents'}")
    for agent in agents:
        name = agent.stem
        text = transform(agent.read_text(encoding="utf-8"), shell=False)
        span = frontmatter_span(text)
        if span is None:
            sys.exit(f"{agent} has no frontmatter")
        text = text[: span[1] + 5] + "\n" + ROLE_NOTE + "\n" + text[span[1] + 5 :]
        write_skill(dest / "skills" / name / "SKILL.md", text)

    if not make_link:
        return
    SKILL_LINK.parent.mkdir(parents=True, exist_ok=True)
    if SKILL_LINK.is_symlink() or SKILL_LINK.exists():
        if not SKILL_LINK.is_symlink():
            sys.exit(f"{SKILL_LINK} exists and is not a symlink")
        SKILL_LINK.unlink()
    SKILL_LINK.symlink_to("../.freebuff/skills")

    print(
        f"synced {len(agents)} role skills, "
        f"{len(list((dest / 'skills').iterdir()))} skills total"
    )


def drift() -> list[str]:
    """Report `.freebuff` files that no longer match the repo's `.claude`.

    Runs the exact sync pipeline into a scratch directory and diffs the result,
    so it catches both stale generated files and files added upstream. Only
    meaningful in a checkout that carries `.claude` (this fork does).
    """
    if not (CLAUDE / "skills").is_dir():
        return []
    with tempfile.TemporaryDirectory() as tmp:
        scratch = Path(tmp) / ".freebuff"
        for rel in KEEP_AS_IS:
            if (DEST / rel).is_file():
                (scratch / rel).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(DEST / rel, scratch / rel)
        try:
            sync(ROOT, dest=scratch, make_link=False)
        except SystemExit:
            return []
        return _tree_diff(scratch, DEST)


def _tree_diff(expected: Path, actual: Path) -> list[str]:
    def files(base: Path) -> set[Path]:
        return {
            path.relative_to(base)
            for path in base.rglob("*")
            if path.is_file() and path.relative_to(base) not in LOCAL_ONLY
        }

    want, have = files(expected), files(actual)
    problems = [f".freebuff/{rel} is missing (run sync)" for rel in sorted(want - have)]
    problems += [f".freebuff/{rel} is stale (run sync)" for rel in sorted(have - want)]
    for rel in sorted(want & have):
        if (expected / rel).read_bytes() != (actual / rel).read_bytes():
            problems.append(f".freebuff/{rel} differs from .claude (run sync)")
    return problems


def check() -> int:
    errors: list[str] = []

    def fail(message: str) -> None:
        errors.append(message)

    for root_file in ("FBGS.md", "AGENTS.md"):
        if not (ROOT / root_file).is_file():
            fail(f"missing {root_file}")

    if not SKILL_LINK.is_symlink():
        fail(f"{SKILL_LINK.relative_to(ROOT)} must be a symlink to ../.freebuff/skills")
        return report(errors)
    if SKILL_LINK.resolve() != (DEST / "skills").resolve():
        fail(f"{SKILL_LINK.relative_to(ROOT)} points at the wrong directory")

    skills = sorted(path for path in SKILL_LINK.iterdir() if path.is_dir())
    names: set[str] = set()
    for skill_dir in skills:
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.is_file():
            fail(f"{skill_dir.name}: missing SKILL.md")
            continue
        text = skill_file.read_text(encoding="utf-8")
        meta = parse_frontmatter(text)
        name, description = meta.get("name", ""), meta.get("description", "")
        if name != skill_dir.name:
            fail(f"{skill_dir.name}: frontmatter name is {name!r}")
        if not NAME_RE.match(name) or len(name) > 64:
            fail(f"{skill_dir.name}: invalid skill name {name!r}")
        if not description:
            fail(f"{skill_dir.name}: empty description")
        elif len(description) > DESC_MAX:
            fail(f"{skill_dir.name}: description is {len(description)} chars")
        names.add(skill_dir.name)

        for marker in (
            ".claude",
            "CLAUDE_SKILL_DIR",
            "CLAUDE_PROJECT_DIR",
            "AskUserQuestion",
            "$ARGUMENTS",
        ):
            if marker in text:
                fail(f"{skill_dir.name}: still references {marker}")
        if any(line.lstrip().startswith("!`") for line in text.splitlines()):
            fail(f"{skill_dir.name}: unrendered shell preamble")

        for ref in re.findall(
            r"\.freebuff/(?:scripts|hooks)/[A-Za-z0-9_.-]+", text
        ):
            if not (ROOT / ref).exists():
                fail(f"{skill_dir.name}: missing referenced file {ref}")

    roster = DEST / "docs" / "agent-roster.md"
    if roster.is_file():
        roles = sorted(
            set(
                re.findall(
                    r"^\| `([a-z0-9-]+)`",
                    roster.read_text(encoding="utf-8"),
                    flags=re.M,
                )
            )
        )
        for role in roles:
            if role not in names:
                fail(f"roster role {role} has no skill")
    else:
        fail("missing .freebuff/docs/agent-roster.md")

    if "fbgs" not in names:
        fail("missing the fbgs dispatcher skill")

    # The original CCGS agent files stay as reference copies, and every one
    # must have a matching runnable role skill.
    agent_files = sorted((DEST / "agents").glob("*.md"))
    if len(agent_files) != 49:
        fail(f"expected 49 agent files, found {len(agent_files)}")
    for agent_file in agent_files:
        if agent_file.stem not in names:
            fail(f"agent {agent_file.stem} has no role skill")

    # A fork carries upstream `.claude`, so also prove `.freebuff` is current.
    pending = drift()
    for problem in pending:
        fail(problem)

    print(
        f"checked {len(skills)} skills ({len(names)} unique names), "
        f"{len(agent_files)} agent files"
        + (f", {len(pending)} drift" if CLAUDE.is_dir() else "")
    )
    return report(errors)


def report(errors: list[str]) -> int:
    if errors:
        print(f"{len(errors)} problem(s):", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1
    print("ok")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sync_parser = sub.add_parser("sync", help="copy CCGS .claude into .freebuff")
    sync_parser.add_argument(
        "--source",
        default=str(ROOT),
        help="CCGS checkout (default: this repo, whose .claude is upstream CCGS)",
    )
    sub.add_parser("check", help="validate the Freebuff skill contract and drift")
    args = parser.parse_args()

    if args.command == "sync":
        sync(Path(args.source).expanduser().resolve())
        return 0
    return check()


if __name__ == "__main__":
    sys.exit(main())
