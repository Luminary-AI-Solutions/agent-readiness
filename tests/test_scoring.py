"""Scoring and decision-merge tests. Run: python -m unittest discover tests"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "skills" / "agent-readiness" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import report  # noqa: E402

META = report.CRITERIA["criteria"]


def make_report(statuses):
    """statuses: {level: [status, ...]} applied in criteria order within each level."""
    crit = {}
    by_level = {}
    for c in META:
        by_level.setdefault(c["level"], []).append(c["id"])
    for lv, ids in by_level.items():
        wanted = statuses.get(lv, [])
        for i, cid in enumerate(ids):
            crit[cid] = {"status": wanted[i] if i < len(wanted) else "fail", "rationale": "test"}
    return {"repo": {"name": "t"}, "criteria": crit}


def count(level):
    return sum(1 for c in META if c["level"] == level)


class ScoringTest(unittest.TestCase):
    def score(self, statuses):
        r = make_report(statuses)
        problems, _ = report.normalize(r, allow_review=False)
        self.assertEqual([p for p in problems if "unresolved" in p], [])
        return report.score(r)

    def test_everything_failing_is_level_one(self):
        self.assertEqual(self.score({})["level"], 1)

    def test_gate_is_eighty_percent_of_previous_level(self):
        n1 = count(1)
        need = -(-4 * n1 // 5)  # ceil(0.8 * n1)
        self.assertEqual(self.score({1: ["pass"] * need})["level"], 2)
        self.assertEqual(self.score({1: ["pass"] * (need - 1)})["level"], 1)

    def test_gates_apply_in_order(self):
        # Level 3 fully passing doesn't help when Level 2 is below the gate
        s = self.score({1: ["pass"] * count(1), 3: ["pass"] * count(3)})
        self.assertEqual(s["level"], 2)

    def test_skips_leave_the_denominator(self):
        n1 = count(1)
        s = self.score({1: ["pass"] * (n1 - 2) + ["skip", "skip"]})
        self.assertEqual(s["levels"][0]["applicable"], n1 - 2)
        self.assertEqual(s["levels"][0]["rate"], 1.0)

    def test_all_levels_passing_is_level_five(self):
        s = self.score({lv: ["pass"] * count(lv) for lv in range(1, 6)})
        self.assertEqual(s["level"], 5)
        self.assertIsNone(s["next"])

    def test_app_fractions_count_partially(self):
        r = make_report({})
        cid = next(c["id"] for c in META if c["scope"] == "app" and c["level"] == 1)
        r["criteria"][cid] = {"status": "fail", "apps": {
            "a": {"status": "pass"}, "b": {"status": "pass"}, "c": {"status": "fail"}, "d": {"status": "skip"}}}
        report.normalize(r, allow_review=False)
        self.assertEqual((r["criteria"][cid]["numerator"], r["criteria"][cid]["denominator"]), (2, 3))
        self.assertAlmostEqual(report.ratio(r["criteria"][cid]), 2 / 3)

    def test_unresolved_review_blocks_unless_allowed(self):
        r = make_report({1: ["review"]})
        problems, unresolved = report.normalize(r, allow_review=False)
        self.assertTrue(any("unresolved" in p for p in problems))
        self.assertEqual(len(unresolved), 1)


class MergeTest(unittest.TestCase):
    def test_decisions_override_and_propagate_to_apps(self):
        draft = make_report({})
        cid = next(c["id"] for c in META if c["scope"] == "app")
        draft["criteria"][cid] = {"status": "review", "apps": {"web": {"status": "review"}, "lib": {"status": "skip"}}}
        merged = report.merge_decisions(draft, {
            "evaluator": {"harness": "test"},
            "criteria": {cid: {"status": "pass", "rationale": "ok"}, "readme": {"status": "skip"}},
        })
        self.assertEqual(merged["criteria"][cid]["apps"]["web"]["status"], "pass")
        self.assertEqual(merged["criteria"][cid]["apps"]["lib"]["status"], "skip")
        self.assertEqual(merged["criteria"]["readme"]["source"], "agent")
        self.assertEqual(merged["evaluator"]["harness"], "test")
        self.assertEqual(merged["status"], "final")


class RubricTest(unittest.TestCase):
    def test_every_criterion_is_well_formed(self):
        lanes = {l["id"] for l in report.CRITERIA["lanes"]}
        pillars = {p["id"] for p in report.CRITERIA["pillars"]}
        ids = [c["id"] for c in META]
        self.assertEqual(len(ids), len(set(ids)))
        for c in META:
            self.assertIn(c["lane"], lanes, c["id"])
            self.assertIn(c["pillar"], pillars, c["id"])
            self.assertIn(c["level"], range(1, 6), c["id"])
            self.assertIn(c["scope"], ("repo", "app"), c["id"])

    def test_every_criterion_has_a_scanner_check(self):
        import scan
        self.assertEqual(sorted(set(c["id"] for c in META) - set(scan.CHECKS)), [])

    def test_lane_counts_cover_failing_criteria(self):
        r = make_report({1: ["fail"] * count(1)})
        report.normalize(r, allow_review=False)
        lanes = report.lane_counts(r["criteria"])
        failing = sum(1 for c in r["criteria"].values() if c["status"] == "fail")
        self.assertEqual(sum(lanes.values()), failing)


class EndToEndTest(unittest.TestCase):
    def test_waivers_skip_and_are_labelled(self):
        with tempfile.TemporaryDirectory() as out:
            (Path(out) / "preferences.json").write_text(json.dumps(
                {"waivers": {"product_analytics_instrumentation": "internal tool", "readme": "testing"}}), encoding="utf-8")
            subprocess.run([sys.executable, str(SCRIPTS / "scan.py"), str(ROOT), "--out", out, "--offline"],
                           capture_output=True, text=True, check=True)
            draft = json.loads((Path(out) / "draft.json").read_text(encoding="utf-8"))
            readme = draft["criteria"]["readme"]
            self.assertEqual((readme["status"], readme["waived"]), ("skip", True))
            self.assertIn("internal tool", draft["criteria"]["product_analytics_instrumentation"]["rationale"])

    def test_scan_and_render_this_repo(self):
        with tempfile.TemporaryDirectory() as out:
            run = lambda *a: subprocess.run([sys.executable, *a], capture_output=True, text=True, check=True)
            run(str(SCRIPTS / "scan.py"), str(ROOT), "--out", out, "--offline")
            draft = json.loads((Path(out) / "draft.json").read_text(encoding="utf-8"))
            self.assertEqual(set(draft["criteria"]), {c["id"] for c in META})
            run(str(SCRIPTS / "report.py"), str(Path(out) / "draft.json"), "--allow-review", "--no-history")
            html = (Path(out) / "report.html").read_text(encoding="utf-8")
            self.assertNotIn("__READINESS_DATA__", html)
            self.assertIn("Agent Readiness", (Path(out) / "summary.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
