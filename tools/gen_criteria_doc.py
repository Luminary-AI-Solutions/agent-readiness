#!/usr/bin/env python3
"""Generate docs/criteria.md from the skill's criteria.json (the single source of truth).

    python tools/gen_criteria_doc.py          # write docs/criteria.md
    python tools/gen_criteria_doc.py --check  # exit 1 if it is out of date
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "skills" / "agent-readiness" / "references" / "criteria.json"
OUT = ROOT / "docs" / "criteria.md"


def render():
    data = json.loads(SRC.read_text(encoding="utf-8"))
    pillars = {p["id"]: p for p in data["pillars"]}
    lines = ["# Criteria", "",
             f"<!-- Generated from {SRC.relative_to(ROOT).as_posix()} by tools/gen_criteria_doc.py. Do not edit. -->", "",
             f"{len(data['criteria'])} criteria across {len(data['pillars'])} pillars and {len(data['levels'])} levels. "
             f"A level unlocks when {round(data['threshold'] * 100)}% of the previous level's applicable criteria pass.", ""]
    for lv in data["levels"]:
        items = [c for c in data["criteria"] if c["level"] == lv["level"]]
        lines += [f"## Level {lv['level']}: {lv['name']}", "", lv["summary"], "",
                  "| Criterion | Pillar | Scope | Difficulty | Passes when |", "|---|---|---|---|---|"]
        for c in sorted(items, key=lambda c: list(pillars).index(c["pillar"])):
            lines.append(f"| **{c['name']}**<br>`{c['id']}` | {pillars[c['pillar']]['name']} | {c['scope']} | "
                         f"{c['difficulty']} | {c['pass'].replace('|', '/')} |")
        lines.append("")
    lines += ["## Pillars", ""] + [f"- **{p['name']}**: {p['why']}" for p in data["pillars"]] + [""]
    return "\n".join(lines)


if __name__ == "__main__":
    text = render()
    if "--check" in sys.argv:
        current = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
        if current != text:
            sys.exit("docs/criteria.md is out of date; run python tools/gen_criteria_doc.py")
        print("docs/criteria.md is up to date")
    else:
        OUT.parent.mkdir(exist_ok=True)
        OUT.write_text(text, encoding="utf-8", newline="\n")
        print(f"wrote {OUT.relative_to(ROOT)}")
