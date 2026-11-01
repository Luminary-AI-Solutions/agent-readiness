---
name: agent-readiness
description: Score how ready a repository is for autonomous coding agents (5 levels, 9 pillars, ~80 criteria) and render an HTML dashboard plus a markdown summary. Use when the user asks for an agent readiness report, score or audit, asks whether a codebase is "agent-ready" or why agents struggle in it, wants to know what to fix so agents work better in a repo, or asks to re-run or refresh a readiness report.
---

# Agent Readiness Report

Evaluate a repository against an agent readiness model: does it have the feedback loops, documentation, environment, guardrails and signals that let a coding agent plan, verify and ship its own work? The output is a level from 1 (Functional) to 5 (Autonomous), a pass rate per pillar, a short list of the highest-impact fixes, and a self-contained dashboard.

The work is split three ways so results are repeatable:

1. **`scripts/scan.py`** gathers evidence deterministically (files, configs, git history, the hosting platform's CLI) and writes a draft with a provisional verdict for every criterion.
2. **You** read the evidence, decide what the scanner can't (`review` items), sanity-check its other verdicts, and write `decisions.json`.
3. **`scripts/report.py`** merges your decisions, computes the score (the model never does arithmetic), and renders `report.html`, `summary.md` and `history.jsonl`.

`<skill-dir>` below means the directory containing this file. Scripts need Python 3.8+ and the standard library only. If Python isn't available, use **Manual mode** at the end.

## Workflow

### 1. Scan

Find the repository root (`git rev-parse --show-toplevel`) and run:

```
python <skill-dir>/scripts/scan.py <repo-root>
```

Output goes to `<repo-root>/.agent-readiness/` unless you pass `--out <dir>`. Use `--out` when the user doesn't want files written into the repo. Add `--offline` when there's no network or the platform CLI shouldn't be used. Platform checks (branch protection, CI timing, labels, issues, bot reviewers) use `gh` when it's installed and authenticated. Without it, those criteria come back as `review`.

The scan prints the discovered apps, provisional counts and the criteria needing review. It takes seconds on most repos.

### 2. Check app discovery

Open `draft.json` and look at `apps` (each has a `kind`: `service`, `web`, `library` or `cli`) and `monorepo.excluded`. Apps are the independently deployable units: a web app, an API service, a worker, a CLI. Shared config packages and internal libraries in a monorepo usually aren't apps. A repo that *is* a published package (a framework, an SDK) is one `library` app, and runtime criteria like logging, tracing and health checks skip for it.

The kind matters because many criteria skip for libraries. If discovery or a kind is wrong, re-run with an explicit list, using `path=kind`:

```
python <skill-dir>/scripts/scan.py <repo-root> --apps apps/web=web,apps/api=service,packages/sdk=library
python <skill-dir>/scripts/scan.py <repo-root> --apps .=library
```

App-scoped criteria (linting, tests, logging and others) are scored per app and appear as fractions like `2/3`.

### 3. Decide

Read `<skill-dir>/references/criteria.json` for each criterion's `pass` rule. Then work through `draft.json`:

- **Every `review` item needs a verdict**: `pass`, `fail` or `skip`.
- **Spot-check `fail` and `pass` verdicts.** The scanner matches on filenames and dependency names, so it can be wrong. Override it when the evidence says otherwise. Common cases: a tool configured under an unusual name (false fail), or a config file that exists but nothing runs (false pass).
- **Gather evidence cheaply.** Read files, list directories, grep, and run read-only commands like `git log`, `gh api` or `gh run list`. Don't install dependencies, run builds or start services unless the user asks for it.
- **Use `skip` only when the criterion genuinely doesn't apply.** Examples: health checks for a library, DAST for a CLI, N+1 detection without a database. The criterion's `pass` text says when skipping is allowed. Hard-to-find evidence is not a reason to skip. Mark it `fail`, and add "(unverified)" to the rationale if you couldn't check, such as a platform setting that needs admin access.
- **Stay consistent with the last run.** If an entry has a `previous` field, keep that verdict unless the evidence actually changed, and say what changed. This keeps scores stable from run to run.
- **Write one-sentence rationales with concrete evidence**: file paths, tool names, counts, durations. For example: "ESLint flat config in apps/web/eslint.config.js, run by the `lint` script and CI" rather than "Linting is set up."
- **Don't be generous.** An agent can only use what's committed and discoverable. A readiness model that flatters the repo is useless to the person reading it.

Write only what you change or confirm to `<out>/decisions.json`. Use your file-writing tool if you have one. Shell heredocs tend to break on the quotes in rationales.

```json
{
  "evaluator": { "harness": "claude-code", "model": "claude-opus-5-5" },
  "criteria": {
    "readme": { "status": "pass", "rationale": "README.md covers purpose, setup and pnpm scripts (142 lines)" },
    "structured_logging": {
      "apps": {
        "apps/web": { "status": "skip", "rationale": "Static frontend; no server runtime" },
        "apps/api": { "status": "fail", "rationale": "Uses console.log throughout src/; no structured logger" }
      }
    }
  },
  "action_items": [
    { "criterion": "pre_commit_hooks", "title": "Add pre-commit hooks",
      "why": "Lint and type errors only surface in CI, about 9 minutes after a push",
      "how": "Add lefthook running `pnpm lint --fix` and `pnpm typecheck` on staged files" }
  ]
}
```

- Set `evaluator.harness` to the tool you're running in (for example `claude-code`, `codex`, `cursor`, `droid`, `gemini-cli`, `copilot`, `opencode`) and `evaluator.model` to your model id if you know it.
- For app-scoped criteria, set verdicts per app under `apps`. A top-level `status` on an app-scoped criterion applies to every app that isn't already skipped.
- Write **2 to 3 `action_items`**, ordered by impact on reaching the next level. Start with failing criteria at the current level, cheapest first (difficulty `basic`, then `intermediate`). Make `why` specific to this repo and `how` concrete enough to act on. If you omit them, the script picks some, but yours will be better.

### 4. Score and render

```
python <skill-dir>/scripts/report.py <out>/draft.json --decisions <out>/decisions.json
```

This writes `report.json`, `report.html`, `summary.md` and appends to `history.jsonl`. It refuses to score while any criterion is still `review`. Fix those in `decisions.json` and re-run. Use `--allow-review` only for a deliberately provisional report.

### 5. Present

Show the user:

- The level and its name, the overall pass rate, and how far they are from the next level (from `summary.md`)
- The pillar table, or the weakest two or three pillars
- Your action items
- Where `report.html` is. Open it if your environment can open files or a browser.

Then offer to fix the gaps. If the `agent-readiness-fix` skill is installed, that's its job.

Mention what's worth committing. `report.json` and `history.jsonl` let the next run stay consistent and let the dashboard show a trend. `draft.json` and `decisions.json` are working files. Don't commit anything unless the user asks.

## Scoring model

- **Levels.** Each criterion belongs to one level. A repository starts at Level 1. Level N+1 unlocks when at least **80%** of Level N's applicable criteria pass, so the gates apply in order. Example: 9/10 at Level 1 and 15/20 at Level 2 is Level 2, because 75% at Level 2 doesn't clear the gate.
- **Monorepos.** A criterion that passes in 2 of 3 apps counts as 0.67 toward its level.
- **Skips.** Skipped criteria are removed from the denominator.
- **Pillars.** These are reporting views, not gates: Style & Validation, Build System, Testing, Documentation, Dev Environment, Debugging & Observability, Security & Governance, Task Discovery, Product & Experimentation.
- **Difficulty.** Each criterion has a difficulty (`basic`, `intermediate` or `advanced`), which sets the fix order. It's independent of level.

## Manual mode (no Python)

If you can't run the scripts:

1. Read `references/criteria.json`.
2. Evaluate each criterion yourself, using the same rules as step 3.
3. Compute each level's pass rate (passing / applicable) and apply the 80% gates in order.
4. Write `summary.md` in this format: a heading with the level and pass rate, a table of the 5 levels, a table of the 9 pillars, then 2 to 3 action items.

The HTML dashboard needs `report.py`. Tell the user it can be rendered later on any machine with Python by putting your verdicts in `decisions.json` and running a scan there.
