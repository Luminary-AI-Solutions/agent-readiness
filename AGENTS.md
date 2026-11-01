# agent-readiness

Two Agent Skills (`SKILL.md` folders) that score how ready a repository is for coding agents and fix the gaps. They're harness-agnostic: plain Markdown instructions plus standard-library Python, with no harness-specific tool names.

## Map
- `skills/agent-readiness/`: the report skill
  - `SKILL.md`: the workflow the agent follows
  - `references/criteria.json`: **single source of truth** for levels, pillars and criteria
  - `scripts/scan.py`: deterministic evidence collection, which writes `draft.json`
  - `scripts/report.py`: merges agent decisions, scores, and renders HTML, markdown and history
  - `assets/report-template.html`: the dashboard (vanilla JS/SVG, no network)
- `skills/agent-readiness-fix/`: the remediation skill, plus an AGENTS.md outline
- `docs/criteria.md`: generated from criteria.json. Don't edit it by hand.
- `examples/`: real reports rendered by the skill
- `tests/`: unittest suite (scoring, merge, end-to-end scan and render)

## Commands
| Task | Command |
|---|---|
| Tests | `python -m unittest discover -s tests -v` |
| Regenerate criteria doc | `python tools/gen_criteria_doc.py` |
| Scan a repo | `python skills/agent-readiness/scripts/scan.py <repo> --out <dir>` |
| Render a provisional report | `python skills/agent-readiness/scripts/report.py <dir>/draft.json --allow-review` |

## Rules
- Scripts must stay **standard library only** and run on Python 3.8+ on Windows, macOS and Linux. CI runs that matrix.
- Adding or changing a criterion: edit `criteria.json`, add a check in `scan.py` (`@check("id")`), then run `tools/gen_criteria_doc.py` and the tests. A criterion without a scanner check falls back to `review`.
- Scanner checks should be conservative. Return `pass` only on clear evidence, return `fail` only when absence is definitive, and use `review` otherwise. The agent resolves `review` items.
- Scoring belongs in `report.py`, never in SKILL.md prose. The model decides verdicts and the script does arithmetic.
- Keep SKILL.md free of harness-specific tool names. Say "run", "read" and "search", not a particular tool's API.
- Dashboard changes: check dark mode, light mode and a 375px-wide viewport. Data is injected at `__READINESS_DATA__`.
