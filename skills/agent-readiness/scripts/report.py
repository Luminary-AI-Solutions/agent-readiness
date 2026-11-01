#!/usr/bin/env python3
"""Score a finalized agent-readiness report and render it.

Scoring is deterministic and lives here, not in the model: a level is
unlocked when at least 80% of the previous level's applicable criteria pass
(monorepo criteria count fractionally, e.g. 3/4 apps = 0.75). Skipped
criteria are excluded from every denominator.

Outputs, next to the report by default:
  report.html    self-contained dashboard (no network needed to view)
  summary.md     markdown summary for PRs, issues or chat
  history.jsonl  one line per run, used for the trend chart

    python report.py .agent-readiness/report.json [--out DIR] [--allow-review] [--no-history] [--json]
    python report.py .agent-readiness/draft.json --decisions .agent-readiness/decisions.json

With --decisions, the agent's verdicts are merged into the draft and the
result is saved as report.json before scoring, so the agent only has to
write the entries it changed.
"""
import argparse
import datetime as dt
import json
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
CRITERIA = json.loads((SKILL_DIR / "references" / "criteria.json").read_text(encoding="utf-8"))
TEMPLATE = SKILL_DIR / "assets" / "report-template.html"
STATUSES = {"pass", "fail", "skip", "review"}
DIFFICULTY_ORDER = {"basic": 0, "intermediate": 1, "advanced": 2}


def summarize_apps(apps):
    """Criterion-level rationale built from per-app verdicts (mirrors scan.py)."""
    if len(apps) == 1:
        return next(iter(apps.values())).get("rationale", "")
    applicable = {k: a for k, a in apps.items() if a.get("status") != "skip"}
    passed = sum(1 for a in applicable.values() if a.get("status") == "pass")
    lead = f"{passed}/{len(applicable)} apps pass" + (f", {len(apps) - len(applicable)} skipped"
                                                      if len(apps) > len(applicable) else "")
    pick = next((kv for kv in apps.items() if kv[1].get("status") in ("fail", "review")), None) or \
        next((kv for kv in applicable.items()), next(iter(apps.items())))
    return f"{lead}. {pick[0]}: {pick[1].get('rationale', '')}"


def merge_decisions(draft, decisions):
    """Overlay the agent's verdicts on the scan draft."""
    report = json.loads(json.dumps(draft))
    for key in ("evaluator", "repo"):
        if isinstance(decisions.get(key), dict):
            report.setdefault(key, {}).update({k: v for k, v in decisions[key].items() if v is not None})
    for path, info in (decisions.get("apps") or {}).items():
        if path in report.get("apps", {}) and isinstance(info, dict):
            report["apps"][path].update(info)
    for cid, change in (decisions.get("criteria") or {}).items():
        if cid not in report["criteria"] or not isinstance(change, dict):
            print(f"warning: decision for unknown criterion ignored: {cid}", file=sys.stderr)
            continue
        entry = report["criteria"][cid]
        for path, app_change in (change.get("apps") or {}).items():
            if "apps" in entry and path in entry["apps"]:
                entry["apps"][path].update(app_change)
            else:
                print(f"warning: {cid}: unknown app {path!r} ignored", file=sys.stderr)
        for k in ("status", "rationale"):
            if k in change:
                entry[k] = change[k]
        if change.get("apps") and "rationale" not in change:
            entry["rationale"] = summarize_apps(entry["apps"])
        if "status" in change and "apps" in entry and "apps" not in change:
            # a criterion-level verdict applies to every app unless apps were set individually
            for a in entry["apps"].values():
                if a.get("status") != "skip" or change["status"] == "skip":
                    a["status"] = change["status"]
                    if "rationale" in change:
                        a["rationale"] = change["rationale"]
        entry["source"] = "agent"
    if decisions.get("action_items") is not None:
        report["action_items"] = decisions["action_items"]
    report["status"] = "final"
    return report


