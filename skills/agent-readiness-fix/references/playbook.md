# Decision playbook

The decisions behind the "Your call" lane, grouped by pillar. Each entry has:

- **Ask:** the question to put to the developer
- **Options:** a starting menu. Filter it to the repo's stack, and add an option if the repo already leans another way.
- **Lean:** a sensible default recommendation, adjusted to what the repo already uses
- **Stage:** how to roll it out without breaking anyone's day, where that matters

Effort: **S** = minutes, **M** = an hour or two, **L** = a day or more.

For a criterion not listed here, build the same shape from its `pass` and `fix` text in criteria.json. Write 2 to 4 concrete options plus *Skip for now* and *Doesn't apply to us*.

---

## Style & Validation

**Linter and formatter** (`lint_config`, `formatter`)
- Ask: Which lint and format toolchain should this repo standardize on?
- Options:
  - **JS/TS:**
    - Biome: one fast tool for lint and format (S)
    - ESLint + Prettier: the biggest plugin ecosystem (M)
    - oxlint + Prettier: very fast, fewer rules (S)
  - **Python:**
    - Ruff for both lint and format (S)
    - Flake8 + Black + isort (M)
  - **Go:** golangci-lint + gofmt (S)
  - **Rust:** Clippy + rustfmt (S)
- Lean: whatever is partly configured already. Otherwise use the single-tool option (Biome or Ruff), since fewer tools means fewer config files for agents to reason about.

**Type checking and strictness** (`type_check`, `strict_typing`)
- Ask: How strict, and how fast to get there?
- Options:
  - Strict everywhere now (L for large codebases)
  - Strict for new and changed files, ratcheting per directory (M)
  - A baseline file that freezes today's errors, so only new ones fail (S)
- Lean: the baseline or ratchet. A sudden wall of errors makes agents "fix" types with `any` and `# type: ignore`.
- Stage: run in CI as non-blocking for a week, then make it blocking.
- Python options: mypy (mature), pyright/basedpyright (fast, strict by design).

**Commit hooks** (`pre_commit_hooks`)
- Ask: Which hook runner, and which checks run on commit?
- Options:
  - lefthook: fast, any language, one YAML file (S)
  - Husky + lint-staged: the JS ecosystem default (S)
  - pre-commit: the Python ecosystem default, polyglot (S)
- Lean: run only fast checks on staged files (format, lint --fix, secret scan), and leave the full suite to CI.

**Agent hooks** (`agent_hooks`)
- Ask: Should checks run automatically while agents edit, and in which harnesses?
- Options:
  - Post-edit formatter + a stop hook running lint and typecheck, configured per harness the team uses: Claude Code and Droid settings hooks, `.cursor/hooks.json`, Copilot and Cline hooks (M)
  - Rely on commit hooks only (S)
- Lean: both. Commit hooks cover every harness; agent hooks catch errors mid-task, when they're cheapest to fix.

**Dead code, unused dependencies, duplication, complexity** (`dead_code_detection`, `unused_dependencies_detection`, `duplicate_code_detection`, `cyclomatic_complexity`)
- Ask: Which of these is worth a CI check here, and blocking or advisory?
- Options:
  - JS/TS: knip covers dead code and unused dependencies (S)
  - Python: vulture + deptry (S)
  - Go: deadcode + `go mod tidy -diff` (S)
  - Complexity: enable the rule in the existing linter, e.g. ESLint `complexity` or Ruff `C901` (S)
  - Duplication: jscpd (S)
- Lean: knip/deptry as advisory first. Complexity limits at a generous threshold that only flags new outliers.

**Module boundaries** (`code_modularization`)
- Ask: Which layers must not import which?
- Options:
  - dependency-cruiser (JS/TS), with rules whose messages say how to fix the violation (M)
  - import-linter (Python) (M)
  - Nx module boundaries (Nx repos) (S)
  - Document the boundaries only (S)
- Lean: enforce two or three rules that encode real past mistakes. Write each error message as an instruction an agent can follow.

**TODO tracking** (`tech_debt_tracking`)
- Options:
  - Require `TODO(#123)` via a lint rule (S)
  - A CI job that turns TODOs into issues (M)
  - Waive it (some teams track debt elsewhere)

## Build System

**One-step setup** (`single_command_setup`)
- Options:
  - `make setup` / `just setup` (S)
  - An npm/pnpm `setup` script (S)
  - `mise` tasks (S)
  - A devcontainer `postCreateCommand` (M)
