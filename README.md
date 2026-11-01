# agent-readiness

**Is your repo ready for coding agents?** Two open [Agent Skills](https://agentskills.io):

- **`agent-readiness`** scores a repository on five levels of agent readiness and renders a dashboard you'll actually want to share.
- **`agent-readiness-fix`** helps you close the gaps your way. The small fixes are automatic; the real decisions stay yours.

They work in **Claude Code, OpenAI Codex, Cursor, GitHub Copilot, Google Antigravity, OpenCode, Cline and Factory Droid**.

![Agent readiness dashboard](docs/dashboard.png)

When agents underperform, the cause is usually the codebase rather than the model. Without hooks, an agent waits ten minutes for CI to report a lint error it could have caught in a second. Undocumented environment variables leave it guessing. Builds that rely on tribal knowledge leave it no way to verify its own work. This skill measures those gaps and ranks what to fix first.

## What it measures

**93 checks across 9 pillars**, gated into **5 levels**:

| Level | Name | What it means | Example checks |
|---|---|---|---|
| 1 | Functional | Code runs and basic tooling exists | README, linter, type checker, lockfile, tests that exit on their own |
| 2 | Documented | Workflows are written down; local guardrails exist | AGENTS.md, single-test command, pre-commit hooks, env template, devcontainer, branch protection |
| 3 | Standardized | Processes are enforced by automation | lean and accurate agent instructions, integration tests, guardrails in config, secret scanning, logs an agent can read |
| 4 | Optimized | Feedback is fast and measured | CI under 10 minutes, agent hooks, browser automation, parallel-agent isolation, flaky-test detection |
| 5 | Autonomous | The system checks and improves itself | verified agent instructions, progressive rollout, errors that become tasks |

A level unlocks when **80%** of the previous level's applicable criteria pass. Pillars: Style & Validation, Build System, Testing, Documentation, Dev Environment, Debugging & Observability, Security & Governance, Task Discovery, Product & Experimentation. The full list, with pass rules, is in [docs/criteria.md](docs/criteria.md).

### Grounded in 2025–26 research

The level model comes from [Factory's Agent Readiness Model](https://docs.factory.com/agent-readiness/overview). The newer criteria come from what labs and researchers have published since:

- **Lean, hand-maintained agent instructions.** LLM-generated context files raised agent cost by more than 20% without improving success, and repository overviews didn't help ([Gloaguen et al., ETH Zürich, 2026](https://arxiv.org/abs/2602.11988)). The rubric checks that AGENTS.md is short and that the paths it names actually exist.
- **Guardrails in config, not prose.** Only about 4–16% of the security rules in 481 public CLAUDE.md files had a matching enforced control ([Yan, 2026](https://arxiv.org/abs/2608.23550)). The rubric checks for committed permission and sandbox settings and agent hooks.
- **Agents that can see the running app.** Agents declared features done after unit checks until they could drive a browser ([Anthropic, 2025](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)). The rubric checks for browser automation on web apps.
- **Parallel-agent friendliness, readable logs, plans in the repo, MCP hygiene, owners for agent config.** These draw on guidance from OpenAI, GitHub, Cursor, Simon Willison's ["lethal trifecta"](https://simonwillison.net/2025/Jun/16/the-lethal-trifecta/) and others.

## How it works

```
scan.py ──► draft.json ──► your agent decides ──► decisions.json ──► report.py ──► report.html
(files, configs,         (93 provisional       (judgment calls,                 summary.md
 git history, gh)         verdicts)             one line of evidence each)      history.jsonl
```

1. **A deterministic scan** collects evidence: config files, dependencies, CI workflows, git history, and the platform CLI (`gh`) for branch protection, CI timing, labels and issues. It returns a provisional verdict for every criterion and marks the judgment calls as `review`.
2. **Your agent** resolves the `review` items, checks the scanner's other verdicts against the actual files, and writes a one-line rationale for each decision.
3. **A script does the scoring.** The model never does arithmetic. Each run is grounded on the previous report, so verdicts only change when the evidence does.

The scripts are standard-library Python 3.10+ with nothing to install. The dashboard is a single HTML file that works offline.

## Fix it your way

`agent-readiness-fix` sorts every failing criterion into one of three lanes:

| Lane | Examples | What happens |
|---|---|---|
| **Auto-fix** | PR/issue templates, `.env.example`, `.gitignore` gaps, missing lockfile, single-test command, CI caching | Applied after one confirmation, then verified |
| **Your call** | linter and formatter, hook runner, strict typing, test strategy, logging stack, feature flags, agent guardrails | The agent lays out 2–4 options with trade-offs and a recommendation; you pick; it implements your pick, staged so nothing goes red unannounced |
| **Manual** | branch protection, platform secret scanning, CLI auth | Exact steps and commands for you to run |

It writes an editable `fix-plan.md`. It saves your choices to `preferences.json`, along with **waivers** for criteria that don't apply to your team, such as analytics in an internal tool, so future reports respect them. It never signs up for services, adds keys, or pushes. A [decision playbook](skills/agent-readiness-fix/references/playbook.md) holds the options per criterion.

## Install

With the [`skills` CLI](https://github.com/vercel-labs/skills) (Node 22+), which detects your installed agents:

```bash
npx skills add Luminary-AI-Solutions/agent-readiness
```

To target specific agents, pass `-a` once per agent. Add `-g` for a user-wide install, or `--copy` on Windows to write real files instead of symlinks:

```bash
npx skills add Luminary-AI-Solutions/agent-readiness -a claude-code -a codex -a cursor -a github-copilot -a antigravity -a opencode -a cline -a droid
```

Or copy the two folders in [`skills/`](skills/) yourself:

| Harness | Project skills dir | User skills dir | Invoke |
|---|---|---|---|
| Claude Code | `.claude/skills/` | `~/.claude/skills/` | ask, or `/agent-readiness` |
| OpenAI Codex | `.agents/skills/` | `~/.agents/skills/` | ask, or `$agent-readiness` |
| Cursor | `.agents/skills/` or `.cursor/skills/` | `~/.cursor/skills/` | ask, or `/agent-readiness` |
| GitHub Copilot | `.github/skills/` or `.agents/skills/` | `~/.copilot/skills/` | ask, or `/agent-readiness` |
| Google Antigravity | `.agents/skills/` | `~/.gemini/config/skills/` | ask, or `/agent-readiness` |
| OpenCode | `.opencode/skills/` or `.agents/skills/` | `~/.config/opencode/skills/` | ask |
| Cline | `.cline/skills/` or `.agents/skills/` | `~/.cline/skills/` | ask, or `/agent-readiness` |
| Factory Droid | `.factory/skills/` or `.agents/skills/` | `~/.factory/skills/` | ask, or `/agent-readiness` |

**One copy for a whole team:** commit the skills to `.agents/skills/`, which every harness above except Claude Code reads, plus a copy or symlink in `.claude/skills/`. Cursor, Copilot, OpenCode and Cline read `.claude/skills/` too. Paths checked against each tool's docs in October 2026; these move, so check yours if something doesn't load.

## Use

Ask in plain language:

- *"Run an agent readiness report on this repo."*
- *"How agent-ready is this codebase? What should we fix first?"*
- *"Fix the readiness gaps"* or *"Get us to Level 3"* (uses `agent-readiness-fix`)

Output lands in `.agent-readiness/`:

| File | What it is |
|---|---|
| `report.html` | The dashboard: level staircase, gap map, next moves, pillar pass/fail, fix plan by lane, trend, and every criterion with its evidence |
| `summary.md` | The same results as markdown, ready for a PR, issue or chat |
| `report.json` | Every verdict and rationale. Commit it so the next run stays consistent. |
| `history.jsonl` | One line per run. Commit it to get a trend chart. |
| `preferences.json` | Your fix choices, working style and waivers |
| `fix-plan.md` | The editable plan from `agent-readiness-fix` |

### Without an agent (CI, quick look)

The scanner works alone. Skipping the judgment step gives a provisional, heuristic-only score, which is useful for tracking a trend in CI:

```bash
python skills/agent-readiness/scripts/scan.py . && python skills/agent-readiness/scripts/report.py .agent-readiness/draft.json --allow-review
```

## Example

[`examples/fastapi/`](examples/fastapi/) is a full report on [fastapi/fastapi](https://github.com/fastapi/fastapi), produced by an agent that followed `SKILL.md` cold. It includes the dashboard, the summary, every rationale, and the agent's `decisions.json`.

## Credits

The five-level model, the 80% gate, the pillar structure, and the practice of grounding each evaluation on the previous report come from [Factory's Agent Readiness Model](https://docs.factory.com/agent-readiness/overview) and their [launch write-up](https://factory.com/news/agent-readiness). This is an independent, harness-agnostic implementation. It is not affiliated with or endorsed by Factory, and its criteria, wording and scoring details are its own.

## Contributing

See [AGENTS.md](AGENTS.md). In short: `criteria.json` is the source of truth, scanner checks stay conservative, scoring stays in `report.py`, and `python -m unittest discover -s tests` must pass.

## License

[MIT](LICENSE)