def normalize(report, allow_review):
    """Fill numerator/denominator from per-app results and validate statuses."""
    problems = []
    meta = {c["id"]: c for c in CRITERIA["criteria"]}
    crit = report.setdefault("criteria", {})
    for cid in meta:
        if cid not in crit:
            problems.append(f"missing criterion: {cid}")
            crit[cid] = {"status": "review", "rationale": "Not evaluated"}
    for cid, c in crit.items():
        if cid not in meta:
            problems.append(f"unknown criterion id (ignored): {cid}")
            continue
        apps = c.get("apps")
        if isinstance(apps, dict) and apps:
            sts = [a.get("status") for a in apps.values()]
            bad = [s for s in sts if s not in STATUSES]
            if bad:
                problems.append(f"{cid}: invalid app status {bad}")
            applicable = [s for s in sts if s != "skip"]
            c["numerator"] = sum(1 for s in applicable if s == "pass")
            c["denominator"] = len(applicable)
            if not applicable:
                c["status"] = "skip"
            elif "review" in applicable:
                c["status"] = "review"
            else:
                c["status"] = "pass" if c["numerator"] == c["denominator"] else "fail"
        else:
            s = c.get("status")
            if s not in STATUSES:
                problems.append(f"{cid}: invalid status {s!r}")
                c["status"] = s = "review"
            c["numerator"] = 1 if s == "pass" else 0
            c["denominator"] = 0 if s == "skip" else 1
    unresolved = [cid for cid, c in crit.items() if c.get("status") == "review" and cid in meta]
    if unresolved and not allow_review:
        problems.append("unresolved 'review' criteria (decide pass/fail/skip, or pass --allow-review "
                        "to score them as failing): " + ", ".join(unresolved))
    return problems, unresolved


def ratio(c):
    if c["status"] == "skip" or not c.get("denominator"):
        return None
    if c["status"] == "review":
        return 0.0
    return c["numerator"] / c["denominator"]


