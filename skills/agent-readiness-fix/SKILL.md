---
name: agent-readiness-fix
description: Guide a developer through closing the gaps in an agent readiness report. Auto-fix the small, reversible items; walk through the real decisions (tooling, policy, architecture) with options and trade-offs so the developer chooses; give exact steps for settings outside the repo. Use when the user asks to fix, remediate or improve agent readiness, to "get this repo to Level N", or to act on a readiness report. Requires a report from the agent-readiness skill.
license: MIT
metadata:
  version: "0.2.0"
---

# Agent Readiness Fix

The developer stays in charge of how their repo works. You do the legwork: sort the gaps, apply the obvious fixes, explain the trade-offs on the rest, and implement whatever the developer picks, in their style.

Every failing criterion falls into one of three **lanes** (`lane` in the agent-readiness skill's `references/criteria.json`):

| Lane | What it covers | Who decides | What you do |
|---|---|---|---|
| **Auto-fix** | Small, reversible changes the repo already settles: PR/issue templates, `.env.example`, `.gitignore` gaps, a missing lockfile, documenting commands that already exist | Facts in the repo | Apply after one confirmation, then verify |
| **Your call** | A choice of tool, policy or architecture: linter, hooks, test strategy, strictness, logging stack, feature flags, CI gates | The developer | Lay out the options, recommend one, implement their pick |
| **Manual** | Outside the repo: branch protection, platform security settings, CLI auth, team process | The developer | Give exact steps and commands |

Adjust lanes for this repo when it's obvious. Promote a "Your call" item to auto when the repo already settles the choice. Example: Ruff is the linter, so `ruff format` is the formatter. Demote an auto item when it isn't clear-cut. Example: the README has a strong voice the team clearly cares about.

## 1. Load

- Read `.agent-readiness/report.json`, or the path the user gives. If there's none, run the `agent-readiness` skill first. If `repo.commit` is well behind `HEAD`, re-run the report before fixing anything.
- Read `.agent-readiness/preferences.json` if it exists. It holds earlier choices, waivers and working style. Don't re-ask anything it already answers.
- Keep `references/playbook.md` open. It lists the decisions per criterion, with options and trade-offs.

## 2. Agree on how to work

Ask once, and only what the user's request didn't already say. Use your harness's question tool if it has one; otherwise offer numbered options in chat. Ask at most three questions:

1. **Scope:** next level only (default), all `basic` and `intermediate` gaps, or a focus area such as "testing" or "security".
2. **Auto-fixes:** apply them and show a summary (default), show each change before applying, or plan only, where you write the plan and they do the work.
3. **Commits:** leave changes uncommitted (default), or one commit per fix on a branch.

Save the answers under `style` in `preferences.json`.

## 3. Write the plan

Pick the targets: failing and `review` criteria within scope, current level first, then lower levels. Write `.agent-readiness/fix-plan.md` with three checklists, one per lane. For each item, include:

- The criterion name and id, and its level
- Why it matters for an agent in *this* repo, in one concrete line. Example: "Lint only runs in CI, about 9 minutes after a push."
- What would change: the files and commands
- For "Your call" items: the question and the short option list

In chat, give a compact summary: the counts per lane, the auto-fix list, and the first decision. The plan file belongs to the developer. They may tick, strike or annotate items, so re-read it before acting on it.

## 4. Auto-fix lane

Unless `style` says to apply directly, confirm the auto-fix list once. Then work through it one item at a time:

- Extend what exists rather than replacing it. Match the repo's package manager, file layout and tone.
- Verify each fix: run the command you documented, validate the template renders, or check that the lockfile installs.
- Stop and ask if an "auto" fix turns out to touch history or secrets. Example: a tracked `.env` should be untracked and its keys rotated. That's the developer's call.
- Report each one as: criterion → files changed → how you verified it.

## 5. "Your call" lane: walk through the decisions

For each item, or a batch of up to three closely related ones such as linter, formatter and hooks:

1. **Why it matters here.** One line, specific to this repo.
2. **Options.** Two to four options from the playbook, filtered to this stack. Give each a one-line trade-off and an effort estimate (S/M/L).
3. **Recommendation.** Say which option you'd pick and why, based on what the repo already uses.
4. **Two standing options.** Always also offer *Skip for now*, and *Doesn't apply to us*. The second becomes a waiver: write `"waivers": {"<criterion_id>": "<their reason>"}` to `preferences.json`. Future reports show it as waived, not failing.

Record each pick under `choices` in `preferences.json`. Then implement exactly what they chose, in their style:

- **Stage big changes so nothing goes red unannounced:**
  - Strict typing: new and changed files first, or a baseline file.
  - Coverage: report-only, then a floor at today's number.
  - New CI checks: non-blocking first.
  - Observability: one service first.
- **External services** (Sentry, PostHog, LaunchDarkly and similar): never sign up, create accounts or add keys. Scaffold the integration behind env vars, add the variables to `.env.example`, and list what the developer must do.
- **Turn prose into enforcement.** When the developer states a rule, such as "agents must never touch migrations", offer to make it a hook, a deny rule or a lint rule. Prose in AGENTS.md is advisory; config is enforced.
- **Plan-only mode, or "teach me".** Instead of editing, write the exact steps, commands and snippets into `fix-plan.md` for the developer to do.

## 6. Manual lane

For each item, give exact steps: the UI path and/or the CLI command, then how to confirm it worked. Example: `gh api -X PUT repos/{owner}/{repo}/branches/main/protection --input protection.json`. Run settings-changing commands only if the developer explicitly asks and has the access.

## 7. Re-score and close

Re-run the agent-readiness skill. Waivers apply automatically. Then:

- Update the checkboxes in `fix-plan.md`.
- Tell the developer the level and pass rate before and after, and which criteria flipped, with evidence.
- List what's still pending: manual steps, deferred decisions, and anything you deliberately left alone.

## Rules

- **No silent product decisions.** Anything that changes how the team works is the developer's call: a new tool, a new required check, a new service, stricter rules.
- **Keep AGENTS.md short and true.** Draft only verified facts: commands you ran, paths that exist. Get conventions, gotchas and "don'ts" from the developer by asking two or three questions. Aim for about 200 lines or fewer. A 2026 ETH Zurich study found LLM-generated context files raised agent cost by more than 20% without improving success, developer-written ones did only slightly better, and directory overviews didn't help at all.
- **One tool beats two.** Extend existing configs before adding a parallel one.
- **Leave git history and the remote alone.** Never commit secrets, never push, never rewrite history. Commit only if `style.commits` says to.
