import json
import unittest
from pathlib import Path
from holco_finance_controls.engine import Engine


def snapshot(sheet, value, comparisons=None):
    data = dict(workbook="synthetic.xlsx", sheet=sheet, scope="A1:A1", captured_at="2026-01-01T00:00:00Z",
                cells=[dict(address="A1", value=value, formula=None, error=None)])
    if comparisons is not None:
        data["comparisons"] = comparisons
    return data


class ReconciliationTests(unittest.TestCase):
    def setUp(self):
        self.engine = Engine(Path(":memory:"))
        self.addCleanup(self.engine.close)

    def plan(self, left, right):
        ids = [self.engine.register(json.dumps(s).encode())["source_id"] for s in (left, right)]
        return self.engine.plan(ids, "excel_reconciliation", "0.01",
                                policy=dict(objective="monthly tie", required_period="2026", required_scope="both totals"))

    def run_pair(self, left, right):
        plan = self.plan(left, right)
        self.assertEqual(plan["declared_comparisons"], left.get("comparisons", []))
        run = self.engine.start(plan["plan_id"], plan["plan_sha256"])
        return self.engine.advance(run["run_id"], 2)

    def test_exact_cents_and_discrepancy(self):
        pairs = [dict(id="total", left="A1", right="A1")]
        for a, b, expected in [(100.49, 100.49, "PASS"), (100.49, 100.48, "PASS"), (100.49, 100.47, "FAIL"), (100, 102, "FAIL")]:
            with self.subTest(a=a, b=b):
                report = self.run_pair(snapshot("Monthly", a, pairs), snapshot("Cumulative", b))
                self.assertTrue(report["complete"])
                self.assertEqual(report["results"][-1]["status"], expected)
                self.assertNotEqual(report["outcome"], "PASS")  # provenance still REVIEW

    def test_missing_mapping_or_evidence_is_not_pass(self):
        for pairs in ([], [dict(id="missing", left="A1", right="B1")]):
            report = self.run_pair(snapshot("Left", 100, pairs), snapshot("Right", 100))
            self.assertEqual(report["results"][-1]["status"], "INCONCLUSIVE")
        pairs = [dict(id="total", left="A1", right="A1")]
        for value in (None, True, "100"):
            report = self.run_pair(snapshot("Left", value, pairs), snapshot("Right", 100))
            self.assertEqual(report["results"][-1]["status"], "INCONCLUSIVE")
        left = snapshot("Left", 100, pairs)
        del left["cells"][0]["error"]
        self.assertEqual(self.run_pair(left, snapshot("Right", 100))["results"][-1]["status"], "INCONCLUSIVE")

    def test_self_comparison_and_duplicate_ids_refused(self):
        pair = dict(id="total", left="A1", right="A1")
        with self.assertRaises(ValueError):
            self.plan(snapshot("Same", 100, [pair]), snapshot("Same", 100))
        with self.assertRaises(ValueError):
            self.plan(snapshot("Left", 100, [pair, pair]), snapshot("Right", 100))
        with self.assertRaises(ValueError):
            self.plan(snapshot("Left", 100, [dict(**pair, status="PASS")]), snapshot("Right", 100))

    def test_failed_comparison_survives_missing_evidence(self):
        pairs = [dict(id="difference", left="A1", right="A1"), dict(id="missing", left="A2", right="A2")]
        report = self.run_pair(snapshot("Left", 100, pairs), snapshot("Right", 102))
        self.assertEqual(report["outcome"], "FAIL")
        self.assertEqual([c["status"] for c in report["results"][-1]["observed"]["checks"]], ["FAIL", "INCONCLUSIVE"])
