# Agent Readiness: fastapi

**Level 2: Documented** | 66% of applicable criteria passing (37/56, 26 skipped)
Next: Level 3 (Standardized) needs 80% of Level 2; currently 57%, about 4 more criteria to pass.

| Level | Name | Passing | Status |
|---|---|---|---|
| 1 | Functional | 89% (8/9) | achieved |
| 2 | Documented | 57% (8/14) | current |
| 3 | Standardized | 73% (11/15) | locked |
| 4 | Optimized | 62% (10/16) | locked |
| 5 | Autonomous | 0% (0/2) | locked |

| Pillar | Passing |
|---|---|
| Style & Validation | 50% (6/12) |
| Build System | 83% (10/12) |
| Testing | 88% (7/8) |
| Documentation | 57% (4/7) |
| Dev Environment | 50% (1/2) |
| Debugging & Observability | 100% (2/2) |
| Security & Governance | 50% (4/8) |
| Task Discovery | 75% (3/4) |
| Product & Experimentation | 0% (0/1) |

## Highest-impact next steps

1. **Add an AGENTS.md with dev commands and conventions** (`agents_md`): Commit AGENTS.md giving `uv sync` + `prek install` as the bootstrap, `bash scripts/test.sh`, `bash scripts/lint.sh`, `bash scripts/format.sh`, the 100% coverage rule, the docs_src/tests pairing and naming conventions
   - Now: Contributor instructions live off-repo (contributing.md is a 7-line link to tiangolo.com), so agents must reverse-engineer setup from CI YAML; the same gap fails single_command_setup and naming_consistency at Level 2
2. **Add a pull request template** (`pr_templates`): Add .github/pull_request_template.md covering title format, label, regression test and docs_src example checklist
   - Now: PRs need an emoji-prefixed title and a latest-changes label (a required check), but nothing tells an agent that before it opens one
3. **Add CODEOWNERS** (`codeowners`): Add .github/CODEOWNERS mapping fastapi/ and tests/ to core maintainers and docs/<lang>/ to translation reviewers
   - Now: No path ownership exists, so agents can't tell who reviews fastapi/ versus docs/<lang>/ translations

## Failing at Level 2 and below

- L1 `gitignore_comprehensive`: missing patterns: .env
- L2 `single_command_setup`: No setup script/Makefile target and no committed doc giving a bootstrap command; docs/en/docs/contributing.md defers to an external tiangolo.com page
- L2 `devcontainer`: No devcontainer, Nix, devbox or dev Dockerfile
- L2 `agents_md`: No AGENTS.md or harness-specific agent instructions
- L2 `codeowners`: No CODEOWNERS file
- L2 `naming_consistency`: Ruff selects E,W,F,I,B,C4,UP only (no pep8-naming N rules) and the in-repo contributing.md is a 7-line stub linking to tiangolo.com; no committed naming rules
- L2 `pr_templates`: No pull request template

_Generated 2026-11-01T02:39:09+00:00 at 45cb2252c7 by the agent-readiness skill. Scoring follows the 5-level, 80%-gated model popularized by Factory's Agent Readiness Model._
