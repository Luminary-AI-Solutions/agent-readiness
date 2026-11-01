#!/usr/bin/env python3
"""Collect deterministic agent-readiness evidence for a repository.

Writes a draft report (same schema as the final report) in which every
criterion has a provisional status: pass / fail / skip from file, config,
git and platform-CLI checks, or "review" where judgment is needed. The agent
running the skill confirms or overrides each entry, then runs report.py.

Standard library only. Python 3.8+.

    python scan.py [REPO] [--out DIR] [--offline] [--apps apps/web=web,apps/api=service]
"""
import argparse
import datetime as dt
import fnmatch
import json
import os
import re
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
CRITERIA = json.loads((SKILL_DIR / "references" / "criteria.json").read_text(encoding="utf-8"))
SKILL_VERSION = "0.1.0"
SCHEMA_VERSION = 1

ALWAYS_EXCLUDED = {".git", "node_modules", "vendor", ".venv", "venv", "__pycache__", ".next", ".nuxt",
                   ".turbo", ".cache", ".tox", ".mypy_cache", ".pytest_cache", ".ruff_cache", ".gradle",
                   "Pods", ".terraform", ".agent-readiness", ".svelte-kit", "bower_components", "coverage"}
WALK_EXCLUDED = ALWAYS_EXCLUDED | {"dist", "build", "target", "out", ".output"}
MAX_FILES = 150_000
MAX_SOURCE_FILES = 6_000
MAX_TEXT = 400_000

MANIFESTS = {"package.json", "pyproject.toml", "setup.py", "setup.cfg", "requirements.txt", "Pipfile", "go.mod",
             "Cargo.toml", "Gemfile", "composer.json", "pom.xml", "build.gradle", "build.gradle.kts", "mix.exs",
             "pubspec.yaml", "Package.swift", "deno.json", "deno.jsonc"}
MANIFEST_GLOBS = ["*.csproj", "*.fsproj", "requirements*.txt"]

LANG_EXT = {
    ".ts": "TypeScript", ".tsx": "TypeScript", ".mts": "TypeScript", ".cts": "TypeScript",
    ".js": "JavaScript", ".jsx": "JavaScript", ".mjs": "JavaScript", ".cjs": "JavaScript",
    ".py": "Python", ".go": "Go", ".rs": "Rust", ".rb": "Ruby", ".java": "Java", ".kt": "Kotlin",
    ".kts": "Kotlin", ".scala": "Scala", ".cs": "C#", ".fs": "F#", ".php": "PHP", ".swift": "Swift",
    ".c": "C", ".h": "C", ".cc": "C++", ".cpp": "C++", ".hpp": "C++", ".cxx": "C++", ".ex": "Elixir",
    ".exs": "Elixir", ".dart": "Dart", ".vue": "Vue", ".svelte": "Svelte", ".lua": "Lua", ".zig": "Zig",
}
STATIC_LANGS = {"Go", "Rust", "Java", "Kotlin", "Scala", "C#", "F#", "Swift", "C", "C++", "Dart", "Zig"}
SOURCE_EXT = set(LANG_EXT) | {".html", ".astro"}

AGENT_FILES = ["AGENTS.md", "CLAUDE.md", "GEMINI.md", ".cursorrules", ".windsurfrules", ".clinerules",
               ".github/copilot-instructions.md", "CONVENTIONS.md"]
AGENT_DIRS = [".claude/", ".cursor/", ".codex/", ".factory/", ".agents/", ".gemini/", ".windsurf/", ".roo/",
              ".kiro/", ".clinerules/", ".continue/", ".amp/", ".opencode/", ".github/copilot-instructions.md",
              ".github/instructions/", ".github/prompts/"]
AGENT_TRAILER = re.compile(
    r"co-authored-by:.*\b(claude|anthropic|copilot|cursor|codex|openai|droid|factory|devin|aider|gemini|"
    r"jules|openhands|amp|sweep|windsurf|cline|kiro|codegen)\b", re.I)

CI_FILES = [".github/workflows/*.yml", ".github/workflows/*.yaml", ".gitlab-ci.yml", ".circleci/*",
            "azure-pipelines.yml", "Jenkinsfile", ".buildkite/*", "bitbucket-pipelines.yml", ".travis.yml",
            ".drone.yml", "cloudbuild.yaml", ".woodpecker.yml", ".woodpecker/*"]

# Dependency / config regexes reused by several checks.
SERVER_DEPS = [r'"express"', r'"fastify"', r'"koa"', r'"hono"', r'"@nestjs/core"', r'"next"', r'"@remix-run/',
               r'"nuxt"', r'"@sveltejs/kit"', r'"astro"', r"\bfastapi\b", r"\bflask\b", r"\bdjango\b",
               r"\bstarlette\b", r"\baiohttp\b", r"gin-gonic/gin", r"labstack/echo", r"gofiber/fiber",
               r"go-chi/chi", r"gorilla/mux", r"\bactix-web\b", r"\baxum\b", r"\brocket\b", r"\brails\b",
               r"\bsinatra\b", r"spring-boot", r"\blaravel\b", r"\bphoenix\b", r"\bktor\b"]
FRONTEND_DEPS = [r'"react"', r'"vue"', r'"svelte"', r'"@angular/core"', r'"solid-js"', r'"preact"', r'"next"',
                 r'"nuxt"', r'"astro"', r'"lit"']
BUNDLER_DEPS = [r'"vite"', r'"webpack"', r'"next"', r'"rollup"', r'"esbuild"', r'"parcel"', r'"@rspack/',
                r'"turbopack"', r'"nuxt"', r'"@sveltejs/kit"', r'"astro"', r'"tsup"']
DB_DEPS = [r'"prisma"', r'"@prisma/client"', r'"drizzle-orm"', r'"typeorm"', r'"sequelize"', r'"mongoose"',
           r'"knex"', r'"pg"', r'"mysql2"', r'"better-sqlite3"', r'"sqlite3"', r'"@supabase/supabase-js"',
           r'"kysely"', r'"@neondatabase/', r"\bsqlalchemy\b", r"\bdjango\b", r"\bpsycopg", r"\basyncpg\b",
           r"\bpymongo\b", r"\bsqlmodel\b", r"\bpeewee\b", r"\btortoise-orm\b", r"gorm\.io", r"jmoiron/sqlx",
           r"jackc/pgx", r"\bdiesel\b", r"\bsea-orm\b", r"\bsqlx\b", r"\bactiverecord\b", r"\brails\b",
           r"\bhibernate\b", r"spring-boot-starter-data", r"\bEntityFrameworkCore\b", r"\becto\b"]
DEPLOY_FILES = ["Dockerfile", "*/Dockerfile", "fly.toml", "vercel.json", "netlify.toml", "render.yaml",
                "railway.json", "railway.toml", "app.yaml", "Procfile", "wrangler.toml", "wrangler.json",
                "wrangler.jsonc", "k8s/*", "kubernetes/*", "helm/*", "charts/*", "serverless.yml",
                "amplify.yml", "*.tf", "skaffold.yaml", "Chart.yaml"]


# Context words meaning a rule is switched off rather than enforced.
DISABLED = r"\bignore|\bdisable|extend-ignore|unfixable|per-file-ignores|[\"']off[\"']|:\s*0\b|\bskip"
# Manifest lines naming the package itself. They're stripped before dependency matching so a
# project named "fastapi" or "express" isn't mistaken for an app built on that framework.
OWN_NAME = re.compile(r"""^\s*(name\s*=\s*["'][^"']*["']|"name"\s*:\s*"[^"]*",?)\s*$|^module\s+\S+\s*$""", re.M)


def enclosing_context(txt, pos):
    """The line containing pos, plus the opening line of a multi-line list it sits in."""
    start = txt.rfind("\n", 0, pos) + 1
    end = txt.find("\n", pos)
    ctx = txt[start:end if end >= 0 else len(txt)]
    opener = txt.rfind("[", 0, pos)
    if opener >= 0 and "]" not in txt[opener:pos]:
        ctx += " " + txt[txt.rfind("\n", 0, opener) + 1:opener + 1]
    return ctx


def run(cmd, cwd, timeout=30):
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout,
                           encoding="utf-8", errors="replace")
        return p.returncode, p.stdout, p.stderr
    except (OSError, subprocess.TimeoutExpired) as e:
        return -1, "", str(e)


def short(items, n=4):
    items = list(dict.fromkeys(items))
    more = len(items) - n
    return ", ".join(items[:n]) + (f" (+{more} more)" if more > 0 else "")


