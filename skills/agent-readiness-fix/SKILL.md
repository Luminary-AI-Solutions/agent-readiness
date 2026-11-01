---
name: agent-readiness-fix
description: Fix the failing criteria from an agent readiness report, such as adding AGENTS.md, linters, pre-commit hooks, env templates, CI checks and templates, then re-score to confirm progress. Use when the user asks to fix, remediate or improve agent readiness, to "get this repo to Level N", or to act on a readiness report's action items. Requires a report from the agent-readiness skill. Run that first if `.agent-readiness/report.json` doesn't exist.
---

# Agent Readiness Fix

Turn a readiness report into repo changes, one criterion at a time, then re-score.

## 1. Load the report

Read `.agent-readiness/report.json`, or the path the user gives. If there's none, run the `agent-readiness` skill first. Its `report.json` lists every criterion with a status and rationale. The criterion definitions, including a `fix` hint for each, are in the agent-readiness skill's `references/criteria.json`.

If the report's commit (`repo.commit`) is far behind `HEAD`, re-run the report first. Its findings may be stale.

## 2. Pick targets

If the user names a focus ("just security", "get us to Level 3", "don't touch CI"), follow it. Otherwise:

1. Start with failing criteria **at the current level**. These are what block the next level. Then do the ones below it.
2. Within that set, take `basic` first, then `intermediate`. Leave `advanced` unless the user asks.
3. Cap a run at about **5 criteria**. Smaller batches are easier to review.

Sort the candidates into three groups:

- **Repo-local changes you can make**: config files, docs, scripts, templates, CI workflow steps.
- **Settings outside the repo**: branch protection, secret scanning or push protection, repository labels. Don't change these yourself. Give the user the exact steps or command (for example `gh api -X PUT repos/{owner}/{repo}/branches/main/protection ...`) and let them run it, unless they explicitly ask you to and you have the access.
- **Decisions that need the user**: new paid or external services (error tracking, analytics, feature flag providers), switching a project to strict typing when that creates hundreds of errors, adding large new frameworks. Propose these and don't apply them.

Show the plan as a short list (criterion, what you'll change, which files) and get a go-ahead before editing, unless the user already told you to proceed.

## 3. Fix, one criterion at a time

- **Match the repository.** Use its package manager, task runner, existing config style and naming. Extend an existing config rather than adding a parallel one. Example: add a rule to the existing ESLint config instead of installing a second linter.
- **Keep it small and idiomatic.** Use the ecosystem default tool (Ruff for Python, Biome or ESLint for JS/TS, golangci-lint for Go, Clippy for Rust) unless the repo already uses something else.
- **Verify each change.** Run the new lint, typecheck, hook or test command and confirm it works. If a new check fails on existing code, either fix the trivial violations or configure a baseline. Don't leave the repo with a red check the user didn't agree to.
- **Write AGENTS.md from what's true.** Commands must actually work: run them, or read the scripts that define them. Use `references/agents-md-template.md` as the outline. If harness-specific files already exist (CLAUDE.md, .cursor/rules, etc.), keep them and make AGENTS.md the shared source. A one-line pointer from the specific file to AGENTS.md is enough.
- **Templates and docs should be short and specific to the repo**: a PR template with the checks this repo runs, and an `.env.example` listing the variables the code actually reads.
- **Never commit secrets.** `.env.example` holds placeholders, never real values.

Work on a branch if the repo is under git. Don't commit or push unless the user asks.

## 4. Re-score

Re-run the report: scan, decide, render, following the agent-readiness skill. The new `report.json` stays grounded on the previous one, so only the criteria you touched should move. Then tell the user:

- The level and pass rate before and after
- Each criterion you flipped, and the evidence
- What's left for them: settings changes, external services, and items you deliberately skipped
