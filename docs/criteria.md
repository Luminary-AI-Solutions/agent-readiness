# Criteria

<!-- Generated from skills/agent-readiness/references/criteria.json by tools/gen_criteria_doc.py. Do not edit. -->

82 criteria across 9 pillars and 5 levels. A level unlocks when 80% of the previous level's applicable criteria pass.

## Level 1: Functional

Code runs and basic tooling exists, but setup is manual and validation is thin.

| Criterion | Pillar | Scope | Difficulty | Passes when |
|---|---|---|---|---|
| **Linter configured**<br>`lint_config` | Style & Validation | app | basic | A linter is configured for the app's primary language (ESLint, Biome, Ruff, Flake8, Pylint, golangci-lint, Clippy, RuboCop, Checkstyle, SwiftLint, ktlint, etc.). |
| **Type checking**<br>`type_check` | Style & Validation | app | basic | The language is statically typed (Go, Rust, Java, C#, Kotlin, Swift, C/C++), or a type checker is configured (tsconfig.json, mypy, pyright, Sorbet, etc.). |
| **Code formatter**<br>`formatter` | Style & Validation | app | basic | An automatic formatter is configured or built into the toolchain and used (Prettier, Biome, Black, Ruff format, gofmt, rustfmt, clang-format, etc.). |
| **Build command documented**<br>`build_cmd_doc` | Build System | app | basic | The exact commands to install, build and run are written down (README, AGENTS.md, CONTRIBUTING) or exposed as obvious scripts (package.json scripts, Makefile, justfile, Taskfile). |
| **Dependencies locked**<br>`deps_pinned` | Build System | app | basic | A lockfile is committed (package-lock.json, pnpm-lock.yaml, yarn.lock, bun.lock(b), uv.lock, poetry.lock, Pipfile.lock, Cargo.lock for binaries, go.sum, Gemfile.lock, composer.lock, etc.). |
| **Unit tests exist**<br>`unit_tests_exist` | Testing | app | basic | The app has meaningful unit tests (test files alongside or in a tests/ dir; more than a placeholder). |
| **Tests runnable locally**<br>`unit_tests_runnable` | Testing | app | basic | There is a documented, single command that runs the tests locally without special credentials (`npm test`, `pytest`, `go test ./...`, `cargo test`, `make test`). |
| **README**<br>`readme` | Documentation | repo | basic | A README exists and explains what the project is and how to get it running (not just a title or template boilerplate). |
| **Comprehensive .gitignore**<br>`gitignore_comprehensive` | Security & Governance | repo | basic | .gitignore excludes secrets (.env, key files), dependency dirs, build output and editor/OS junk for the languages in use, and no such files are tracked. |

## Level 2: Documented

Workflows are written down for humans and agents; local guardrails catch mistakes early.

| Criterion | Pillar | Scope | Difficulty | Passes when |
|---|---|---|---|---|
| **Strict typing**<br>`strict_typing` | Style & Validation | app | intermediate | Type checking runs in strict mode (`strict: true` in tsconfig, mypy `strict = true`, pyright `strict`), or the language is statically typed by default. |
| **Pre-commit hooks**<br>`pre_commit_hooks` | Style & Validation | repo | basic | Local hooks run lint/format/type checks before commit (pre-commit, Husky, lefthook, simple-git-hooks, lint-staged, a committed .githooks/ wired via core.hooksPath). |
| **Naming conventions**<br>`naming_consistency` | Style & Validation | app | intermediate | Naming conventions are documented (AGENTS.md, CONTRIBUTING, style guide) or enforced by lint rules (e.g. ESLint naming-convention, pep8-naming). |
| **VCS CLI available**<br>`vcs_cli_tools` | Build System | repo | basic | The hosting platform's CLI (gh, glab, az repos, etc.) is installed and authenticated in the environment the agent runs in, so it can open PRs and read CI/issue state. |
| **Single-command setup**<br>`single_command_setup` | Build System | repo | intermediate | A fresh clone can be bootstrapped with one documented command (`make setup`, `./scripts/bootstrap`, `just setup`, `npm run setup`, devcontainer, `mise install && ...`). |
| **Test naming conventions**<br>`test_naming_conventions` | Testing | app | basic | Test files follow a consistent, tool-recognized pattern (*.test.ts, *_test.go, test_*.py, configured testMatch/testpaths). |
| **Agent instructions file**<br>`agents_md` | Documentation | repo | basic | An agent instructions file exists with real, repo-specific content: AGENTS.md (the cross-harness standard), or a harness-specific equivalent (CLAUDE.md, GEMINI.md, .cursor/rules, .github/copilot-instructions.md, .windsurfrules). Must cover commands and conventions, not just a stub. |
| **Docs kept fresh**<br>`documentation_freshness` | Documentation | repo | basic | Key docs in the repo (README, AGENTS.md or equivalent, CONTRIBUTING) were each updated within 180 days of the repository's latest commit, so they move with the code. A stub that only links elsewhere counts as present but not substantive. |
| **Env template**<br>`env_template` | Dev Environment | app | basic | Required environment variables are documented in a committed template (.env.example, .env.sample, .env.template) or a documented config section. Skip if the app needs no env configuration. |
| **Reproducible environment**<br>`devcontainer` | Dev Environment | repo | intermediate | A reproducible dev environment is defined: .devcontainer/devcontainer.json, Nix flake/shell, devbox.json, or a Dockerfile/compose setup documented for development. |
| **Branch protection**<br>`branch_protection` | Security & Governance | repo | basic | The default branch is protected (branch protection or rulesets requiring PRs/reviews/status checks). Verify with the platform CLI/API when possible. |
| **CODEOWNERS**<br>`codeowners` | Security & Governance | repo | basic | A CODEOWNERS file exists (root, .github/ or docs/) assigning owners to paths. |
| **Issue templates**<br>`issue_templates` | Task Discovery | repo | basic | Issue templates or forms exist (.github/ISSUE_TEMPLATE/, .gitlab/issue_templates/). |
| **PR template**<br>`pr_templates` | Task Discovery | repo | basic | A pull/merge request template exists (pull_request_template.md in root, .github/ or docs/; .gitlab/merge_request_templates/). |

## Level 3: Standardized

Processes are enforced by automation: integration tests, security scanning, observability.

| Criterion | Pillar | Scope | Difficulty | Passes when |
|---|---|---|---|---|
| **Large file guard**<br>`large_file_detection` | Style & Validation | repo | intermediate | Something prevents large/binary files from landing in git: Git LFS via .gitattributes, a check-added-large-files hook, or a CI size check. |
| **Tech debt tracking**<br>`tech_debt_tracking` | Style & Validation | repo | intermediate | TODO/FIXME comments are tracked or constrained: a lint rule requiring ticket references, a TODO scanner in CI, or a debt register that is maintained. |
| **Agents already in the loop**<br>`agentic_development` | Build System | repo | basic | There is evidence agents already work here: agent co-author trailers in recent commits, agent config dirs (.claude/, .cursor/, .codex/, .factory/, .github/copilot-instructions.md), or agent bot PRs. |
| **Automated PR review**<br>`automated_pr_review` | Build System | repo | intermediate | Pull requests get automated review beyond CI pass/fail: an AI reviewer, a review bot, Danger, or policy bots that comment on PRs. |
| **Release automation**<br>`release_automation` | Build System | repo | intermediate | Releases/deploys are triggered by automation (CD workflow on merge/tag, semantic-release, changesets, release-please, GoReleaser, platform auto-deploy like Vercel/Netlify/Fly connected to the repo). |
| **Monorepo tooling**<br>`monorepo_tooling` | Build System | repo | intermediate | Multi-app repos use workspace tooling (pnpm/npm/yarn workspaces, Turborepo, Nx, Bazel, Pants, Cargo/Go workspaces, uv workspaces). Skip for single-app repos. |
| **Unused dependency detection**<br>`unused_dependencies_detection` | Build System | app | intermediate | Unused dependencies are detected in CI or hooks (knip, depcheck, deptry, cargo-udeps/machete, `go mod tidy` diff check). |
| **Integration / E2E tests**<br>`integration_tests_exist` | Testing | app | intermediate | There are tests that exercise components together or end to end (integration/ or e2e/ suites, Playwright, Cypress, testcontainers, API tests against a running service). |
| **Test isolation**<br>`test_isolation` | Testing | app | intermediate | Tests are isolated and parallel-safe: run in parallel (pytest-xdist, Jest/Vitest workers, go test -race/-parallel), use fixtures/factories, no shared mutable global state or order dependence. |
| **Coverage tracked**<br>`test_coverage_thresholds` | Testing | app | intermediate | Coverage is measured and either enforced with a threshold or reported on PRs (coverage thresholds in config, Codecov/Coveralls, CI coverage gate). |
| **Agent skills / commands**<br>`skills` | Documentation | repo | intermediate | Reusable agent skills or commands for working on this repo are committed where harnesses discover them (.claude/skills, .agents/skills, .factory/skills, .codex/skills, .cursor/skills, .github/skills, or custom slash-command/prompt dirs). Skills shipped as package data for end users don't count. |
| **API schema documented**<br>`api_schema_docs` | Documentation | app | intermediate | Apps that expose an API publish a machine-readable schema (OpenAPI/Swagger, GraphQL SDL, protobuf, tRPC/zod schemas exported, JSON Schema). Skip for apps with no API surface. |
| **Architecture documented**<br>`service_flow_documented` | Documentation | repo | intermediate | Architecture or key flows are documented (ARCHITECTURE.md, docs/ with diagrams, Mermaid/PlantUML, ADRs) beyond what the README says. |
| **Local services**<br>`local_services_setup` | Dev Environment | repo | intermediate | Backing services (DB, cache, queues) can be started locally with one command (docker-compose, Tilt, Skaffold, supabase start, testcontainers). Skip if there are no backing services. |
| **Schema as code**<br>`database_schema` | Dev Environment | app | intermediate | Apps that use a database manage schema as code (migrations dir, Prisma/Drizzle schema, Alembic, Rails/Django migrations, Flyway, Atlas). Skip if there is no database. |
| **Structured logging**<br>`structured_logging` | Debugging & Observability | app | intermediate | Deployed services log through a structured logger (pino, winston JSON, structlog, zap, slog, tracing, logback JSON) instead of bare print/console.log. Skip for libraries. |
| **Tracing**<br>`distributed_tracing` | Debugging & Observability | app | advanced | Services emit traces (OpenTelemetry, Datadog APM, Honeycomb, Sentry performance, X-Ray) with trace context propagated. Skip for libraries/CLIs. |
| **Metrics**<br>`metrics_collection` | Debugging & Observability | app | intermediate | Services expose or ship runtime metrics (Prometheus client, StatsD, OpenTelemetry metrics, Datadog, platform analytics). Skip for libraries/CLIs. |
| **Error tracking**<br>`error_tracking_contextualized` | Debugging & Observability | app | intermediate | Errors are captured with context (Sentry, Bugsnag, Rollbar, Honeybadger, Datadog error tracking) including release/user/request tags. Skip for libraries. |
| **Health checks**<br>`health_checks` | Debugging & Observability | app | basic | Services expose health/readiness endpoints or probes (/health, /healthz, /ready, k8s probes, platform health checks). Skip for libraries/CLIs/static sites. |
| **Secret scanning**<br>`secret_scanning` | Security & Governance | repo | basic | Secrets are scanned for: platform secret scanning/push protection enabled, or gitleaks/trufflehog/detect-secrets in hooks or CI. |
| **Dependency updates automated**<br>`dependency_update_automation` | Security & Governance | repo | basic | Dependency updates are automated (Dependabot config, Renovate config, or equivalent). |
| **Secrets management**<br>`secrets_management` | Security & Governance | app | intermediate | Runtime secrets come from a manager or platform store (env injected by platform, Vault, AWS/GCP/Azure secret managers, Doppler, 1Password, SOPS) and no secrets are hardcoded in source. |
| **Issue labels**<br>`issue_labeling_system` | Task Discovery | repo | basic | Issues use a deliberate label taxonomy beyond the platform defaults (type, area, priority), visible via the platform CLI/API or a labels config file. |

## Level 4: Optimized

Feedback loops are fast and measured; quality and delivery are tracked continuously.

| Criterion | Pillar | Scope | Difficulty | Passes when |
|---|---|---|---|---|
| **Dead code detection**<br>`dead_code_detection` | Style & Validation | app | advanced | A dedicated detector for unused exports, files or functions runs in CI or hooks (knip, ts-prune, vulture, deadcode, unparam). General unused-import/unused-variable lint rules don't count on their own. |
| **Duplicate code detection**<br>`duplicate_code_detection` | Style & Validation | repo | advanced | Copy-paste detection runs in CI (jscpd, PMD CPD, SonarQube duplication gate, etc.). |
| **Complexity limits**<br>`cyclomatic_complexity` | Style & Validation | app | advanced | Function complexity is measured and limited (ESLint `complexity`, Ruff C901/mccabe, gocyclo, Clippy cognitive_complexity, Sonar, etc.). |
| **Module boundaries enforced**<br>`code_modularization` | Style & Validation | app | advanced | Architectural boundaries are enforced by tooling (dependency-cruiser, eslint-plugin-boundaries, Nx module boundaries, import-linter, ArchUnit, Go internal/ packages used deliberately). |
| **N+1 query detection**<br>`n_plus_one_detection` | Style & Validation | app | advanced | Apps that use an ORM/database have N+1 detection (Bullet, nplusone, Django assertNumQueries patterns, Prisma/Hibernate query logging checks). Skip if the app has no database access. |
| **Fast CI feedback**<br>`fast_ci_feedback` | Build System | repo | advanced | The slowest workflow that runs on pull requests typically finishes in about 10 minutes or less (median of recent runs). Fail if there is no CI at all. |
| **Regular deployments**<br>`deployment_frequency` | Build System | repo | intermediate | Releases or deploys happen regularly (e.g. several in the last 90 days, visible via tags, releases, or deploy workflow runs). Skip for libraries with no deploy target only if releases also aren't applicable. |
| **Build performance tracked**<br>`build_performance_tracking` | Build System | repo | advanced | Builds are cached or measured: dependency or build caching in CI (actions/cache, setup-* cache), Turborepo/Nx/Bazel remote cache, sccache, or CI timing dashboards and build-time budgets. |
| **Release notes automated**<br>`release_notes_automation` | Build System | repo | intermediate | Changelogs or release notes are generated from commits/PRs (changesets, release-please, semantic-release, git-cliff, GitHub generated notes, conventional commits enforced). |
| **Feature flags**<br>`feature_flag_infrastructure` | Build System | app | advanced | Deployed apps have a feature flag system (LaunchDarkly, Unleash, GrowthBook, Flagsmith, PostHog flags, Statsig, OpenFeature, or a deliberate in-house system). Skip for libraries/CLIs. |
| **Bundle size guard**<br>`heavy_dependency_detection` | Build System | app | advanced | Frontend/bundled apps have a size budget or analyzer in CI (size-limit, bundlesize, bundle analyzer with thresholds, Lighthouse CI budgets). Skip for non-bundled apps. |
| **Version drift detection**<br>`version_drift_detection` | Build System | repo | advanced | Monorepos keep shared dependency versions aligned (syncpack, manypkg, pnpm catalogs, Renovate group rules, Bazel/Gradle version catalogs). Skip for single-app repos. |
| **Flaky test detection**<br>`flaky_test_detection` | Testing | repo | advanced | Flaky tests are detected or quarantined (retry-and-report, quarantine lists, Trunk/BuildPulse/Datadog CI visibility, stress-run jobs, flaky-test issue automation). |
| **Test performance tracked**<br>`test_performance_tracking` | Testing | repo | advanced | Test durations or benchmarks are tracked (slowest-test reporting, --durations in CI, benchmark workflows, CI analytics). |
| **Docs generated**<br>`automated_doc_generation` | Documentation | repo | advanced | Some docs are generated from source and kept in sync automatically (TypeDoc, Sphinx autodoc, rustdoc/godoc published, OpenAPI generation in CI, docs site build). |
| **Environment verified**<br>`devcontainer_runnable` | Dev Environment | repo | advanced | The reproducible environment is exercised in CI (devcontainers/ci action, Nix build in CI, compose-based test job) so it doesn't rot. Skip if no environment definition exists (devcontainer already fails). |
| **Alerting**<br>`alerting_configured` | Debugging & Observability | repo | advanced | Alert rules are defined as code or documented (Prometheus/Alertmanager rules, Datadog/Grafana monitors-as-code, PagerDuty/Opsgenie integration, Sentry alert rules referenced). Skip for libraries. |
| **Deploy observability**<br>`deployment_observability` | Debugging & Observability | repo | advanced | Deploys are visible in monitoring (release markers in Sentry/Datadog, deploy annotations, dashboards linked from docs) so regressions can be tied to a release. Skip for libraries. |
| **Profiling**<br>`profiling_instrumentation` | Debugging & Observability | app | advanced | Performance can be profiled in a standard way (pprof endpoints, continuous profiling like Pyroscope/Datadog, documented profiling scripts, benchmark harnesses). |
| **Runbooks**<br>`runbooks_documented` | Debugging & Observability | repo | intermediate | Operational runbooks exist (runbooks/ or docs/ops, incident playbooks, linked from alerts or docs). Skip for libraries. |
| **Code quality metrics**<br>`code_quality_metrics` | Debugging & Observability | repo | intermediate | Code health is measured over time (coverage trend, SonarQube/CodeClimate/Codacy, DeepSource, CI-published quality reports). |
| **Log scrubbing**<br>`log_scrubbing` | Security & Governance | app | advanced | Logs redact sensitive fields (logger redact config, scrubbing processors, Sentry beforeSend scrubbing). Skip for libraries and CLIs. |
| **PII handling**<br>`pii_handling` | Security & Governance | app | advanced | Apps that handle personal data have an explicit approach (data classification, PII-tagged fields, encryption at rest for sensitive columns, documented retention). Skip if no personal data. |
| **Static security analysis**<br>`automated_security_review` | Security & Governance | repo | intermediate | Application source or dependencies are scanned for vulnerabilities on PRs (CodeQL, Semgrep, Snyk, SonarQube security, Bandit, gosec, npm/pip/cargo audit, osv-scanner). Linters that only scan CI workflow files (e.g. zizmor, actionlint) don't count. |
| **Healthy backlog**<br>`backlog_health` | Task Discovery | repo | intermediate | Open issues are descriptive and triaged: clear titles, bodies with context, labels applied, stale issues closed. Skip if the repo doesn't use an issue tracker visible to the agent. |
| **Product analytics**<br>`product_analytics_instrumentation` | Product & Experimentation | app | intermediate | User-facing apps instrument product events (PostHog, Amplitude, Mixpanel, Segment, GA4, Plausible, Vercel Analytics). Skip for libraries, CLIs and internal infrastructure. |

## Level 5: Autonomous

The system checks and improves itself; agents can take on long-running work end to end.

| Criterion | Pillar | Scope | Difficulty | Passes when |
|---|---|---|---|---|
| **Progressive rollout**<br>`progressive_rollout` | Build System | repo | advanced | Deploys can roll out gradually (canary, percentage rollouts, blue/green, Argo Rollouts, Flagger, platform traffic splitting). Skip for libraries/CLIs. |
| **Automated rollback**<br>`rollback_automation` | Build System | repo | advanced | There is a documented one-step or automatic rollback (platform instant rollback, rollback workflow, Argo/Flagger auto-abort on bad metrics). Skip for libraries/CLIs. |
| **Stale flag cleanup**<br>`dead_feature_flag_detection` | Build System | repo | advanced | Stale feature flags are detected and cleaned up (flag provider stale reports wired to issues, Piranha, a CI check). Skip if there is no flag system. |
| **Agent instructions verified**<br>`agents_md_validation` | Documentation | repo | advanced | Something checks that the agent instructions stay true: a CI job that runs the documented commands, an automated AGENTS.md updater, or a scheduled agent that refreshes it. |
| **Resilience patterns**<br>`circuit_breakers` | Debugging & Observability | app | advanced | Calls to external dependencies use circuit breakers/bulkheads/timeouts via a library or mesh (opossum, resilience4j, Polly, pybreaker, gobreaker, Istio/Envoy policies). Skip for apps without external dependencies. |
| **Dynamic security testing**<br>`dast_scanning` | Security & Governance | app | advanced | Running web apps are scanned dynamically (OWASP ZAP, Burp, Nuclei, StackHawk) in CI or on a schedule. Skip for non-web apps. |
| **Privacy compliance**<br>`privacy_compliance` | Security & Governance | repo | advanced | User-facing products that collect personal data have privacy controls in code (consent management, data export/deletion paths, documented DPA/GDPR handling). Skip otherwise. |
| **Experimentation**<br>`experimentation_infrastructure` | Product & Experimentation | app | advanced | User-facing apps can run A/B tests or experiments (GrowthBook, Statsig, Optimizely, PostHog experiments, LaunchDarkly experiments). Skip for libraries, CLIs and infrastructure. |
| **Errors become tasks**<br>`error_to_insight_pipeline` | Product & Experimentation | repo | advanced | Production errors or user feedback flow automatically into the task tracker (Sentry/Bugsnag-to-issue integration, feedback-to-issue automation, an agent that files issues from alerts). |

## Pillars

- **Style & Validation**: Linters, type checkers and formatters catch mistakes in seconds, so agents don't burn cycles waiting on CI to find a typo.
- **Build System**: Deterministic, documented build and release commands let an agent verify its change compiles and ships without guessing flags.
- **Testing**: Fast, locally runnable tests are the agent's feedback loop: change, run, read the failure, iterate.
- **Documentation**: Written instructions replace tribal knowledge. Agents only know what is discoverable in the repo.
- **Dev Environment**: Reproducible environments remove 'works on my machine' for humans and agents alike.
- **Debugging & Observability**: Logs, traces and metrics turn 'it failed' into 'it failed because X was null in Y', which an agent can act on.
- **Security & Governance**: Agents move fast. Branch protection, secret scanning and ownership rules make sure they move fast safely.
- **Task Discovery**: Structured issues, labels and templates let an agent find, scope and report on work without a human translating.
- **Product & Experimentation**: Analytics and experiments let an agent see whether a change mattered, not just whether it compiled.