class Repo:
    def __init__(self, root: Path, offline: bool):
        self.root = root
        self.offline = offline
        self.is_git = run(["git", "rev-parse", "--is-inside-work-tree"], root)[1].strip() == "true"
        self.files = self._list_files()
        self.lower_map = {f.lower(): f for f in self.files}
        self._text = {}
        self.ci_files = self.find(CI_FILES)
        self.config_files = [f for f in self.files if self._is_config(f)]
        self.manifest_files = [f for f in self.files if self._is_manifest(f)]
        self.source_hits = {}
        self.gh = GitHub(self) if not offline else None

    # --- file index -------------------------------------------------------
    def _list_files(self):
        files = []
        if self.is_git:
            code, out, _ = run(["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
                               self.root, timeout=120)
            if code == 0:
                for f in out.split("\0"):
                    if f and not (set(f.split("/")[:-1]) & ALWAYS_EXCLUDED) and (self.root / f).is_file():
                        files.append(f)
                        if len(files) >= MAX_FILES:
                            break
                return sorted(files)
        for dirpath, dirnames, filenames in os.walk(self.root):
            dirnames[:] = [d for d in dirnames if d not in WALK_EXCLUDED]
            rel = Path(dirpath).relative_to(self.root).as_posix()
            for name in filenames:
                files.append(name if rel == "." else f"{rel}/{name}")
            if len(files) >= MAX_FILES:
                break
        return sorted(files)

    @staticmethod
    def _is_manifest(f):
        name = f.rsplit("/", 1)[-1]
        return name in MANIFESTS or any(fnmatch.fnmatch(name, g) for g in MANIFEST_GLOBS)

    @staticmethod
    def _is_config(f):
        parts = f.split("/")
        name = parts[-1].lower()
        if parts[0] in (".github", ".gitlab", ".circleci", ".husky", ".githooks", ".buildkite", ".devcontainer",
                        ".changeset", ".woodpecker"):
            return True
        if len(parts) > 4:
            return False
        if name.endswith((".json", ".jsonc", ".yaml", ".yml", ".toml", ".cfg", ".ini", ".conf", ".hcl",
                          ".properties", ".xml", ".gradle", ".kts", ".neon", ".mk")):
            return not name.endswith(("lock.json", ".lock", "lock.yaml")) and name != "package-lock.json"
        if re.search(r"(^|\.)(config|rc)\.(c|m)?(js|ts)$|^\.[\w-]+rc(\.(c|m)?js)?$", name):
            return True
        return name in {"makefile", "justfile", "taskfile.yml", "dockerfile", "jenkinsfile", "procfile",
                        "tiltfile", "noxfile.py", "conftest.py", "setup.py", "dangerfile.js", "dangerfile.ts",
                        "gemfile", ".gitattributes", ".gitignore", ".bazelrc", "build.bazel", "workspace"}

    def text(self, f, limit=MAX_TEXT):
        if f not in self._text:
            try:
                with open(self.root / f, "r", encoding="utf-8", errors="ignore") as fh:
                    self._text[f] = fh.read(limit)
            except OSError:
                self._text[f] = ""
        return self._text[f]

    def json(self, f):
        try:
            return json.loads(self.text(f))
        except (ValueError, TypeError):
            return None

    def exists(self, f):
        return f.lower() in self.lower_map

    def find(self, patterns, under="", anchored=False):
        """Glob-match tracked files. Patterns without '/' match basenames anywhere under `under`;
        patterns with '/' match paths relative to `under`; patterns ending in '/' match that
        directory anywhere, or only at the top of `under` when anchored. Case-insensitive."""
        prefix = "" if under in ("", ".") else under.rstrip("/") + "/"
        out = []
        for f in self.files:
            if prefix and not f.startswith(prefix):
                continue
            rel = f[len(prefix):].lower()
            base = rel.rsplit("/", 1)[-1]
            for p in patterns:
                p = p.lower()
                if p.endswith("/"):
                    if rel.startswith(p) or (not anchored and ("/" + p) in ("/" + rel)):
                        out.append(f)
                        break
                elif ("/" in p and fnmatch.fnmatch(rel, p)) or ("/" not in p and fnmatch.fnmatch(base, p)):
                    out.append(f)
                    break
        return out

    def scoped(self, files, app):
        """Files that apply to an app: inside the app dir, or repo-level (top level / tooling dirs)."""
        if app.path == ".":
            return files
        prefix = app.path + "/"
        return [f for f in files if f.startswith(prefix) or "/" not in f or
                f.split("/")[0] in (".github", ".gitlab", ".circleci", ".husky", ".githooks", ".devcontainer",
                                    ".buildkite", "scripts", "tools", ".changeset")]

    def grep(self, regexes, files, flags=re.I, reject=None):
        """First match per (regex, file). With `reject`, a match is skipped when its line, or the
        key of the list it sits in (e.g. `ignore = [`), matches `reject`."""
        hits = []
        rej = re.compile(reject, re.I) if reject else None
        for rx in regexes:
            r = re.compile(rx, flags)
            for f in files:
                txt = self.text(f)
                for m in r.finditer(txt):
                    if rej and rej.search(enclosing_context(txt, m.start())):
                        continue
                    hits.append(f"{f} ({m.group(0).strip()[:40]})")
                    break
        return hits

    # --- one pass over source files ----------------------------------------
    SOURCE_PATTERNS = {
        "env_read": r"process\.env|import\.meta\.env|os\.environ|os\.getenv|env::var|os\.Getenv|ENV\[|"
                    r"System\.getenv|GetEnvironmentVariable|Deno\.env",
        "health": r"""["'`]/(api/)?(health|healthz|healthcheck|ready|readyz|livez|ping)["'`/?]""",
        "redact": r"\bredact|\bscrub|before_?send|send_default_pii|\bmask(Sensitive|PII)",
        "secret_literal": r"AKIA[0-9A-Z]{16}|sk_live_[0-9a-zA-Z]{20,}|ghp_[0-9A-Za-z]{36}|"
                          r"xox[baprs]-[0-9A-Za-z-]{10,}|-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----|"
                          r"AIza[0-9A-Za-z_\-]{35}",
        "todo": r"\b(TODO|FIXME|HACK|XXX)\b",
        "rust_test": r"#\[(tokio::)?test\]",
        "profiling": r"net/http/pprof|pyroscope|cProfile|@datadog/pprof|\bpprof\b|py-spy|async-profiler",
        "analytics": r"posthog|gtag\(|plausible|umami|amplitude|mixpanel|@vercel/analytics|segment\.(com|io)",
        "pii": r"\bpii\b|personal.?data|gdpr|ccpa|data.?retention|anonymi[sz]",
        "breaker": r"circuit.?breaker|CircuitBreaker|bulkhead",
    }

    def scan_sources(self):
        compiled = {k: re.compile(v) for k, v in self.SOURCE_PATTERNS.items()}
        sources = [f for f in self.files if os.path.splitext(f)[1].lower() in SOURCE_EXT]
        for f in sources[:MAX_SOURCE_FILES]:
            try:
                with open(self.root / f, "r", encoding="utf-8", errors="ignore") as fh:
                    txt = fh.read(MAX_TEXT)
            except OSError:
                continue
            for k, rx in compiled.items():
                if rx.search(txt):
                    self.source_hits.setdefault(k, []).append(f)
        self.source_truncated = len(sources) > MAX_SOURCE_FILES

    def source(self, key, app, exclude_tests=False):
        hits = self.source_hits.get(key, [])
        if app.path != ".":
            hits = [f for f in hits if f.startswith(app.path + "/")]
        if exclude_tests:
            hits = [f for f in hits if not re.search(r"(^|/)(tests?|__tests__|spec|e2e|fixtures?)/|"
                                                     r"[._-](test|spec)\.|_test\.", f)]
        return hits

    # --- git ----------------------------------------------------------------
    def git(self, *args, timeout=30):
        if not self.is_git:
            return ""
        code, out, _ = run(["git", *args], self.root, timeout)
        return out if code == 0 else ""

    def last_commit_ts(self, path=None):
        out = self.git("log", "-1", "--format=%ct", *(["--", path] if path else []))
        return int(out.strip()) if out.strip().isdigit() else None


class GitHub:
    """Optional signals from the `gh` CLI. Every call degrades to None."""

    def __init__(self, repo):
        self.repo = repo
        self.slug = None
        self.available = False
        self.authed = False
        self.info = {}
        url = repo.git("remote", "get-url", "origin").strip()
        self.remote_url = url
        m = re.search(r"github\.com[:/]([^/\s]+)/([^/\s]+?)(\.git)?/?$", url)
        if not m or not shutil.which("gh"):
            return
        self.slug = f"{m.group(1)}/{m.group(2)}"
        self.available = True
        code, _, _ = run(["gh", "auth", "status"], repo.root, 20)
        self.authed = code == 0
        if self.authed:
            self.info = self.api(f"repos/{self.slug}") or {}

    def api(self, path, timeout=30):
        if not self.authed:
            return None
        code, out, _ = run(["gh", "api", path], self.repo.root, timeout)
        if code != 0:
            return None
        try:
            return json.loads(out)
        except ValueError:
            return None

    def api_status(self, path):
        code, out, err = run(["gh", "api", "-i", path], self.repo.root, 30)
        m = re.match(r"HTTP/\S+ (\d+)", out or "")
        return int(m.group(1)) if m else (None if code else 200), out

    def cli_json(self, *args, timeout=60):
        if not self.authed:
            return None
        code, out, _ = run(["gh", *args, "-R", self.slug], self.repo.root, timeout)
        if code != 0:
            return None
        try:
            return json.loads(out)
        except ValueError:
            return None

    @property
    def default_branch(self):
        return self.info.get("default_branch")


class App:
    KINDS = ("service", "web", "library", "cli")

    def __init__(self, repo, path, kind=None):
        self.path = path
        self.kind_override = kind
        prefix = "" if path == "." else path + "/"
        files = [f for f in repo.files if f.startswith(prefix)] if prefix else repo.files
        exts = Counter(LANG_EXT[e] for e in (os.path.splitext(f)[1].lower() for f in files) if e in LANG_EXT)
        total = sum(exts.values()) or 1
        self.languages = [l for l, n in exts.most_common(4) if n / total >= 0.08] or [l for l, _ in exts.most_common(1)]
        self.manifests = [f for f in repo.manifest_files if (f.startswith(prefix) if prefix else True)
                          and f.count("/") <= prefix.count("/") + 1]
        root_manifests = [f for f in repo.manifest_files if "/" not in f]
        self.manifest_text = OWN_NAME.sub("", "\n".join(repo.text(f) for f in dict.fromkeys(self.manifests + root_manifests)))
        self.own_manifest_text = OWN_NAME.sub("", "\n".join(repo.text(f) for f in self.manifests))
        self.config = repo.scoped(repo.config_files, self)
        self.is_server = self.has_dep(SERVER_DEPS)
        self.is_frontend = self.has_dep(FRONTEND_DEPS) or bool(repo.find(["index.html"], path)) and not self.is_server
        self.has_bundler = self.has_dep(BUNDLER_DEPS)
        self.has_db = self.has_dep(DB_DEPS) or bool(repo.find(["schema.prisma", "migrations/", "alembic.ini"], path))
        self.source_files = sum(1 for f in files if os.path.splitext(f)[1].lower() in LANG_EXT
                                and not re.search(r"(\.config|rc)\.\w+$", f))
        own_deploy = repo.find(DEPLOY_FILES, path) if path != "." else \
            [f for f in repo.find(DEPLOY_FILES, "") if f.count("/") <= 1 and not f.startswith("docs")]
        self.published = self._published(repo)
        self.deployable = bool(own_deploy) or (self.is_server and not self.published)
        self.is_library = self.kind() in ("library", "cli")
        self.description = self._describe(repo)

    def _published(self, repo):
        """Does the manifest describe a package meant to be installed by others?"""
        for f in self.manifests:
            t, name = repo.text(f), f.rsplit("/", 1)[-1]
            if name == "pyproject.toml" and "[project]" in t and "[build-system]" in t:
                return True
            if name == "setup.py":
                return True
            if name == "package.json":
                j = repo.json(f) or {}
                if not j.get("private") and any(k in j for k in ("main", "exports", "module", "bin", "types")):
                    return True
            if name == "Cargo.toml" and ("[lib]" in t or repo.exists(f.replace("Cargo.toml", "src/lib.rs"))):
                return True
        return bool(repo.find(["*.gemspec"], self.path))

    def has_dep(self, regexes, own=False):
        txt = self.own_manifest_text if own else self.manifest_text
        return any(re.search(r, txt, re.I) for r in regexes)

    def dep_hits(self, regexes):
        return [re.search(r, self.manifest_text, re.I).group(0).strip('"') for r in regexes
                if re.search(r, self.manifest_text, re.I)]

    def _describe(self, repo):
        for f in self.manifests:
            if f.endswith("package.json"):
                d = (repo.json(f) or {}).get("description")
                if d:
                    return d
            if f.endswith("pyproject.toml"):
                m = re.search(r'^description\s*=\s*"([^"]+)"', repo.text(f), re.M)
                if m:
                    return m.group(1)
        return f"{', '.join(self.languages) or 'Unknown language'} {self.kind()}"

    def kind(self):
        if self.kind_override:
            return self.kind_override
        if self.published and not self.deployable:
            return "library"
        if self.is_server:
            return "service"
        if self.is_frontend:
            return "web"
        return "service" if self.deployable else "library"


# --- app discovery ----------------------------------------------------------
def discover_apps(repo):
    globs, tool = [], None
    pkg = repo.json("package.json") or {}
    ws = pkg.get("workspaces")
    if isinstance(ws, dict):
        ws = ws.get("packages")
    if isinstance(ws, list):
        globs += ws
        tool = "npm/yarn workspaces"
    if repo.exists("pnpm-workspace.yaml"):
        block = re.search(r"packages:\s*\n((?:\s*-.*\n?)+)", repo.text("pnpm-workspace.yaml"))
        if block:
            globs += re.findall(r"-\s*['\"]?([^'\"#\n]+?)['\"]?\s*$", block.group(1), re.M)
            tool = "pnpm workspaces"
    lerna = repo.json("lerna.json") or {}
    if lerna.get("packages"):
        globs += lerna["packages"]
        tool = tool or "lerna"
    for f, label in (("Cargo.toml", "cargo workspace"), ("pyproject.toml", "uv workspace")):
        if repo.exists(f):
            m = re.search(r"members\s*=\s*\[([^\]]*)\]", repo.text(f), re.S)
            if m and ("[workspace]" in repo.text(f) or "tool.uv.workspace" in repo.text(f)):
                globs += re.findall(r"['\"]([^'\"]+)['\"]", m.group(1))
                tool = tool or label
    if repo.exists("go.work"):
        globs += [g.strip().lstrip("./") for g in re.findall(r"^\s*(\./[^\s)]+|[\w\-/]+)\s*$",
                  re.sub(r"^(go|toolchain)\s.*$", "", repo.text("go.work"), flags=re.M), re.M)
                  if g.strip() not in ("use", "(", ")")]
        tool = tool or "go workspace"

    manifest_dirs = sorted({f.rsplit("/", 1)[0] for f in repo.manifest_files if "/" in f})
    members = set()
    for g in globs:
        g = g.strip().rstrip("/").lstrip("./")
        if not g or g.startswith("!"):
            continue
        for d in manifest_dirs:
            if fnmatch.fnmatch(d, g) or (g.endswith("/**") and d.startswith(g[:-3])):
                members.add(d)
    if not members:
        conventional = [d for d in manifest_dirs if re.match(r"^(apps|services|packages|cmd|libs)/[^/]+$", d)]
        if len(conventional) >= 2:
            members = set(conventional)
            tool = None
    apps = sorted(members) if members else ["."]
    truncated = len(apps) > 30
    return apps[:30], tool, truncated


def select_apps(repo, paths):
    """Keep independently deployable apps. Shared libraries and config packages in a
    monorepo are only kept when nothing in the workspace is deployable."""
    apps = [App(repo, p) for p in paths]
    if len(apps) == 1:
        return apps, []
    real = [a for a in apps if a.source_files >= 3]
    deployable = [a for a in real if a.deployable or a.is_frontend]
    keep = deployable or real or apps
    return keep, [a.path for a in apps if a not in keep]


# --- checks -----------------------------------------------------------------
# Each check returns (status, rationale). App-scoped checks take (repo, app);
# repo-scoped checks take (repo, apps).
CHECKS = {}


def check(cid):
    def deco(fn):
        CHECKS[cid] = fn
        return fn
    return deco


def by_markers(hits, found, missing_status, missing_msg):
    if hits:
        return "pass", f"{found}: {short(hits)}"
    return missing_status, missing_msg


def cfg(repo, app, regexes):
    files = app.config if app else repo.config_files
    return repo.grep(regexes, files)


@check("lint_config")
def _(repo, app):
    hits = repo.find([".eslintrc*", "eslint.config.*", "biome.json", "biome.jsonc", ".oxlintrc.json", "ruff.toml",
                      ".ruff.toml", ".flake8", ".pylintrc", "pylintrc", ".golangci.y*ml", ".golangci.toml",
                      "clippy.toml", ".clippy.toml", ".rubocop.yml", "checkstyle*.xml", ".swiftlint.yml",
                      ".ktlint*", "detekt.yml", "phpcs.xml*", ".credo.exs", "analysis_options.yaml",
                      "deno.json", "deno.jsonc", ".stylelintrc*"], app.path)
    hits += [f for f in (".eslintrc.json", ".eslintrc.js", ".eslintrc.cjs", "eslint.config.js", "eslint.config.mjs",
                         "biome.json", "ruff.toml", ".golangci.yml") if repo.exists(f)]
    hits += app.dep_hits([r'"eslint"', r'"@biomejs/biome"', r'"oxlint"', r"\[tool\.ruff", r"\[tool\.pylint",
                          r"\bflake8\b", r'"eslintConfig"', r'"next"'])
    if "Rust" in app.languages and repo.grep([r"cargo clippy"], app.config + repo.ci_files):
        hits.append("cargo clippy in CI/scripts")
    if "Go" in app.languages and repo.grep([r"go vet|staticcheck|golangci"], app.config + repo.ci_files):
        hits.append("go vet/staticcheck in CI/scripts")
    if hits == ["next"]:
        return "review", "Next.js present (ships `next lint`) but no explicit ESLint config found"
    return by_markers(hits, "Linter configured", "fail", "No linter configuration found for "
                      f"{', '.join(app.languages) or 'this app'}")


@check("type_check")
def _(repo, app):
    static = [l for l in app.languages if l in STATIC_LANGS]
    if static and not set(app.languages) & {"TypeScript", "JavaScript", "Python", "Ruby", "PHP"}:
        return "pass", f"Statically typed language: {', '.join(static)}"
    hits = []
    if set(app.languages) & {"TypeScript", "JavaScript", "Vue", "Svelte"}:
        hits += repo.find(["tsconfig*.json", "jsconfig.json", "deno.json"], app.path) + \
                [f for f in ("tsconfig.json", "tsconfig.base.json") if repo.exists(f)]
    if "Python" in app.languages:
        hits += repo.find(["mypy.ini", ".mypy.ini", "pyrightconfig.json"], app.path)
        hits += app.dep_hits([r"\[tool\.mypy", r"\[tool\.pyright", r"\[tool\.basedpyright", r"\[mypy\]", r"\bmypy\b",
                              r"\bpyright\b", r"\bty\b\s*[=>]"])
    if "Ruby" in app.languages:
        hits += repo.find(["sorbet/", "*.rbs", "Steepfile"], app.path)
    if "PHP" in app.languages:
        hits += repo.find(["phpstan.neon*", "psalm.xml*"], app.path)
    if not app.languages:
        return "skip", "No source code detected"
    return by_markers(hits, "Type checking configured", "fail",
                      f"Dynamically typed ({', '.join(app.languages)}) with no type checker configured")


@check("formatter")
def _(repo, app):
    hits = repo.find([".prettierrc*", "prettier.config.*", "biome.json", "biome.jsonc", "dprint.json",
                      ".clang-format", "rustfmt.toml", ".rustfmt.toml", ".scalafmt.conf", ".editorconfig-checker*",
                      ".php-cs-fixer*", ".swiftformat", ".formatter.exs"], app.path)
    hits += [f for f in (".prettierrc", ".prettierrc.json", "prettier.config.js", "biome.json") if repo.exists(f)]
    hits += app.dep_hits([r'"prettier"', r'"@biomejs/biome"', r"\[tool\.black", r"\bblack\b",
                          r"\[tool\.ruff\.format", r"\byapf\b", r"\bautopep8\b", r'"prettier":'])
    hits += cfg(repo, app, [r"ruff format", r"gofmt|gofumpt|goimports", r"cargo fmt", r"dotnet format"])
    for lang, tool in (("Go", "gofmt (built into the toolchain)"), ("Rust", "rustfmt (standard toolchain)"),
                       ("Dart", "dart format"), ("Zig", "zig fmt")):
        if lang in app.languages:
            hits.append(tool)
    if repo.exists("deno.json") or repo.exists("deno.jsonc"):
        hits.append("deno fmt")
    return by_markers(hits, "Formatter available", "fail", "No code formatter configured")


@check("strict_typing")
def _(repo, app):
    static = [l for l in app.languages if l in STATIC_LANGS]
    if static and not set(app.languages) & {"TypeScript", "JavaScript", "Python", "Ruby", "PHP"}:
        return "pass", f"Statically typed language: {', '.join(static)}"
    notes, fails = [], []
    if set(app.languages) & {"TypeScript", "JavaScript"}:
        tsconfigs = repo.find(["tsconfig*.json"], app.path) + [f for f in ("tsconfig.json", "tsconfig.base.json")
                                                              if repo.exists(f)]
        txt = "\n".join(repo.text(f) for f in tsconfigs)
        if re.search(r'"strict"\s*:\s*true', txt):
            notes.append("tsconfig strict: true")
        elif re.search(r'"extends"\s*:\s*"[^"]*(strict|strictest)', txt):
            notes.append("tsconfig extends a strict preset")
        elif tsconfigs:
            fails.append("tsconfig without strict: true")
        else:
            fails.append("no tsconfig")
    if "Python" in app.languages:
        if app.has_dep([r"strict\s*=\s*true", r'typeCheckingMode\s*=\s*"strict"', r"--strict"]) or \
                repo.grep([r"strict\s*=\s*(true|True)|typeCheckingMode.*strict|mypy.*--strict"],
                          app.config + repo.ci_files):
            notes.append("mypy/pyright strict")
        else:
            fails.append("Python type checking not strict")
    if not notes and not fails:
        return "skip", "No typed or type-checkable source detected"
    if fails:
        return "fail", "; ".join(fails + notes)
    return "pass", "; ".join(notes)


@check("pre_commit_hooks")
def _(repo, apps):
    hits = repo.find([".pre-commit-config.yaml", ".pre-commit-config.yml", ".husky/", "lefthook.yml",
                      "lefthook.yaml", ".lefthook.yml", "lefthook.toml", ".githooks/", ".simple-git-hooks*",
                      ".lintstagedrc*", "lint-staged.config.*"], "")
    pkg = repo.text("package.json") if repo.exists("package.json") else ""
    if re.search(r'"(simple-git-hooks|husky|lint-staged)"\s*:\s*\{', pkg):
        hits.append("package.json hook config")
    return by_markers(hits, "Commit hooks configured", "fail",
                      "No pre-commit/Husky/lefthook configuration found")


@check("naming_consistency")
def _(repo, app):
    docs = repo.find(AGENT_FILES + ["CONTRIBUTING.md", "STYLEGUIDE.md", "docs/style*"], "")
    hits = repo.grep([r"naming|name (files|components|functions)|camelCase|snake_case|PascalCase|kebab-case"], docs)
    hits += cfg(repo, app, [r"naming-convention|pep8-naming|\bN8\d\d\b|\"N\"|revive|stylecheck|RSpec/.*Name"])
    if hits:
        return "pass", f"Naming conventions documented or enforced: {short(hits, 3)}"
    return "review", "No explicit naming rules found; judge whether conventions are evident and consistent"


@check("large_file_detection")
def _(repo, apps):
    hits = repo.grep([r"filter=lfs"], repo.find([".gitattributes"]))
    hits += repo.grep([r"check-added-large-files|large.?file|max.?file.?size|git-sizer"],
                      repo.config_files + repo.ci_files)
    return by_markers(hits, "Large-file guard present", "fail",
                      "No Git LFS, check-added-large-files hook, or CI size check found")


@check("tech_debt_tracking")
def _(repo, apps):
    hits = repo.grep([r"no-warning-comments|\"TD\"|'TD'|\bTD00\d|\bFIX00\d|todo-tracker|tdg-github-action|"
                      r"todo-to-issue|leasot|godox|fixme"], repo.config_files + repo.ci_files, reject=DISABLED)
    todos = len(repo.source_hits.get("todo", []))
    if hits:
        return "pass", f"TODO tracking configured: {short(hits, 3)}"
    return "fail", f"No TODO/FIXME tracking rule or scanner ({todos} source files contain TODO/FIXME markers)"


@check("dead_code_detection")
def _(repo, app):
    hits = app.dep_hits([r'"knip"', r'"ts-prune"', r'"ts-unused-exports"', r"\bvulture\b", r"\bdeadcode\b"])
    hits += repo.grep([r"\bknip\b|ts-prune|vulture|deadcode|unparam|unused-exports|deny\(dead_code\)"],
                      app.config, reject=DISABLED)
    hits += repo.find(["knip.json", "knip.jsonc", ".knip.json", "knip.config.*"], app.path)
    return by_markers(hits, "Dead code detection configured", "fail", "No dead code detector found")


@check("duplicate_code_detection")
def _(repo, apps):
    hits = repo.find([".jscpd.json", "sonar-project.properties"], "")
    hits += repo.grep([r"\bjscpd\b|\bcpd\b|simian|dupl\b|pylint.*duplicate-code|sonar"],
                      repo.config_files + repo.ci_files)
    return by_markers(hits, "Duplicate code detection configured", "fail", "No copy-paste detection found")


@check("cyclomatic_complexity")
def _(repo, app):
    hits = repo.grep([r"[\"']?complexity[\"']?\s*:\s*\[?\s*[\"']?(error|warn|[12])", r"\bC90\d?\b|mccabe|max-complexity",
                           r"gocyclo|gocognit|cyclop", r"cognitive_complexity", r"\bradon\b|\bxenon\b|\blizard\b",
                           r"sonarjs|sonar", r"Metrics/(Cyclomatic|Perceived)Complexity"], app.config, reject=DISABLED)
    return by_markers(hits, "Complexity limits configured", "fail", "No complexity analysis configured")


@check("code_modularization")
def _(repo, app):
    hits = repo.find([".dependency-cruiser*", ".importlinter", "importlinter.ini", "deptrac.yaml"], app.path)
    hits += cfg(repo, app, [r"dependency-cruiser|eslint-plugin-boundaries|enforce-module-boundaries|"
                            r"import-linter|archunit|no-restricted-imports|import/no-restricted-paths|depguard"])
    if hits:
        return "pass", f"Module boundaries enforced: {short(hits, 3)}"
    return "review", "No boundary-enforcement tooling found; check for deliberate structure (e.g. Go internal/)"


@check("n_plus_one_detection")
def _(repo, app):
    if not app.has_db or app.is_library:
        return "skip", "No database access detected" if not app.has_db else "Library; no database of its own"
    hits = app.dep_hits([r"\bbullet\b", r"\bnplusone\b", r"django-zen-queries", r"\bprosopite\b"])
    hits += repo.grep([r"assertNumQueries|nplusone|bullet|prosopite|query.?count"], app.config)
    if hits:
        return "pass", f"N+1 detection: {short(hits, 3)}"
    return "fail", "Database access detected but no N+1 query detection"


@check("build_cmd_doc")
def _(repo, app):
    docs = repo.find(["README*", "CONTRIBUTING*"] + AGENT_FILES, app.path) + \
        [f for f in repo.find(["README*", "CONTRIBUTING*"] + AGENT_FILES, "") if "/" not in f]
    cmd = (r"(npm|pnpm|yarn|bun) (run |install|i\b|dev|build|start)|make \w+|just \w+|cargo (build|run)|"
           r"go (build|run)|uv (sync|run)|poetry (install|run)|pip install|python -m|bundle (install|exec)|"
           r"gradlew? \w+|mvn \w+|dotnet (build|run)|docker compose up|task \w+|deno task")
    hits = repo.grep([cmd], list(dict.fromkeys(docs)))
    scripts = []
    for f in app.manifests:
        if f.endswith("package.json"):
            s = (repo.json(f) or {}).get("scripts") or {}
            scripts += [k for k in s if k in ("build", "dev", "start", "test")]
    scripts += repo.find(["Makefile", "justfile", "Taskfile.yml"], app.path)
    if hits:
        return "pass", f"Build/run commands documented in {short(h.split(' (')[0] for h in hits)}"
    if scripts:
        return "pass", f"Build/run commands discoverable via scripts: {short(scripts)}"
    return "fail", "No documented build/run commands and no obvious script runner"


@check("deps_pinned")
def _(repo, app):
    if not app.manifests and app.path != ".":
        return "skip", "No dependency manifest"
    pairs = [("package.json", ["package-lock.json", "pnpm-lock.yaml", "yarn.lock", "bun.lockb", "bun.lock",
                               "npm-shrinkwrap.json"]),
             ("pyproject.toml", ["uv.lock", "poetry.lock", "pdm.lock", "Pipfile.lock", "requirements*.txt",
                                 "pixi.lock", "requirements.lock"]),
             ("Pipfile", ["Pipfile.lock"]), ("Cargo.toml", ["Cargo.lock"]), ("go.mod", ["go.sum"]),
             ("Gemfile", ["Gemfile.lock"]), ("composer.json", ["composer.lock"]), ("pubspec.yaml", ["pubspec.lock"]),
             ("Package.swift", ["Package.resolved"]), ("mix.exs", ["mix.lock"]),
             ("build.gradle", ["gradle.lockfile", "libs.versions.toml"]),
             ("build.gradle.kts", ["gradle.lockfile", "libs.versions.toml"]), ("deno.json", ["deno.lock"])]
    missing, found = [], []
    for manifest, locks in pairs:
        if not any(f.rsplit("/", 1)[-1] == manifest for f in app.manifests):
            continue
        lock_hits = repo.find(locks, app.path) + [l for l in repo.find(locks, "") if "/" not in l]
        if manifest == "go.mod" and not re.search(r"^require", repo.text(next(f for f in app.manifests
                                                  if f.endswith("go.mod"))), re.M):
            found.append("go.mod (no external deps)")
        elif lock_hits:
            found.append(lock_hits[0])
        else:
            missing.append(manifest)
    reqs = [f for f in app.manifests if re.search(r"requirements.*\.txt$", f)]
    for r in reqs:
        lines = [l for l in repo.text(r).splitlines() if l.strip() and not l.strip().startswith(("#", "-"))]
        if lines and all("==" in l or "@" in l for l in lines):
            found.append(f"{r} (fully pinned)")
        elif lines and not found:
            missing.append(f"{r} (unpinned ranges)")
    if "pom.xml" in " ".join(app.manifests):
        found.append("pom.xml (explicit versions)")
    if missing:
        return "fail", f"No lockfile for {short(missing)}" + (f"; found {short(found)}" if found else "")
    if found:
        return "pass", f"Lockfiles committed: {short(found)}"
    return "review", "No recognized manifest/lockfile pair; check how dependencies are pinned"


@check("vcs_cli_tools")
def _(repo, apps):
    url = repo.git("remote", "get-url", "origin").strip()
    host = "gitlab" if "gitlab" in url else "github" if "github" in url else None
    tool = {"github": "gh", "gitlab": "glab"}.get(host)
    if not tool:
        return "review", f"Remote host not recognized ({url or 'no origin remote'}); check for its CLI"
    if repo.offline:
        return "review", "Offline scan; check `" + tool + " auth status`"
    if not shutil.which(tool):
        return "fail", f"{tool} CLI not installed in this environment"
    code, _, _ = run([tool, "auth", "status"], repo.root, 20)
    return ("pass", f"{tool} installed and authenticated") if code == 0 else ("fail", f"{tool} installed but not authenticated")


@check("single_command_setup")
def _(repo, apps):
    hits = []
    for mk in repo.find(["Makefile", "justfile", "Taskfile.yml", "Taskfile.yaml", "mise.toml", ".mise.toml"], ""):
        if "/" not in mk and re.search(r"^\s*(setup|bootstrap|init|install|dev-setup)\s*:|\[tasks\.(setup|bootstrap)",
                                       repo.text(mk), re.M):
            hits.append(f"{mk} setup target")
    hits += repo.find(["scripts/setup*", "scripts/bootstrap*", "bin/setup", "script/setup", "script/bootstrap",
                       "setup.sh", "bootstrap.sh", ".devcontainer/devcontainer.json", ".devcontainer.json",
                       "flake.nix", "devbox.json"], "")
    pkg = repo.json("package.json") or {}
    if any(k in (pkg.get("scripts") or {}) for k in ("setup", "bootstrap")):
        hits.append("package.json setup script")
    if hits:
        return "pass", f"One-step setup available: {short(hits, 3)}"
    return "review", "No setup script/target found; check whether README gives a single bootstrap command"


@check("agentic_development")
def _(repo, apps):
    hits = repo.find(AGENT_DIRS, "", anchored=True)
    log = repo.git("log", "-n", "300", "--format=%B")
    trailers = {m.group(1).lower() for m in AGENT_TRAILER.finditer(log)}
    if trailers:
        hits.insert(0, f"agent co-author trailers in recent commits ({', '.join(sorted(trailers))})")
    dirs = sorted({h.split("/")[0] + ("/" if "/" in h else "") for h in hits if not h.startswith("agent co-author")})
    summary = [h for h in hits if h.startswith("agent co-author")] + dirs
    return by_markers(summary, "Agents already in use", "fail", "No agent config or agent co-authored commits found")


@check("automated_pr_review")
def _(repo, apps):
    hits = repo.find([".coderabbit.y*ml", "dangerfile.*", ".github/copilot-review*", ".greptile*", ".sourcery.yaml",
                      ".pr_agent.toml", ".ellipsis.yaml", ".gemini/config.yaml", "bugbot*"], "")
    hits += repo.grep([r"claude-code-action|anthropics/claude|coderabbit|codex|copilot.*review|danger/danger|dangerfile|danger-js|\bdanger (ci|pr)\b|reviewdog|"
                       r"pr-agent|qodo|greptile|ellipsis|sourcery|gemini-code-assist|cursor.*bugbot"], repo.ci_files)
    if hits:
        return "pass", f"Automated PR review configured: {short(hits, 3)}"
    gh = repo.gh
    if gh and gh.authed:
        prs = gh.cli_json("pr", "list", "--state", "merged", "--limit", "8", "--json", "number") or []
        bots = set()
        for pr in prs[:8]:
            for kind in ("reviews", "comments"):
                path = f"repos/{gh.slug}/{'pulls' if kind == 'reviews' else 'issues'}/{pr['number']}/{kind}"
                for item in gh.api(path) or []:
                    user = item.get("user") or {}
                    if user.get("type") == "Bot" and not re.search(r"vercel|netlify|codecov|dependabot|renovate|"
                                                                  r"changeset|github-actions", user.get("login", ""), re.I):
                        bots.add(user.get("login"))
        if bots:
            return "pass", f"Bot reviewers active on recent PRs: {short(sorted(bots))}"
        if prs:
            return "fail", f"No review bots on the last {len(prs)} merged PRs and none configured"
    return "review", "No review bot config found; check PR history for AI/bot reviewers"


@check("release_automation")
def _(repo, apps):
    hits = repo.find([".releaserc*", "release.config.*", "release-please-config.json", ".release-please-manifest.json",
                      ".changeset/", ".goreleaser.y*ml", "vercel.json", "netlify.toml", "fly.toml", "render.yaml",
                      "railway.json", "railway.toml", "app.yaml", "wrangler.toml", "wrangler.json*", "amplify.yml",
                      ".github/workflows/*deploy*", ".github/workflows/*release*", ".github/workflows/*publish*",
                      "cloudbuild.yaml", "skaffold.yaml"], "")
    hits += repo.grep([r"(npm|pnpm|yarn) publish|twine upload|uv publish|cargo publish|gh release create|"
                       r"docker/build-push-action|deploy|semantic-release|release-please|changesets/action"],
                      repo.ci_files)
    if hits:
        return "pass", f"Release/deploy automation: {short(hits, 3)}"
    return "review", "No CD workflow or release tool found; check for platform git integrations (Vercel, Netlify, etc.)"


@check("monorepo_tooling")
def _(repo, apps):
    if len(apps) < 2:
        return "skip", "Single-application repository"
    hits = repo.find(["turbo.json", "nx.json", "pnpm-workspace.yaml", "lerna.json", "WORKSPACE", "WORKSPACE.bazel",
                      "MODULE.bazel", "pants.toml", "go.work", "rush.json", "moon.yml", ".moon/"], "")
    if (repo.json("package.json") or {}).get("workspaces"):
        hits.append("package.json workspaces")
    if "[workspace]" in (repo.text("Cargo.toml") if repo.exists("Cargo.toml") else ""):
        hits.append("Cargo workspace")
    return by_markers(hits, "Workspace tooling", "fail", f"{len(apps)} apps but no workspace tooling")


@check("unused_dependencies_detection")
def _(repo, app):
    hits = app.dep_hits([r'"knip"', r'"depcheck"', r"\bdeptry\b", r"cargo-udeps", r"cargo-machete", r"\bcreosote\b"])
    hits += cfg(repo, app, [r"\bknip\b|depcheck|deptry|cargo[- ]udeps|cargo[- ]machete|go mod tidy|"
                            r"dependency-analysis|unused-deps|creosote"])
    return by_markers(hits, "Unused dependency detection", "fail", "No unused-dependency check found")


@check("fast_ci_feedback")
def _(repo, apps):
    if not repo.ci_files:
        return "fail", "No CI configuration found"
    gh = repo.gh
    if gh and gh.authed:
        runs = gh.cli_json("run", "list", "--limit", "100", "--json",
                           "event,status,conclusion,createdAt,updatedAt,workflowName") or []
        by_wf = {}
        pr_runs = [r for r in runs if r.get("event") == "pull_request"] or runs
        for r in pr_runs:
            if r.get("status") != "completed" or r.get("conclusion") not in ("success", "failure"):
                continue
            try:
                a = dt.datetime.fromisoformat(r["createdAt"].replace("Z", "+00:00"))
                b = dt.datetime.fromisoformat(r["updatedAt"].replace("Z", "+00:00"))
            except (KeyError, ValueError):
                continue
            by_wf.setdefault(r.get("workflowName", "?"), []).append((b - a).total_seconds() / 60)
        medians = {wf: sorted(d)[len(d) // 2] for wf, d in by_wf.items() if len(d) >= 2}
        if medians:
            wf, slowest = max(medians.items(), key=lambda kv: kv[1])
            status = "pass" if slowest <= 10 else "fail"
            return status, (f"Slowest PR workflow '{wf}' has a median of {slowest:.1f} min over "
                            f"{len(by_wf[wf])} runs (target <= 10 min)")
        return "review", "CI configured but too few recent runs to measure; estimate from workflow contents"
    return "review", f"CI configured ({short(repo.ci_files, 2)}); run durations not available offline"


@check("deployment_frequency")
def _(repo, apps):
    cutoff = dt.datetime.now(dt.timezone.utc).timestamp() - 90 * 86400
    tags = [int(t) for t in repo.git("for-each-ref", "refs/tags", "--format=%(creatordate:unix)").split() if t.isdigit()]
    recent = sum(1 for t in tags if t >= cutoff)
    if recent >= 3:
        return "pass", f"{recent} tags/releases in the last 90 days"
    gh = repo.gh
    if gh and gh.authed:
        runs = gh.cli_json("run", "list", "--limit", "100", "--json", "workflowName,createdAt,conclusion") or []
        deploys = [r for r in runs if re.search(r"deploy|release|publish|cd\b", r.get("workflowName", ""), re.I)
                   and r.get("conclusion") == "success"]
        recent_deploys = [r for r in deploys if dt.datetime.fromisoformat(
            r["createdAt"].replace("Z", "+00:00")).timestamp() >= cutoff]
        if len(recent_deploys) >= 3:
            return "pass", f"{len(recent_deploys)} successful deploy/release workflow runs in the last 90 days"
        deployments = gh.api(f"repos/{gh.slug}/deployments?per_page=50") or []
        recent_dep = [d for d in deployments if dt.datetime.fromisoformat(
            d["created_at"].replace("Z", "+00:00")).timestamp() >= cutoff]
        if len(recent_dep) >= 3:
            return "pass", f"{len(recent_dep)} GitHub deployments in the last 90 days"
    return "review", f"{recent} tags in the last 90 days; check the deploy platform for release cadence"


@check("build_performance_tracking")
def _(repo, apps):
    hits = repo.find(["turbo.json", "nx.json", ".bazelrc", "sccache*"], "")
    hits += repo.grep([r"actions/cache|cache:\s*['\"]?(npm|pnpm|yarn|pip|poetry|gradle|maven)|setup-uv.*cache|"
                       r"enable-cache|Swatinem/rust-cache|remote_cache|--remote-cache|sccache|ccache|"
                       r"buildjet|depot\.dev|gradle-build-action|cache-from"], repo.ci_files + repo.config_files)
    return by_markers(hits, "Build caching/measurement", "fail", "No build caching or build timing found")


@check("release_notes_automation")
def _(repo, apps):
    hits = repo.find([".changeset/", "release-please-config.json", ".releaserc*", "release.config.*", "cliff.toml",
                      ".github/release.yml", ".github/release.yaml", "commitlint.config.*", ".commitlintrc*",
                      ".goreleaser.y*ml", ".versionrc*", "towncrier.toml", "changelog.d/"], "")
    hits += repo.grep([r"generate_release_notes|--generate-notes|release-drafter|conventional-changelog|"
                       r"git-cliff|towncrier|latest-changes|release-notes\.md"], repo.ci_files + repo.config_files)
    return by_markers(hits, "Release notes automated", "fail", "No changelog/release-notes automation found")


@check("feature_flag_infrastructure")
def _(repo, app):
    flags = [r"launchdarkly", r"unleash", r"growthbook", r"flagsmith", r"statsig", r"@openfeature|openfeature",
             r"configcat", r"@splitsoftware|splitio", r'"flags"', r"@vercel/flags", r"flipper", r"\bwaffle\b",
             r"django-waffle", r"posthog"]
    hits = app.dep_hits(flags)
    hits = [h for h in hits if h != "posthog"] or (["posthog (check feature flags usage)"] if hits else [])
    if hits and not hits[0].startswith("posthog"):
        return "pass", f"Feature flag provider: {short(hits)}"
    if app.is_library:
        return "skip", "Library/CLI; feature flags not applicable"
    if hits:
        return "review", "PostHog present; check whether its feature flags are used"
    return "fail", "No feature flag system found"


@check("heavy_dependency_detection")
def _(repo, app):
    if not app.has_bundler:
        return "skip", "No bundler detected; bundle size not applicable"
    hits = app.dep_hits([r'"size-limit"', r'"@size-limit/', r'"bundlesize"', r'"bundlewatch"', r'"@lhci/cli"',
                         r'"@next/bundle-analyzer"', r'"rollup-plugin-visualizer"', r'"webpack-bundle-analyzer"'])
    hits += repo.find([".size-limit*", "lighthouserc*", ".bundlewatch*"], app.path)
    hits += repo.grep([r"size-limit|bundlesize|bundlewatch|lhci|budgets?\.json|compressed-size-action"], repo.ci_files)
    return by_markers(hits, "Bundle size guard", "fail", "Bundled app without a size budget/analyzer")


@check("version_drift_detection")
def _(repo, apps):
    if len(apps) < 2:
        return "skip", "Single-application repository"
    hits = repo.find([".syncpackrc*", "libs.versions.toml"], "")
    hits += repo.grep([r"syncpack|manypkg|catalog:|\[workspace\.dependencies\]|matchUpdateTypes|groupName"],
                      repo.config_files)
    return by_markers(hits, "Version alignment tooling", "fail", "Multiple apps without version drift checks")


@check("progressive_rollout")
def _(repo, apps):
    hits = repo.grep([r"argoproj\.io/v1alpha1.*Rollout|kind:\s*Rollout|flagger|canary|blue.?green|"
                      r"traffic.?split|percentage.?rollout|gradual"], repo.config_files + repo.ci_files)
    if hits:
        return "pass", f"Progressive rollout config: {short(hits, 3)}"
    if not any(a.deployable for a in apps):
        return "skip", "No deployable service detected"
    return "review", "No canary/rollout config found; check the deploy platform (some do this natively)"


@check("rollback_automation")
def _(repo, apps):
    hits = repo.find([".github/workflows/*rollback*"], "")
    hits += repo.grep([r"rollback|roll back|revert.?deploy|autoRollback|abort.*analysis"],
                      repo.ci_files + [f for f in repo.find(["README*", "RUNBOOK*", "runbooks/", "docs/runbooks/", "docs/ops/", "docs/deploy*"] + AGENT_FILES, "")
                       if f.count("/") <= 2])
    if hits:
        return "pass", f"Rollback path documented/automated: {short(hits, 3)}"
    if not any(a.deployable for a in apps):
        return "skip", "No deployable service detected"
    return "review", "No rollback workflow or documentation found; check platform instant-rollback usage"


@check("dead_feature_flag_detection")
def _(repo, apps):
    hits = repo.grep([r"stale.?flag|piranha|flag.?cleanup|unused.?flag"], repo.config_files + repo.ci_files)
    if hits:
        return "pass", f"Stale flag detection: {short(hits, 3)}"
    return "review", "Depends on feature_flag_infrastructure: skip if no flags, otherwise fail unless cleanup exists"


TEST_PATTERNS = ["*.test.*", "*.spec.*", "*_test.go", "test_*.py", "*_test.py", "*Test.java", "*Tests.java",
                 "*Test.kt", "*Tests.cs", "*Test.cs", "*_spec.rb", "*_test.rb", "*Test.php", "*_test.exs",
                 "*_test.dart", "*Tests.swift", "__tests__/", "tests/", "test/", "spec/", "src/test/"]


def test_files(repo, app):
    return [f for f in repo.find(TEST_PATTERNS, app.path) if os.path.splitext(f)[1].lower() in SOURCE_EXT]


@check("unit_tests_exist")
def _(repo, app):
    tests = test_files(repo, app)
    if "Rust" in app.languages:
        tests += repo.source("rust_test", app)
    tests = list(dict.fromkeys(tests))
    if len(tests) >= 3:
        return "pass", f"{len(tests)} test files (e.g. {short(tests, 2)})"
    if tests:
        return "review", f"Only {len(tests)} test file(s): {short(tests)}; check they are meaningful"
    if not app.languages:
        return "skip", "No source code"
    return "fail", "No test files found"


@check("unit_tests_runnable")
def _(repo, app):
    tests = test_files(repo, app) or (repo.source("rust_test", app) if "Rust" in app.languages else [])
    if not tests:
        return "fail", "No tests to run"
    hits = []
    for f in app.manifests + [m for m in repo.manifest_files if "/" not in m]:
        if f.endswith("package.json"):
            t = ((repo.json(f) or {}).get("scripts") or {}).get("test", "")
            if t and "no test specified" not in t:
                hits.append(f"{f} test script")
    for mk in repo.find(["Makefile", "justfile", "Taskfile.yml"], app.path) + \
            [m for m in repo.find(["Makefile", "justfile"], "") if "/" not in m]:
        if re.search(r"^\s*test[\w-]*\s*:", repo.text(mk), re.M):
            hits.append(f"{mk} test target")
    if "Python" in app.languages and (repo.find(["pytest.ini", "tox.ini", "noxfile.py", "conftest.py"], app.path)
                                      or app.has_dep([r"\[tool\.pytest", r"\bpytest\b"])):
        hits.append("pytest")
    for lang, tool in (("Go", "go test"), ("Rust", "cargo test"), ("Dart", "dart test"), ("Elixir", "mix test")):
        if lang in app.languages:
            hits.append(tool)
    if repo.grep([r"(npm|pnpm|yarn|bun) (run )?test|pytest|go test|cargo test|make test|just test|uv run pytest"],
                 [f for f in repo.find(["README*"] + AGENT_FILES, "") if "/" not in f]):
        hits.append("documented in README/agent docs")
    return by_markers(hits, "Test command", "review", "Tests exist but no obvious single test command")


@check("test_naming_conventions")
def _(repo, app):
    tests = test_files(repo, app)
    if not tests:
        return "fail" if app.languages else "skip", "No tests found"
    return "pass", f"Tests follow recognized patterns ({len(tests)} files)"


@check("integration_tests_exist")
def _(repo, app):
    hits = repo.find(["integration/", "integration_tests/", "e2e/", "acceptance/", "tests/integration*",
                      "test/integration*", "*.e2e.*", "*.integration.*", "*_integration_test.*", "playwright.config.*",
                      "cypress.config.*", "cypress.json", "wdio.conf.*", "detox.config.*", "tests/e2e*"], app.path)
    hits += app.dep_hits([r"testcontainers", r'"@playwright/test"', r'"cypress"', r'"supertest"', r"\bhttpx\b.*test"])
    if hits:
        return "pass", f"Integration/E2E tests: {short(hits, 3)}"
    return "review" if test_files(repo, app) else "fail", "No integration/E2E suite found by name; check whether any tests cross component boundaries"


@check("test_isolation")
def _(repo, app):
    hits = app.dep_hits([r"pytest-xdist", r'"vitest"', r'"jest"', r'"@playwright/test"', r"parallel_tests",
                         r'"mocha".*parallel', r"\bnextest\b"])
    for lang, tool in (("Go", "go test (parallel per package)"), ("Rust", "cargo test (multi-threaded)")):
        if lang in app.languages:
            hits.append(tool)
    hits += cfg(repo, app, [r"-race\b|--parallel|-n auto|pytest -n|--workers|maxWorkers|fullyParallel"])
    if hits and test_files(repo, app):
        return "pass", f"Parallel-capable test runner: {short(hits, 3)}"
    if not test_files(repo, app):
        return "fail", "No tests"
    return "review", "Check for shared state/order dependence; no parallel test runner detected"


@check("test_coverage_thresholds")
def _(repo, app):
    hits = repo.find(["codecov.y*ml", ".codecov.y*ml", ".coveragerc", ".nycrc*", ".c8rc*", "coveralls*"], app.path)
    hits += [f for f in ("codecov.yml", ".codecov.yml") if repo.exists(f)]
    hits += cfg(repo, app, [r"coverageThreshold|thresholds?\s*[:=]\s*\{|fail_under|--cov-fail-under|check-coverage|"
                            r"codecov|coveralls|coverage.*(minimum|threshold)|tarpaulin|llvm-cov|go test.*-cover"])
    return by_markers(hits, "Coverage measured/enforced", "fail", "No coverage threshold or reporting found")


@check("flaky_test_detection")
def _(repo, apps):
    hits = repo.find(["trunk.yaml", ".trunk/"], "")
    hits += repo.grep([r"retryTimes|retries\s*:\s*(process\.env\.CI\s*\?\s*)?[1-9]|pytest-rerunfailures|--reruns|"
                       r"flaky|quarantine|buildpulse|datadog-ci|rspec-retry|--stress|test-retry|nextest.*retries"],
                      repo.config_files + repo.ci_files)
    return by_markers(hits, "Flaky test handling", "fail", "No flaky-test retry/detection found")


@check("test_performance_tracking")
def _(repo, apps):
    hits = repo.grep([r"--durations|slowTestThreshold|benchmark|codspeed|criterion|-bench\b|vitest bench|"
                      r"pytest-benchmark|test-reporter|junit|testTimings"], repo.config_files + repo.ci_files)
    return by_markers(hits, "Test timing/benchmarks tracked", "fail", "No test duration or benchmark tracking found")


@check("readme")
def _(repo, apps):
    readmes = [f for f in repo.find(["README*"], "") if "/" not in f]
    if not readmes:
        return "fail", "No README at the repository root"
    txt = repo.text(readmes[0])
    headings = len(re.findall(r"^#{1,3} |^=+$|^-{3,}$", txt, re.M))
    if len(txt) >= 400 and (headings >= 2 or "```" in txt):
        return "pass", f"{readmes[0]} ({len(txt.splitlines())} lines, {headings} headings)"
    return "review", f"{readmes[0]} is short ({len(txt)} chars); check it explains purpose and setup"


@check("agents_md")
def _(repo, apps):
    found = repo.find(AGENT_FILES + [".cursor/rules/", ".github/instructions/"], "")
    if not found:
        return "fail", "No AGENTS.md or harness-specific agent instructions"
    sizes = {f: len(repo.text(f)) for f in found}
    best = max(sizes, key=sizes.get)
    has_agents = any(f.rsplit("/", 1)[-1] == "AGENTS.md" for f in found)
    note = "" if has_agents else " (no cross-harness AGENTS.md; consider adding one)"
    if sizes[best] >= 600:
        return "pass", f"Agent instructions: {short(found, 3)}; largest {best} ({sizes[best]} chars){note}"
    return "review", f"Agent instructions are thin ({best}, {sizes[best]} chars){note}"


@check("documentation_freshness")
def _(repo, apps):
    if not repo.is_git:
        return "review", "Not a git repository; can't measure doc age"
    head = repo.last_commit_ts()
    docs = [f for f in repo.find(["README*", "CONTRIBUTING*"] + AGENT_FILES, "") if "/" not in f or f.startswith(".github/")]
    if not docs or not head:
        return "fail", "No key docs to evaluate"
    stale = []
    for f in docs:
        ts = repo.last_commit_ts(f)
        if ts is None:
            continue
        age = (head - ts) / 86400
        if age > 180:
            stale.append(f"{f} ({int(age)}d behind latest commit)")
    if stale:
        return "fail", f"Stale docs: {short(stale)}"
    return "pass", f"{short(docs)} updated within 180 days of the latest commit"


@check("skills")
def _(repo, apps):
    hits = repo.find([".claude/skills/", ".agents/skills/", ".factory/skills/", ".codex/skills/", ".cursor/skills/",
                      ".github/skills/", ".gemini/skills/", ".opencode/skills/", ".claude/commands/",
                      ".factory/commands/", ".codex/prompts/", ".cursor/commands/", ".github/prompts/",
                      ".gemini/commands/", ".opencode/command/", ".windsurf/workflows/"], "", anchored=True)
    skills = [h for h in hits if h.endswith("SKILL.md")]
    if hits:
        return "pass", (f"{len(skills)} skill(s)" if skills else "Agent commands") + f": {short(hits, 3)}"
    return "fail", "No agent skills or custom commands committed"


@check("api_schema_docs")
def _(repo, app):
    if app.is_library:
        return "skip", "Library; no deployed API surface"
    hits = repo.find(["openapi*.y*ml", "openapi*.json", "swagger*.y*ml", "swagger*.json", "*.graphql", "*.gql",
                      "schema.graphql", "*.proto", "asyncapi*"], app.path)
    hits += app.dep_hits([r"\bfastapi\b", r'"@nestjs/swagger"', r"drf-spectacular", r"drf-yasg", r"springdoc",
                          r'"@asteasolutions/zod-to-openapi"', r'"trpc-openapi"', r"swaggo", r"utoipa", r"aide",
                          r'"@hono/zod-openapi"', r'"fastify-swagger"|"@fastify/swagger"', r"\bapispec\b"])
    if hits:
        return "pass", f"API schema: {short(hits, 3)}"
    if app.is_library or not app.is_server:
        return "skip", "Library or no HTTP API framework detected"
    return "fail", "Exposes an HTTP API but no machine-readable schema found"


@check("service_flow_documented")
def _(repo, apps):
    hits = repo.find(["ARCHITECTURE*", "DESIGN.md", "docs/architecture*", "docs/adr/", "adr/", "docs/decisions/",
                      "*.puml", "*.mmd", "*.drawio", "*.excalidraw", "docs/design*"], "")
    hits += repo.grep([r"```mermaid"], repo.find(["*.md"], "")[:400])
    docs_md = repo.find(["docs/*.md", "docs/**/*.md"], "")
    if hits:
        return "pass", f"Architecture docs: {short(hits, 3)}"
    if len(docs_md) >= 3:
        return "review", f"docs/ has {len(docs_md)} markdown files; check whether any explain architecture/flows"
    return "fail", "No architecture docs, diagrams or ADRs"


@check("automated_doc_generation")
def _(repo, apps):
    hits = repo.find(["typedoc.json", "mkdocs.y*ml", "docs/conf.py", "docusaurus.config.*", ".readthedocs.y*ml",
                      "book.toml", ".vitepress/", "docs/.vitepress/", ".storybook/", "jsdoc.json", "Doxyfile",
                      "mint.json", "docs.json", ".redocly.yaml", "typedoc.config.*"], "")
    hits += repo.grep([r"typedoc|sphinx|mkdocs|cargo doc|godoc|pkgsite|docusaurus|actions/deploy-pages|"
                       r"redoc|openapi-generator|api-extractor|pdoc"], repo.ci_files)
    return by_markers(hits, "Docs generated from source", "fail", "No doc generation tooling found")


@check("agents_md_validation")
def _(repo, apps):
    hits = repo.grep([r"AGENTS\.md|CLAUDE\.md|agent.?instructions|copilot-instructions"], repo.ci_files)
    return by_markers(hits, "CI touches agent instructions", "fail", "Nothing verifies agent instructions stay accurate")


@check("env_template")
def _(repo, app):
    hits = repo.find([".env.example", ".env.sample", ".env.template", ".env.dist", "example.env", ".env.local.example",
                      ".env.development.example", "env.example", ".dev.vars.example"], app.path)
    hits += [f for f in (".env.example", ".env.sample", ".env.template") if repo.exists(f)]
    if hits:
        return "pass", f"Env template: {short(hits)}"
    reads = repo.source("env_read", app, exclude_tests=True)
    if reads and app.is_library:
        return "review", (f"Library reads environment variables ({short(reads, 2)}); pass if they're documented, "
                          "skip if they're optional tuning")
    if reads:
        return "fail", f"Reads environment variables ({short(reads, 2)}) but no .env template"
    return "skip", "No environment variable usage detected"


@check("devcontainer")
def _(repo, apps):
    hits = repo.find([".devcontainer/devcontainer.json", ".devcontainer.json", ".devcontainer/*/devcontainer.json",
                      "flake.nix", "shell.nix", "devbox.json", "devenv.nix", ".gitpod.yml", "Dockerfile.dev",
                      "dev.Dockerfile", ".mise.toml", "mise.toml", ".tool-versions"], "")
    strong = [h for h in hits if not h.endswith((".tool-versions", "mise.toml"))]
    if strong:
        return "pass", f"Reproducible environment: {short(strong, 3)}"
    if hits:
        return "review", f"Toolchain pinned ({short(hits)}) but no full environment definition"
    return "fail", "No devcontainer, Nix, devbox or dev Dockerfile"


@check("local_services_setup")
def _(repo, apps):
    hits = repo.find(["docker-compose*.y*ml", "compose*.y*ml", "Tiltfile", "skaffold.yaml", "supabase/config.toml",
                      "garden.yml", ".devcontainer/docker-compose*.y*ml"], "")
    hits += [d for a in apps for d in a.dep_hits([r"testcontainers"])]
    if hits:
        return "pass", f"Local services: {short(hits, 3)}"
    if not any(a.has_db and not a.is_library for a in apps):
        return "skip", "No backing services detected"
    return "fail", "Uses a database but no one-command local services setup"


@check("database_schema")
def _(repo, app):
    if not app.has_db or app.is_library:
        return "skip", "No database usage detected" if not app.has_db else "Library; no database of its own"
    hits = repo.find(["migrations/", "migrate/", "alembic/", "alembic.ini", "schema.prisma", "drizzle.config.*",
                      "supabase/migrations/", "db/migrate/", "flyway*", "liquibase*", "atlas.hcl", "schema.sql",
                      "knexfile.*", "ent/schema/", "*.sql"], app.path)
    hits += [h for h in repo.find(["supabase/migrations/", "migrations/", "prisma/"], "") if "/" in h][:2]
    return by_markers(hits, "Schema managed as code", "fail", "Database used but no migrations/schema files")


@check("devcontainer_runnable")
def _(repo, apps):
    if not repo.find([".devcontainer/", ".devcontainer.json", "flake.nix", "shell.nix", "devbox.json", "devenv.nix"], ""):
        return "skip", "No environment definition to verify (devcontainer criterion fails)"
    hits = repo.grep([r"devcontainers/ci|devcontainer (build|up)|nix (build|flake check|develop)|devbox run|"
                      r"cachix|DeterminateSystems"], repo.ci_files)
    return by_markers(hits, "Environment exercised in CI", "fail", "Environment definition is never built in CI")


def obs_check(deps, label):
    def fn(repo, app):
        if app.is_library:
            return "skip", "Library/CLI; runtime observability not applicable"
        hits = app.dep_hits(deps)
        if hits:
            return "pass", f"{label}: {short(hits)}"
        return ("fail" if app.is_server else "review"), f"No {label.lower()} found" + \
            ("" if app.is_server else " (frontend/unknown app: decide fail vs skip)")
    return fn


CHECKS["structured_logging"] = obs_check(
    [r'"pino"', r'"winston"', r'"bunyan"', r'"@logtape/', r"\bstructlog\b", r"\bloguru\b", r"python-json-logger",
     r"go\.uber\.org/zap", r"rs/zerolog", r"sirupsen/logrus", r"\btracing-subscriber\b", r"\bslog\b", r"logback",
     r"log4j", r"Serilog", r"\blogstash", r'"@axiomhq/', r'"consola"', r'"evlog"'], "Structured logger")
CHECKS["distributed_tracing"] = obs_check(
    [r"opentelemetry", r'"dd-trace"', r"\bddtrace\b", r'"@vercel/otel"', r"honeycomb", r"jaeger", r"zipkin",
     r"aws-xray", r'"newrelic"', r'"@sentry/(node|nextjs|bun)"', r"sentry-sdk\[.*\]"], "Tracing")
CHECKS["metrics_collection"] = obs_check(
    [r'"prom-client"', r"prometheus[_-]client", r"prometheus/client_golang", r"\bmetrics-exporter",
     r'"hot-shots"', r"\bstatsd\b", r"datadog", r"opentelemetry.*metric", r"micrometer", r"\bprometheus\b",
     r'"@opentelemetry/sdk-metrics"'], "Metrics")
CHECKS["error_tracking_contextualized"] = obs_check(
    [r'"@sentry/', r"sentry-sdk", r"getsentry/sentry-go", r"\bsentry\b", r"bugsnag", r"rollbar", r"honeybadger",
     r'"@datadog/browser-rum"', r"raygun", r"airbrake", r'"@highlight-run/', r"posthog.*exception"], "Error tracking")


@check("health_checks")
def _(repo, app):
    hits = repo.source("health", app, exclude_tests=True)
    hits += repo.grep([r"livenessProbe|readinessProbe|HEALTHCHECK|healthcheck:|health_check|healthCheckPath"],
                      app.config + repo.find(["Dockerfile", "fly.toml", "render.yaml", "*.yaml"], app.path)[:50])
    if hits:
        return "pass", f"Health checks: {short(hits, 3)}"
    if app.is_library or (app.kind() == "web" and not app.is_server):
        return "skip", "Not a long-running service"
    return "fail", "Service without health/readiness endpoints"


@check("alerting_configured")
def _(repo, apps):
    hits = repo.grep([r"^\s*-?\s*alert:\s|alertmanager|datadog_monitor|grafana_rule|pagerduty|opsgenie|"
                      r"sentry.*alert|newrelic_alert|uptime"], repo.config_files, flags=re.I | re.M)
    hits += repo.find(["alerts/", "alerting/", "monitoring/"], "")
    if hits:
        return "pass", f"Alerting config: {short(hits, 3)}"
    if not any(a.deployable for a in apps):
        return "skip", "No deployed service detected"
    return "review", "No alert rules in the repo; alerts may live in the monitoring tool, so check docs for evidence"


@check("deployment_observability")
def _(repo, apps):
    hits = repo.grep([r"sentry-cli releases|getsentry/action-release|sentry.*release|datadog.*deploy|"
                      r"newrelic.*deployment|grafana.*annotation|honeycomb.*marker|DD_VERSION|SENTRY_RELEASE"],
                     repo.ci_files + repo.config_files)
    if hits:
        return "pass", f"Deploy markers: {short(hits, 3)}"
    if not any(a.deployable for a in apps):
        return "skip", "No deployed service detected"
    return "fail", "Deploys are not marked in monitoring"


@check("profiling_instrumentation")
def _(repo, app):
    hits = repo.source("profiling", app)
    hits += repo.grep([r"codspeed|benchmark|pytest-benchmark|cargo bench|go test.*-bench"], repo.ci_files)
    hits += app.dep_hits([r"pyroscope", r'"clinic"', r'"0x"', r"\bscalene\b", r"py-spy", r"\bcriterion\b",
                          r"pytest-benchmark", r'"tinybench"', r"pprof"])
    if hits:
        return "pass", f"Profiling: {short(hits, 3)}"
    return "fail" if app.is_library else "review", "No profiling hooks or benchmarks found"


@check("runbooks_documented")
def _(repo, apps):
    hits = repo.find(["runbooks/", "runbook*", "docs/runbooks/", "docs/ops/", "playbooks/", "docs/oncall*",
                      "INCIDENT*", "docs/incident*", "OPERATIONS.md"], "")
    if hits:
        return "pass", f"Runbooks: {short(hits, 3)}"
    if not any(a.deployable for a in apps):
        return "skip", "No deployed service detected"
    return "fail", "No runbooks or operational docs"


@check("code_quality_metrics")
def _(repo, apps):
    hits = repo.find(["sonar-project.properties", ".codeclimate.yml", ".deepsource.toml", ".codacy.y*ml",
                      "codecov.y*ml", ".codecov.y*ml", "qodana.yaml"], "")
    hits += repo.grep([r"codecov|coveralls|sonar|codeclimate|deepsource|codacy|qodana|smokeshow|"
                       r"coverage-comment|py-cov-action|coverage report"], repo.ci_files)
    return by_markers(hits, "Quality metrics published", "fail", "No code quality metrics tracked")


@check("circuit_breakers")
def _(repo, app):
    hits = app.dep_hits([r'"opossum"', r'"cockatiel"', r"resilience4j", r"\bPolly\b", r"pybreaker", r"circuitbreaker",
                         r"sony/gobreaker", r"hystrix", r"failsafe", r'"brakes"', r"\bpurgatory\b"])
    hits += repo.source("breaker", app)
    if hits:
        return "pass", f"Resilience library/pattern: {short(hits, 3)}"
    if app.is_library:
        return "skip", "Library/CLI"
    return "review", "No circuit breaker found; fail if the app calls external services"


@check("gitignore_comprehensive")
def _(repo, apps):
    if not repo.exists(".gitignore"):
        return "fail", "No .gitignore"
    gi = repo.text(".gitignore")
    langs = {l for a in apps for l in a.languages}
    expect = {".env": r"^\s*\*?\.env", }
    if langs & {"TypeScript", "JavaScript", "Vue", "Svelte"}:
        expect["node_modules"] = r"node_modules"
    if "Python" in langs:
        expect["__pycache__/.venv"] = r"__pycache__|\.venv|\*\.py\[cod\]"
    if "Rust" in langs:
        expect["target/"] = r"target"
    missing = [k for k, rx in expect.items() if not re.search(rx, gi, re.M)]
    tracked = [f for f in repo.files if re.search(r"(^|/)\.env(\.[\w-]+)?$", f) and not re.search(
        r"example|sample|template|dist|defaults?$", f)] + \
        [f for f in repo.files if re.search(r"(^|/)(id_rsa|id_ed25519)$|\.pem$|\.p12$|\.pfx$", f)]
    if repo.is_git:
        tracked_set = set(repo.git("ls-files").splitlines())
        tracked = [f for f in tracked if f in tracked_set]
    if missing or tracked:
        parts = ([f"missing patterns: {', '.join(missing)}"] if missing else []) + \
                ([f"sensitive files tracked: {short(tracked)}"] if tracked else [])
        return "fail", "; ".join(parts)
    return "pass", f".gitignore covers {', '.join(expect)}; no secret files tracked"


@check("branch_protection")
def _(repo, apps):
    gh = repo.gh
    if not (gh and gh.authed and gh.default_branch):
        return "review", "Can't query the hosting platform; check default-branch protection manually"
    b = gh.default_branch
    status, _ = gh.api_status(f"repos/{gh.slug}/branches/{b}/protection")
    if status == 200:
        return "pass", f"Branch protection enabled on {b}"
    rules = gh.api(f"repos/{gh.slug}/rules/branches/{b}")
    if rules:
        return "pass", f"Rulesets apply to {b}: {short(sorted({r.get('type', '?') for r in rules}))}"
    if status == 404:
        return "fail", f"{b} is not protected and no rulesets apply"
    return "review", f"Protection API returned {status} (needs admin); check settings manually"


@check("codeowners")
def _(repo, apps):
    hits = [f for f in ("CODEOWNERS", ".github/CODEOWNERS", "docs/CODEOWNERS", ".gitlab/CODEOWNERS") if repo.exists(f)]
    return by_markers(hits, "CODEOWNERS", "fail", "No CODEOWNERS file")


@check("secret_scanning")
def _(repo, apps):
    hits = repo.find([".gitleaks.toml", ".secrets.baseline", ".trufflehog*", ".secretlintrc*", ".gitguardian.y*ml"], "")
    hits += repo.grep([r"gitleaks|trufflehog|detect-secrets|ggshield|secretlint|talisman"],
                      repo.config_files + repo.ci_files)
    if hits:
        return "pass", f"Secret scanning in repo tooling: {short(hits, 3)}"
    gh = repo.gh
    if gh and gh.info:
        sa = gh.info.get("security_and_analysis") or {}
        ss = (sa.get("secret_scanning") or {}).get("status")
        pp = (sa.get("secret_scanning_push_protection") or {}).get("status")
        if ss == "enabled" or pp == "enabled":
            return "pass", f"GitHub secret scanning {ss or '?'}, push protection {pp or '?'}"
        if ss == "disabled":
            return "fail", "GitHub secret scanning disabled and no scanner in hooks/CI"
    return "review", "No scanner in hooks/CI; platform setting not visible (may need admin)"


@check("dependency_update_automation")
def _(repo, apps):
    hits = repo.find([".github/dependabot.y*ml", "renovate.json", "renovate.json5", ".renovaterc*",
                      ".github/renovate.json*", ".gitlab/renovate.json"], "")
    if '"renovate"' in (repo.text("package.json") if repo.exists("package.json") else ""):
        hits.append("package.json renovate config")
    return by_markers(hits, "Automated dependency updates", "fail", "No Dependabot/Renovate configuration")


@check("secrets_management")
def _(repo, app):
    leaks = repo.source("secret_literal", app, exclude_tests=True)
    if leaks:
        return "fail", f"Possible hardcoded secrets in {short(leaks)}"
    managers = app.dep_hits([r"vault", r"aws-sdk.*secrets|@aws-sdk/client-secrets-manager|secretsmanager",
                             r"@google-cloud/secret-manager|google-cloud-secret-manager", r"azure.*keyvault",
                             r"doppler", r"@1password", r"\bsops\b", r"infisical"])
    if managers:
        return "pass", f"Secret manager: {short(managers)}; no hardcoded secrets found"
    if repo.source("env_read", app, exclude_tests=True):
        return "pass", "Secrets read from environment; no hardcoded secrets found"
    return "skip" if app.is_library else "review", "No secret usage detected"


@check("log_scrubbing")
def _(repo, app):
    hits = repo.source("redact", app, exclude_tests=True)
    if hits:
        return "pass", f"Redaction/scrubbing: {short(hits, 3)}"
    if app.is_library:
        return "skip", "Library/CLI"
    return "review", "No log redaction found; fail if the app logs user data"


@check("pii_handling")
def _(repo, app):
    hits = repo.source("pii", app, exclude_tests=True)
    hits += repo.find(["PRIVACY*", "docs/privacy*", "docs/data*"], "")
    if hits:
        return "review", f"PII-related code/docs found ({short(hits, 3)}); judge whether handling is explicit"
    return "review", "Decide whether this app handles personal data; skip if not"


@check("automated_security_review")
def _(repo, apps):
    hits = repo.grep([r"codeql|semgrep|snyk|bandit|gosec|brakeman|npm audit|pnpm audit|yarn audit|pip-audit|"
                      r"cargo audit|cargo-deny|govulncheck|osv-scanner|trivy|grype|sonar"], repo.ci_files)
    hits += repo.find([".semgrep.y*ml", ".snyk", "deny.toml"], "")
    if hits:
        return "pass", f"Static security scanning: {short(hits, 3)}"
    gh = repo.gh
    if gh and gh.authed:
        ds = gh.api(f"repos/{gh.slug}/code-scanning/default-setup")
        if ds and ds.get("state") == "configured":
            return "pass", "GitHub code scanning default setup is configured"
    return "fail", "No SAST or dependency audit in CI"


@check("dast_scanning")
def _(repo, app):
    hits = repo.grep([r"zaproxy|owasp.?zap|nuclei|stackhawk|burp|dastardly"], repo.ci_files)
    if hits:
        return "pass", f"DAST: {short(hits, 3)}"
    if app.is_library or not (app.is_server or app.is_frontend):
        return "skip", "Not a deployed web application"
    return "fail", "Web app without dynamic security scanning"


@check("privacy_compliance")
def _(repo, apps):
    hits = repo.find(["PRIVACY*", "docs/privacy*", "*cookie-consent*", "*consent*"], "")
    hits += [d for a in apps for d in a.dep_hits([r"cookieconsent|cookie-consent|@osano|onetrust|klaro|cookiebot"])]
    if hits:
        return "review", f"Privacy artifacts found ({short(hits, 3)}); judge whether export/deletion/consent are handled"
    if not any((a.is_frontend or a.is_server) and not a.is_library for a in apps):
        return "skip", "No user-facing app detected"
    return "review", "Decide whether the product collects personal data; skip if not, else fail without controls"


@check("issue_templates")
def _(repo, apps):
    hits = repo.find([".github/ISSUE_TEMPLATE/", ".github/ISSUE_TEMPLATE.md", "ISSUE_TEMPLATE.md",
                      ".gitlab/issue_templates/"], "")
    return by_markers(hits, "Issue templates", "fail", "No issue templates")


@check("pr_templates")
def _(repo, apps):
    hits = repo.find(["pull_request_template.md", ".github/PULL_REQUEST_TEMPLATE/", ".gitlab/merge_request_templates/"], "")
    return by_markers(hits, "PR template", "fail", "No pull request template")


GITHUB_DEFAULT_LABELS = {"bug", "documentation", "duplicate", "enhancement", "good first issue", "help wanted",
                         "invalid", "question", "wontfix", "dependencies", "javascript", "python", "github_actions"}


@check("issue_labeling_system")
def _(repo, apps):
    hits = repo.find([".github/labels.y*ml", ".github/labels.json", ".github/labeler.y*ml", "labels.y*ml"], "")
    if hits:
        return "pass", f"Labels as code: {short(hits)}"
    gh = repo.gh
    if gh and gh.authed:
        labels = gh.cli_json("label", "list", "--limit", "200", "--json", "name")
        if labels is not None:
            custom = [l["name"] for l in labels if l["name"].lower() not in GITHUB_DEFAULT_LABELS]
            if len(custom) >= 4:
                return "pass", f"{len(custom)} custom labels (e.g. {short(custom, 5)})"
            return "fail", f"Only GitHub default labels" + (f" plus {short(custom)}" if custom else "")
    return "review", "Can't list labels offline; check the tracker's label taxonomy"


@check("backlog_health")
def _(repo, apps):
    gh = repo.gh
    if not (gh and gh.authed):
        return "review", "Can't read the issue tracker; check open issues manually"
    if gh.info and not gh.info.get("has_issues", True):
        return "skip", "Issues are disabled on this repository"
    issues = gh.cli_json("issue", "list", "--state", "open", "--limit", "60", "--json", "title,body,labels,updatedAt")
    if issues is None:
        return "review", "Issue list unavailable"
    if not issues:
        closed = gh.cli_json("issue", "list", "--state", "closed", "--limit", "5", "--json", "number") or []
        return ("pass", "No open issues; tracker in use and clear") if closed else \
            ("skip", "Issue tracker not used (tracking likely lives elsewhere)")
    n = len(issues)
    if n < 5:
        return "review", f"Only {n} open issue(s); judge from their quality and whether the tracker is in active use"
    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=365)
    described = sum(1 for i in issues if len((i.get("body") or "").strip()) >= 80)
    labeled = sum(1 for i in issues if i.get("labels"))
    fresh = sum(1 for i in issues if dt.datetime.fromisoformat(i["updatedAt"].replace("Z", "+00:00")) >= cutoff)
    ok = described / n >= 0.7 and labeled / n >= 0.7 and fresh / n >= 0.6
    return ("pass" if ok else "fail"), (f"{n} open issues: {described * 100 // n}% described, "
                                        f"{labeled * 100 // n}% labeled, {fresh * 100 // n}% touched within a year")


@check("product_analytics_instrumentation")
def _(repo, app):
    hits = app.dep_hits([r"posthog", r"amplitude", r"mixpanel", r"@segment/|analytics-node|analytics-next",
                         r'"@vercel/analytics"', r"plausible", r"umami", r"heap", r"fathom", r"rudderstack",
                         r'"@next/third-parties"', r"react-ga4?|vue-gtag", r"pendo", r"june-so|@june-so"])
    hits += repo.source("analytics", app, exclude_tests=True)[:2]
    if hits:
        return "pass", f"Product analytics: {short(hits, 3)}"
    if app.is_library or (not app.is_frontend and app.kind() != "service"):
        return "skip", "Not a user-facing app"
    return "fail", "User-facing app without product analytics"


@check("experimentation_infrastructure")
def _(repo, app):
    hits = app.dep_hits([r"growthbook", r"statsig", r"optimizely", r"launchdarkly", r"\beppo\b", r"@splitsoftware",
                         r"abtasty", r"vwo", r"posthog"])
    if hits and hits != ["posthog"]:
        return "pass", f"Experimentation platform: {short(hits)}"
    if app.is_library or (not app.is_frontend and app.kind() != "service"):
        return "skip", "Not a user-facing app"
    if hits:
        return "review", "PostHog present; check whether experiments are used"
    return "fail", "No experimentation/A-B testing infrastructure"


@check("error_to_insight_pipeline")
def _(repo, apps):
    hits = repo.grep([r"sentry.*(github|issue)|create-issue|issue-from|linear.*sentry|feedback.*issue"],
                     repo.ci_files + repo.config_files)
    if hits:
        return "pass", f"Error/feedback-to-issue automation: {short(hits, 3)}"
    if any(a.dep_hits([r"sentry", r"bugsnag", r"rollbar"]) for a in apps):
        return "review", "Error tracking present; integration with the issue tracker is configured in the tool, not the repo"
    return "fail", "No error tracking feeding the issue tracker"


# --- draft assembly -----------------------------------------------------------
def summarize_apps(per_app, num, den):
    if len(per_app) == 1:
        return next(iter(per_app.values()))["rationale"]
    lead = f"{num}/{den} apps pass" + (f", {len(per_app) - den} skipped" if len(per_app) > den else "")
    # surface the most informative per-app reason: a failure if any, else the first applicable one
    pick = next((r for r in per_app.items() if r[1]["status"] in ("fail", "review")), None) or         next((r for r in per_app.items() if r[1]["status"] != "skip"), next(iter(per_app.items())))
    return f"{lead}. {pick[0]}: {pick[1]['rationale']}"


def aggregate(app_results):
    statuses = [r["status"] for r in app_results.values()]
    applicable = [s for s in statuses if s != "skip"]
    num = sum(1 for s in applicable if s == "pass")
    if not applicable:
        overall = "skip"
    elif "review" in applicable:
        overall = "review"
    else:
        overall = "pass" if num == len(applicable) else "fail"
    return overall, num, len(applicable)


def build_draft(repo, apps, tool, truncated, out_dir):
    previous = None
    prev_path = out_dir / "report.json"
    if prev_path.exists():
        try:
            previous = json.loads(prev_path.read_text(encoding="utf-8"))
        except ValueError:
            previous = None

    criteria = {}
    for c in CRITERIA["criteria"]:
        fn = CHECKS.get(c["id"])
        entry = {}
        if c["scope"] == "app":
            per_app = {}
            for app in apps:
                try:
                    s, why = fn(repo, app) if fn else ("review", "No automated check")
                except Exception as e:  # a broken heuristic must never sink the scan
                    s, why = "review", f"Scanner error: {e.__class__.__name__}: {e}"
                per_app[app.path] = {"status": s, "rationale": why}
            overall, num, den = aggregate(per_app)
            entry = {"status": overall, "numerator": num, "denominator": den,
                     "rationale": summarize_apps(per_app, num, den),
                     "apps": per_app}
        else:
            try:
                s, why = fn(repo, apps) if fn else ("review", "No automated check")
            except Exception as e:
                s, why = "review", f"Scanner error: {e.__class__.__name__}: {e}"
            entry = {"status": s, "numerator": 1 if s == "pass" else 0, "denominator": 0 if s == "skip" else 1,
                     "rationale": why}
        entry["source"] = "scan"
        if previous and c["id"] in (previous.get("criteria") or {}):
            p = previous["criteria"][c["id"]]
            entry["previous"] = {"status": p.get("status"), "rationale": p.get("rationale")}
        criteria[c["id"]] = entry

    head = repo.git("rev-parse", "HEAD").strip() or None
    branch = repo.git("rev-parse", "--abbrev-ref", "HEAD").strip() or None
    dirty = bool(repo.git("status", "--porcelain").strip()) if repo.is_git else None
    unpushed = repo.git("log", "@{u}..", "--oneline").strip() if repo.is_git else ""
    url = repo.gh.remote_url if repo.gh else repo.git("remote", "get-url", "origin").strip()
    langs = Counter()
    for a in apps:
        langs.update(a.languages)
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "draft",
        "repo": {"name": repo.root.name, "url": url or None, "commit": head, "branch": branch,
                 "has_local_changes": dirty, "has_unpushed_commits": bool(unpushed)},
        "generated_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "evaluator": {"harness": None, "model": None, "skill_version": SKILL_VERSION},
        "languages": [l for l, _ in langs.most_common()],
        "monorepo": {"tool": tool, "app_count": len(apps), "truncated": truncated},
        "apps": {a.path: {"description": a.description, "languages": a.languages, "kind": a.kind()} for a in apps},
        "criteria": criteria,
        "action_items": [],
        "previous_report": {"generated_at": previous.get("generated_at"), "commit": (previous.get("repo") or {}).get("commit")}
        if previous else None,
        "scan_notes": [n for n in [
            "Offline scan: platform checks (branch protection, CI timing, labels, issues) left for review." if repo.offline else None,
            "gh CLI not authenticated: platform checks left for review." if (repo.gh and repo.gh.available and not repo.gh.authed) else None,
            "Not a git repository: history-based checks are limited." if not repo.is_git else None,
            f"Source scan capped at {MAX_SOURCE_FILES} files." if getattr(repo, "source_truncated", False) else None,
            "More than 30 apps found; only the first 30 were evaluated." if truncated else None,
        ] if n],
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("repo", nargs="?", default=".", help="repository root (default: .)")
    ap.add_argument("--out", help="output directory (default: <repo>/.agent-readiness)")
    ap.add_argument("--offline", action="store_true", help="skip gh/glab platform checks")
    ap.add_argument("--apps", help="comma-separated app paths to evaluate, overriding discovery. Use . for the "
                                   "root and path=kind to set a kind (service, web, library, cli), e.g. .=library")
    args = ap.parse_args()

    root = Path(args.repo).resolve()
    if not root.is_dir():
        sys.exit(f"Not a directory: {root}")
    out_dir = Path(args.out).resolve() if args.out else root / ".agent-readiness"
    out_dir.mkdir(parents=True, exist_ok=True)

    repo = Repo(root, args.offline)
    repo.scan_sources()
    paths, tool, truncated = discover_apps(repo)
    if args.apps:
        wanted = []
        for item in (x.strip() for x in args.apps.split(",") if x.strip()):
            path, _, kind = item.partition("=")
            if kind and kind not in App.KINDS:
                sys.exit(f"Unknown app kind {kind!r}; use one of {', '.join(App.KINDS)}")
            wanted.append((path.strip().strip("/") or ".", kind or None))
        apps = [App(repo, p, k) for p, k in wanted]
        excluded = [p for p in paths if p not in {w[0] for w in wanted}]
    else:
        apps, excluded = select_apps(repo, paths)
    paths = [a.path for a in apps]
    draft = build_draft(repo, apps, tool, truncated, out_dir)
    draft["monorepo"]["excluded"] = excluded

    draft_path = out_dir / "draft.json"
    draft_path.write_text(json.dumps(draft, indent=2), encoding="utf-8")

    counts = Counter(c["status"] for c in draft["criteria"].values())
    print(f"Scanned {root.name}: {len(repo.files)} files, {len(apps)} app(s) "
          f"[{', '.join(paths[:6])}{', ...' if len(paths) > 6 else ''}], languages: {', '.join(draft['languages']) or 'none'}")
    print(f"Provisional: {counts['pass']} pass, {counts['fail']} fail, {counts['skip']} skip, {counts['review']} need review")
    for n in draft["scan_notes"]:
        print(f"Note: {n}")
    print(f"Draft written to {draft_path}")
    review = [cid for cid, c in draft["criteria"].items() if c["status"] == "review"]
    if review:
        print("Needs review: " + ", ".join(review))


if __name__ == "__main__":
    main()