- Lean: whatever runner already exists. The script must be non-interactive and idempotent.

**Release automation and notes** (`release_automation`, `release_notes_automation`)
- Options:
  - release-please: PR-based, conventional commits (M)
  - Changesets: per-PR change notes, great for monorepos (M)
  - semantic-release: fully automatic (M)
  - Platform auto-deploy on merge (Vercel, Netlify, Fly, Cloudflare) + GitHub-generated release notes (S)
- Lean: apps that deploy on merge only need generated notes. Published packages want Changesets or release-please.

**Automated PR review** (`automated_pr_review`)
- Ask: Do you want an AI reviewer on every PR, and which one?
- Options:
  - The review bot of the harness you already pay for: Claude Code GitHub Action, Codex review, Copilot code review, Cursor Bugbot (S)
  - A dedicated reviewer such as CodeRabbit or Greptile (S, costs money)
  - Danger rules for mechanical policy only (M)
- Lean: one reviewer, not three. Keep it advisory, not a required check.

**Fast CI** (`fast_ci_feedback`, `build_performance_tracking`)
- Options:
  - Dependency caching (S)
  - Split lint, type and test into parallel jobs (S)
  - Run only affected packages, using Turborepo/Nx (M)
  - Shard tests (M)
- Lean: caching and parallel jobs first; they often halve CI time.

**Feature flags** (`feature_flag_infrastructure`)
- Options:
  - Env-var flags in a single typed module (S)
  - OpenFeature + a provider (M)
  - PostHog flags, if PostHog is already present (S)
  - LaunchDarkly, GrowthBook or Statsig (M, external)
- Lean: start with typed env flags unless you need per-user targeting. Often waived for small apps.

**Monorepo tooling** (`monorepo_tooling`, `version_drift_detection`)
- Options:
  - Workspaces only (S)
  - Turborepo (S)
  - Nx (M)
  - For version drift: pnpm catalogs or syncpack (S)

## Testing

**First tests** (`unit_tests_exist`)
- Ask: What's the riskiest logic to cover first?
- Options:
  - Pure business logic (S)
  - API handlers with an in-memory database (M)
  - The one flow that breaks most often (M)
- Lean: write five to ten tests around the code agents will change most, and set up the runner with a single-test command.

**Integration and E2E** (`integration_tests_exist`, `browser_automation`)
- Options:
  - API tests against a running app with a test database or testcontainers (M)
  - A Playwright smoke test of the main flow (M)
  - A browser MCP server (Playwright MCP, Chrome DevTools MCP) so agents can look at the UI (S)
- Lean: one Playwright smoke test + document the command. Anthropic found agents marked features done after unit-only checks until they could drive a browser.

**Coverage** (`test_coverage_thresholds`, `code_quality_metrics`)
- Options:
  - Report-only coverage on PRs (S)
  - A floor at today's percentage that only goes up (S)
  - A fixed target (S, risky)
- Lean: a floor at today's number. Fixed targets invite low-value tests.

**Flaky tests** (`flaky_test_detection`)
- Options:
  - Retries with reporting (Playwright/Jest retries, pytest-rerunfailures) (S)
  - A quarantine list (S)
  - A flaky-test service (M, external)

## Documentation

**AGENTS.md** (`agents_md`, `agents_md_lean`)
- Ask the developer:
  1. What do new teammates get wrong in their first week?
  2. What must agents never touch?
  3. Which commands do you actually run?
- Draft from verified facts only: commands you ran, paths that exist. Put commands first, then conventions and gotchas. Aim for about 200 lines or fewer, with no directory tour.
- If CLAUDE.md, GEMINI.md, `.cursor/rules` etc. exist, make AGENTS.md the source of truth and point the others at it.

**Skills and scoped instructions** (`skills`, `scoped_instructions`)
- Ask: Which multi-step workflows do people repeat? Examples: releasing, adding a migration, adding an API route.
- Options:
  - One SKILL.md per workflow in `.agents/skills/` (read by most harnesses) and `.claude/skills/` for Claude Code (S each)
  - Nested AGENTS.md per app (S)
  - Path-scoped rules (S)

**API schema, architecture, generated docs** (`api_schema_docs`, `service_flow_documented`, `automated_doc_generation`)
- Options:
  - Export the framework's OpenAPI spec in CI (S)
  - ARCHITECTURE.md with one component diagram and two request flows (M)
  - TypeDoc/Sphinx/mkdocs build in CI (M)

