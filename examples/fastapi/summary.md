# Agent Readiness: fastapi

**Level 2: Documented** | 61% of applicable criteria passing (36/59, 34 skipped)
Next: Level 3 (Standardized) needs 80% of Level 2; currently 47%, about 5 more criteria to pass.

| Level | Name | Passing | Status |
|---|---|---|---|
| 1 | Functional | 89% (8/9) | achieved |
| 2 | Documented | 47% (7/15) | current |
| 3 | Standardized | 65% (11/17) | locked |
| 4 | Optimized | 59% (10/17) | locked |
| 5 | Autonomous | 0% (0/1) | locked |

| Pillar | Passing |
|---|---|
| Style & Validation | 46% (6/13) |
| Build System | 83% (10/12) |
| Testing | 78% (7/9) |
| Documentation | 67% (4/6) |
| Dev Environment | 50% (1/2) |
| Debugging & Observability | 100% (2/2) |
| Security & Governance | 44% (4/9) |
| Task Discovery | 40% (2/5) |
| Product & Experimentation | 0% (0/1) |

**Fix lanes:** 6 auto-fix · 17 your call · 0 manual

## Highest-impact next steps

1. **Add an AGENTS.md with dev commands and conventions** [Your call] (`agents_md`): Commit a <200-line AGENTS.md giving `uv sync` + `prek install` as the bootstrap, `bash scripts/test.sh` and `bash scripts/test.sh tests/test_x.py::test_y`, `bash scripts/lint.sh`/`format.sh`, the 100% coverage gate, the docs_src/tests/test_tutorial pairing and naming rules
   - Now: The only in-repo contributing doc is a 7-line link to tiangolo.com, so agents reverse-engineer setup from CI YAML; the same gap fails single_test_command, single_command_setup and naming_consistency at Level 2
2. **Add a pull request template** [Auto-fix] (`pr_templates`): Add .github/pull_request_template.md with title format, label, regression test and docs_src example checklist
   - Now: PRs need an emoji-prefixed title and a label for the required latest-changes/label check, and regression-test proof is checked in CI, but nothing tells an agent before it opens a PR
3. **Add CODEOWNERS covering code and agent prompts** [Your call] (`codeowners`): Add .github/CODEOWNERS with a `*` maintainer default plus entries for fastapi/.agents/, scripts/general-llm-prompt.md and docs/*/llm-prompt.md
   - Now: No path ownership and the master ruleset needs 0 approvals, so changes to fastapi/, docs/<lang>/ and the agent prompts (fastapi/.agents/, docs/*/llm-prompt.md) have no designated reviewer; also fails agent_config_reviewed at Level 3

## Failing at Level 2 and below

- L1 `gitignore_comprehensive`: .gitignore has env/venv/dist/.idea/.DS_Store but not .env or .venv (uv's default env dir)
- L2 `single_command_setup`: No setup script, Makefile or justfile target and no committed doc naming a bootstrap command; `uv sync` + `prek install` must be inferred from pyproject.toml and CI YAML
- L2 `devcontainer`: No devcontainer, Nix, devbox or dev Dockerfile
- L2 `agents_md`: No AGENTS.md or harness-specific agent instructions
- L2 `codeowners`: No CODEOWNERS file
- L2 `naming_consistency`: Ruff selects no pep8-naming (N) rules and the only in-repo contributing doc (docs/en/docs/contributing.md, 7 lines) links off-repo to tiangolo.com; no committed naming rules
- L2 `issue_templates`: Only .github/ISSUE_TEMPLATE/privileged.yml (one free-form 'Issue Content' box for maintainers) plus config.yml links; no repro or acceptance-criteria fields. The bug-report repro form lives in DISCUSSION_TEMPLATE/questions.yml, not issues
- L2 `pr_templates`: No pull request template
- L2 `single_test_command`: No in-repo doc shows running one test; scripts/test.sh forwards ${@} so `bash scripts/test.sh tests/test_x.py::test_y` would work, but nothing says so

_Generated 2026-11-01T03:22:47+00:00 at 45cb2252c7 by the agent-readiness skill. Scoring follows the 5-level, 80%-gated model popularized by Factory's Agent Readiness Model._