def score(report):
    meta = CRITERIA["criteria"]
    crit = report["criteria"]
    threshold = CRITERIA["threshold"]

    def bucket(items):
        rs = [ratio(crit[c["id"]]) for c in items]
        rs = [r for r in rs if r is not None]
        return {"passed": round(sum(rs), 2), "applicable": len(rs), "total": len(items),
                "rate": (sum(rs) / len(rs)) if rs else 1.0}

    levels = []
    for lv in CRITERIA["levels"]:
        b = bucket([c for c in meta if c["level"] == lv["level"]])
        levels.append({**lv, **b})
    achieved = 1
    for lv in levels[:-1]:
        if lv["rate"] >= threshold:
            achieved = lv["level"] + 1
        else:
            break
    for lv in levels:
        lv["unlocked"] = lv["level"] <= achieved
        lv["achieved"] = lv["level"] <= achieved

    pillars = [{**p, **bucket([c for c in meta if c["pillar"] == p["id"]])} for p in CRITERIA["pillars"]]
    overall = bucket(meta)
    current = levels[achieved - 1]
    gap = 0
    if achieved < 5:
        # criteria that would need to flip from fail to pass to clear the gate
        need = threshold * current["applicable"] - current["passed"]
        gap = max(0, int(-(-round(need, 6) // 1)))
    return {
        "level": achieved,
        "level_name": current["name"],
        "threshold": threshold,
        "levels": levels,
        "pillars": pillars,
        "overall": overall,
        "next": None if achieved == 5 else {"level": achieved + 1, "name": levels[achieved]["name"],
                                            "progress": current["rate"], "criteria_needed": gap},
        "skipped": sum(1 for c in crit.values() if c.get("status") == "skip" and not c.get("waived")),
        "waived": sum(1 for c in crit.values() if c.get("waived")),
        "lanes": lane_counts(crit),
    }


def lane_counts(crit):
    """How the failing criteria split across fix lanes (auto / guided / manual)."""
    out = {l["id"]: 0 for l in CRITERIA.get("lanes", [])}
    for c in CRITERIA["criteria"]:
        if crit.get(c["id"], {}).get("status") in ("fail", "review"):
            out[c.get("lane", "guided")] = out.get(c.get("lane", "guided"), 0) + 1
    return out


def actions(report, sc):
    meta = {c["id"]: c for c in CRITERIA["criteria"]}
    if report.get("action_items"):
        return [dict(a, lane=a.get("lane") or meta.get(a.get("criterion"), {}).get("lane")) for a in report["action_items"]]
    failing = [cid for cid, c in report["criteria"].items()
               if cid in meta and c["status"] in ("fail", "review")]
    failing.sort(key=lambda cid: (0 if meta[cid]["level"] <= sc["level"] else 1,
                                  abs(meta[cid]["level"] - sc["level"]),
                                  DIFFICULTY_ORDER[meta[cid]["difficulty"]]))
    return [{"criterion": cid, "title": meta[cid]["name"], "why": report["criteria"][cid].get("rationale", ""),
             "how": meta[cid]["fix"], "lane": meta[cid].get("lane")} for cid in failing[:3]]


def update_history(path, report, sc):
    entry = {"generated_at": report.get("generated_at"), "commit": (report.get("repo") or {}).get("commit"),
             "rubric": f"{CRITERIA['version']}:{len(CRITERIA['criteria'])}",
             "level": sc["level"], "rate": round(sc["overall"]["rate"], 4),
             "pillars": {p["id"]: round(p["rate"], 4) for p in sc["pillars"]}}
    rows = []
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                rows.append(json.loads(line))
            except ValueError:
                continue
    if rows and rows[-1].get("commit") and rows[-1].get("commit") == entry["commit"] \
            and rows[-1].get("rubric") == entry["rubric"]:
        rows[-1] = entry  # a re-run on the same commit and rubric replaces; a rubric change gets its own point
    else:
        rows.append(entry)
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    return rows


def pct(x):
    return f"{round(x * 100)}%"


def markdown(report, sc, acts, unresolved):
    meta = {c["id"]: c for c in CRITERIA["criteria"]}
    repo = report.get("repo") or {}
    lines = [f"# Agent Readiness: {repo.get('name', 'repository')}", "",
             f"**Level {sc['level']}: {sc['level_name']}** | {pct(sc['overall']['rate'])} of applicable criteria "
             f"passing ({sc['overall']['passed']:g}/{sc['overall']['applicable']}, {sc['skipped']} skipped)"]
    if sc["next"]:
        lines.append(f"Next: Level {sc['next']['level']} ({sc['next']['name']}) needs {pct(sc['threshold'])} of "
                     f"Level {sc['level']}; currently {pct(sc['next']['progress'])}"
                     + (f", about {sc['next']['criteria_needed']} more criteria to pass." if sc['next']['criteria_needed'] else "."))
    if unresolved:
        lines.append(f"\n> Provisional: {len(unresolved)} criteria still marked `review` were scored as failing.")
    lines += ["", "| Level | Name | Passing | Status |", "|---|---|---|---|"]
    for lv in sc["levels"]:
        st = "achieved" if lv["level"] < sc["level"] else "current" if lv["level"] == sc["level"] else "locked"
        lines.append(f"| {lv['level']} | {lv['name']} | {pct(lv['rate'])} ({lv['passed']:g}/{lv['applicable']}) | {st} |")
    lines += ["", "| Pillar | Passing |", "|---|---|"]
    for p in sc["pillars"]:
        lines.append(f"| {p['name']} | {pct(p['rate'])} ({p['passed']:g}/{p['applicable']}) |")
    lane_name = {l["id"]: l["name"] for l in CRITERIA.get("lanes", [])}
    lc = sc.get("lanes") or {}
    if sum(lc.values()):
        lines += ["", "**Fix lanes:** " + " · ".join(f"{lc.get(l['id'], 0)} {l['name'].lower()}"
                                                     for l in CRITERIA.get("lanes", []))
                  + (f" · {sc['waived']} waived by the team" if sc.get("waived") else "")]
    if acts:
        lines += ["", "## Highest-impact next steps", ""]
        for i, a in enumerate(acts, 1):
            tag = f" [{lane_name[a['lane']]}]" if a.get("lane") in lane_name else ""
            lines.append(f"{i}. **{a.get('title')}**{tag} (`{a.get('criterion')}`): {a.get('how') or ''}".rstrip())
            if a.get("why"):
                lines.append(f"   - Now: {a['why']}")
    blocking = [cid for cid, c in report["criteria"].items() if cid in meta and meta[cid]["level"] <= sc["level"]
                and c["status"] in ("fail", "review")]
    if blocking:
        lines += ["", f"## Failing at Level {sc['level']} and below", ""]
        for cid in sorted(blocking, key=lambda x: (meta[x]["level"], meta[x]["pillar"])):
            c = report["criteria"][cid]
            frac = f" {c['numerator']}/{c['denominator']}" if c.get("denominator", 1) > 1 else ""
            lines.append(f"- L{meta[cid]['level']} `{cid}`{frac}: {c.get('rationale', '')}")
    lines += ["", f"_Generated {report.get('generated_at', '')} at {(repo.get('commit') or '')[:10]} "
              f"by the agent-readiness skill. Scoring follows the 5-level, 80%-gated model popularized by "
              f"Factory's Agent Readiness Model._", ""]
    return "\n".join(lines)


def render_html(payload, out):
    tpl = TEMPLATE.read_text(encoding="utf-8")
    data = json.dumps(payload, separators=(",", ":")).replace("<", "\\u003c")
    name = (payload["report"].get("repo") or {}).get("name", "repository")
    html = tpl.replace("__READINESS_DATA__", data).replace("__REPO_NAME__", name.replace("<", "&lt;"))
    out.write_text(html, encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("report", help="path to report.json, or to draft.json when using --decisions")
    ap.add_argument("--decisions", help="agent verdicts to merge into the draft; writes report.json")
    ap.add_argument("--out", help="output directory (default: the report's directory)")
    ap.add_argument("--allow-review", action="store_true", help="score unresolved 'review' items as failing")
    ap.add_argument("--no-history", action="store_true", help="don't append to history.jsonl")
    ap.add_argument("--json", action="store_true", help="print the computed score as JSON instead of markdown")
    args = ap.parse_args()
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # pipes on Windows default to cp1252
        except (AttributeError, ValueError):
            pass

    src = Path(args.report).resolve()
    report = json.loads(src.read_text(encoding="utf-8"))
    out_dir = Path(args.out).resolve() if args.out else src.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    if args.decisions:
        report = merge_decisions(report, json.loads(Path(args.decisions).read_text(encoding="utf-8")))

    problems, unresolved = normalize(report, args.allow_review)
    blocking = [p for p in problems if p.startswith(("unresolved", "missing")) or "invalid" in p]
    for p in problems:
        print(f"warning: {p}", file=sys.stderr)
    if blocking and not args.allow_review:
        sys.exit("Fix the problems above, or rerun with --allow-review for a provisional render.")

    if args.decisions:
        (out_dir / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    sc = score(report)
    acts = actions(report, sc)
    hist_path = out_dir / "history.jsonl"
    history = update_history(hist_path, report, sc) if not args.no_history else \
        [{"generated_at": report.get("generated_at"), "level": sc["level"], "rate": sc["overall"]["rate"]}]

    payload = {"report": report, "meta": CRITERIA, "score": sc, "actions": acts, "history": history,
               "provisional": bool(unresolved),
               "rendered_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()}
    render_html(payload, out_dir / "report.html")
    md = markdown(report, sc, acts, unresolved)
    (out_dir / "summary.md").write_text(md, encoding="utf-8")

    if args.json:
        print(json.dumps({"level": sc["level"], "level_name": sc["level_name"], "overall": sc["overall"],
                          "levels": [{k: lv[k] for k in ("level", "name", "rate", "passed", "applicable")}
                                     for lv in sc["levels"]],
                          "pillars": [{k: p[k] for k in ("id", "name", "rate", "passed", "applicable")}
                                      for p in sc["pillars"]]}, indent=2))
    else:
        print(md)
    print(f"\nDashboard: {out_dir / 'report.html'}\nSummary:   {out_dir / 'summary.md'}", file=sys.stderr)


if __name__ == "__main__":
    main()