**Keeping instructions true** (`agents_md_validation`)
- Options:
  - A CI job that runs the commands in AGENTS.md and checks its paths (M)
  - A scheduled agent run that opens a PR when docs drift (M)

## Dev Environment

**Reproducible environment** (`devcontainer`, `devcontainer_runnable`)
- Options:
  - A devcontainer: works with Codespaces and most IDEs (M)
  - A Nix flake or devbox (M)
  - `.github/workflows/copilot-setup-steps.yml`, if Copilot's coding agent is used (S)
  - Docker Compose for services + a setup script (S)
- Lean: whatever matches how the team already works locally. Build it in CI once a week so it doesn't rot.

**Local services and parallel agents** (`local_services_setup`, `parallel_agent_isolation`)
- Options:
  - compose.yaml for backing services (S)
  - testcontainers per test run (M)
  - Ports and DB URLs from env + `.worktreeinclude`, so each worktree can run its own copy (M)
- Lean: env-driven ports and a per-run test database. These two changes are what let several agents work at once.

## Debugging & Observability

**Logging, tracing, metrics, errors** (`structured_logging`, `distributed_tracing`, `metrics_collection`, `error_tracking_contextualized`)
- Ask: What's your observability backend, if any?
- Options:
  - Structured logger only, at the start: pino, structlog, zap/slog, tracing (S)
  - OpenTelemetry SDK exporting to the existing backend (M)
  - Sentry or a similar service for errors (S, external)
  - Self-hosted options such as GlitchTip or Grafana (M)
- Lean: a structured logger with request IDs first. Add OpenTelemetry when there's somewhere to send it.

**Alerting and runbooks** (`alerting_configured`, `runbooks_documented`, `deployment_observability`)
- Options:
  - Alert rules as code next to the service (M)
  - A runbooks/ directory with one page per alert (S)
  - Release markers sent from the deploy job (S)

## Security & Governance

**CODEOWNERS** (`codeowners`, `agent_config_reviewed`)
- Ask: Who owns what? A default owner plus specific owners for agent config, CI and infra.
- Lean: a catch-all owner, plus explicit owners for `AGENTS.md`, `.claude/`, `.cursor/`, `.agents/`, MCP configs and `.github/workflows/`. Changing what agents are told deserves review.

**Agent guardrails** (`agent_guardrails_config`, `mcp_config_hygiene`)
- Ask: What should agents never read or run?
- Options:
  - Shared permission deny rules for `.env*` and `secrets/`, plus an allowlist of safe dev commands, per harness: `.claude/settings.json`, `.codex/config.toml`, Cursor/Droid settings (S)
  - Sandboxed runs with network limits (M)
  - MCP configs with env-referenced secrets and pinned versions (S)
- Lean: deny rules for secrets at minimum. A 2026 study of 481 CLAUDE.md files found only 4–16% of their security rules were backed by an enforced control.

**Secret scanning** (`secret_scanning`, `secrets_management`)
- Options:
  - gitleaks in commit hooks + CI (S)
  - The platform's push protection (manual, S)
  - Both (recommended)

**Dependency updates and SAST** (`dependency_update_automation`, `automated_security_review`)
- Options:
  - Dependabot: built in, simple (S)
  - Renovate: grouping and automerge rules (M)
  - CodeQL default setup (S, manual toggle)
  - Semgrep (S)
- Lean: grouped weekly updates, so agents and humans aren't buried in PRs.

## Task Discovery

**Issues, labels, plans** (`issue_templates`, `issue_labeling_system`, `plans_in_repo`)
- Options:
  - Issue forms that require acceptance criteria (S)
  - Labels for type, area and priority, kept as code (S)
  - `docs/plans/` with one short plan per in-flight feature (S)
- Lean: acceptance criteria in every issue. Agents need to know when they're done.

## Product & Experimentation

**Analytics and experiments** (`product_analytics_instrumentation`, `experimentation_infrastructure`, `error_to_insight_pipeline`)
- These are frequently *Doesn't apply*: internal tools, libraries, early prototypes. Offer the waiver first.
- Options:
  - PostHog for analytics, flags and experiments in one (M, external)
  - The existing analytics vendor's SDK (S)
  - Connect error tracking to the issue tracker (S, manual)
