# AGENTS.md outline

AGENTS.md is the cross-harness file most coding agents read on startup. Fill each section from what is true in the repo. Delete sections that don't apply, and keep the whole file roughly under 200 lines. Agents read every line, every session.

```markdown
# <Project name>

<One or two sentences: what this is, who uses it, what's deployed where.>

## Map
- `apps/web/`: <what it is, framework>
- `apps/api/`: <what it is, framework>
- `packages/shared/`: <what lives here>
<Only the directories an agent needs to navigate. Skip the obvious ones.>

## Commands
| Task | Command |
|---|---|
| Install | `pnpm install` |
| Dev server | `pnpm dev` (web on :3000, api on :4000) |
| Test (all) | `pnpm test` |
| Test (one file) | `pnpm vitest run path/to/file.test.ts` |
| Lint / fix | `pnpm lint` / `pnpm lint --fix` |
| Typecheck | `pnpm typecheck` |
| Build | `pnpm build` |
<Every command here must actually work. Verify before writing it down.>

## Before you finish a change
1. `pnpm lint && pnpm typecheck && pnpm test` all pass.
2. <Any codegen to re-run, e.g. `pnpm db:generate` after schema changes.>
3. <Docs or changelog to update.>

## Conventions
- <Naming, file layout, import style, error handling. Only rules that aren't enforced by a linter.>
- <Patterns to copy: "New API routes follow apps/api/src/routes/users.ts".>

## Environment
- Copy `.env.example` to `.env`. <Which variables are required for local dev, and where real values come from.>
- <Local services: `docker compose up -d` starts Postgres and Redis.>

## Gotchas
- <Things that have bitten people: flaky tests, slow steps, generated files not to edit, ports, platform quirks.>

## Don't
- <Hard boundaries: don't edit generated/, don't change public API without a version bump, never commit .env.>
```

Tips:

- Prefer commands over prose. An agent can run `pnpm test` but can't run "make sure tests pass".
- Point to example files instead of describing patterns at length.
- If CLAUDE.md, GEMINI.md, .cursor/rules or copilot-instructions.md exist, make AGENTS.md the source of truth and have them reference it, e.g. a CLAUDE.md that says `See AGENTS.md`.
