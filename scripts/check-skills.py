#!/usr/bin/env python3
"""Enforce the skill authoring rules that plugin validate does not check.

`claude plugin validate --strict` checks the manifest. It says nothing about
whether a SKILL.md will actually be selected at the right moment, which is what
these rules protect:

  1. `description` is present. It is the only required frontmatter key — the
     published spec treats the directory name as authoritative, so `name` is
     optional. Where `name` IS present it must match the directory, since a
     mismatch silently changes how the skill is addressed.
  2. `description` opens with "Use when" — a description that summarizes the
     workflow instead of its triggers gets followed *instead of* the skill body
  3. `description` is under the 1024-character limit
  4. the body stays under 500 words; heavier material belongs in references/
  5. every relative link in the body resolves

Exits non-zero listing every violation, so one run reports all of them.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

SKILLS = Path(__file__).resolve().parent.parent / "skills"
DESCRIPTION_LIMIT = 1024
BODY_WORD_LIMIT = 500


def parse(path: Path) -> tuple[dict[str, str], str]:
    text = path.read_text()
    if not text.startswith("---"):
        raise ValueError("missing YAML frontmatter")
    end = text.index("---", 3)
    raw, body = text[3:end], text[end + 3 :]

    fields: dict[str, str] = {}
    key = None
    for line in raw.splitlines():
        match = re.match(r"^(\w+):\s*(.*)$", line)
        if match:
            key = match.group(1)
            fields[key] = match.group(2).strip().lstrip(">").strip()
        elif key and line.strip():
            fields[key] = (fields[key] + " " + line.strip()).strip()
    return fields, body


def main() -> int:
    problems: list[str] = []

    for directory in sorted(p for p in SKILLS.iterdir() if p.is_dir()):
        skill = directory / "SKILL.md"
        if not skill.exists():
            problems.append(f"{directory.name}: no SKILL.md")
            continue

        try:
            fields, body = parse(skill)
        except ValueError as exc:
            problems.append(f"{directory.name}: {exc}")
            continue

        name = fields.get("name")
        description = fields.get("description", "")

        # `name` is optional per the spec; only check it when the author supplied one.
        if name is not None and name != directory.name:
            problems.append(f"{directory.name}: frontmatter name is {name!r}, expected {directory.name!r}")
        if not description:
            problems.append(f"{directory.name}: description is required")
        if not description.startswith("Use when"):
            problems.append(f"{directory.name}: description must open with 'Use when', got {description[:40]!r}")
        if len(description) > DESCRIPTION_LIMIT:
            problems.append(f"{directory.name}: description is {len(description)} chars, limit {DESCRIPTION_LIMIT}")

        words = len(body.split())
        if words > BODY_WORD_LIMIT:
            problems.append(f"{directory.name}: body is {words} words, limit {BODY_WORD_LIMIT} — move detail to references/")

        for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", body):
            if target.startswith(("http", "#", "mailto:")):
                continue
            if not (skill.parent / target.split("#")[0]).exists():
                problems.append(f"{directory.name}: broken link {target!r}")

    if problems:
        print("Skill check failed:\n")
        for problem in problems:
            print(f"  - {problem}")
        return 1

    count = len([p for p in SKILLS.iterdir() if p.is_dir()])
    print(f"Skill check passed: {count} skills conform")
    return 0


if __name__ == "__main__":
    sys.exit(main())
