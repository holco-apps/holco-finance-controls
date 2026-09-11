import json
import unittest
from pathlib import Path
from holco_finance_controls.engine import Engine
from holco_finance_controls.excel_snapshot import parse_snapshot


def fixture():
    return dict(workbook="synthetic.xlsx", sheet="Cash", scope="A1:C1", captured_at="2026-01-01T00:00:00Z",
                cells=[dict(address="A1", value=100, formula=None, error=None),
                       dict(address="B1", value=20, formula=None, error=None),
                       dict(address="C1", value=120, formula="=A1+B1", error=None)],
                checks=[dict(id="rollforward", target="C1", terms=[dict(address="A1"), dict(address="B1")])])


class SnapshotTests(unittest.TestCase):
    def run_snapshot(self, data):
        e = Engine(Path(":memory:"))
        try:
            s = e.register(json.dumps(data).encode())
            with self.assertRaises(ValueError):
                e.plan([s["source_id"]], "excel_snapshot")
            p = e.plan([s["source_id"]], "excel_snapshot", policy=dict(objective="cash tie", required_period="2026", required_scope="A1:C1"))
            self.assertEqual(p["declared_equations"], data.get("checks", []))
            with self.assertRaises(ValueError):
                e.start(p["plan_id"], "wrong")
            r = e.start(p["plan_id"], p["plan_sha256"])
            return e.advance(r["run_id"], 4)
        finally:
            e.close()

    def test_rollforward(self):
        r = self.run_snapshot(fixture())
        self.assertTrue(r["complete"])
        self.assertEqual(r["outcome"], "REVIEW")
        self.assertEqual(r["results"][-1]["status"], "PASS")

    def test_discrepancy_and_errors(self):
        d = fixture(); d["cells"][2]["value"] = 121
        self.assertEqual(self.run_snapshot(d)["results"][-1]["status"], "FAIL")
        d["cells"][2].update(formula="=A1+#REF!", error="#REF!")
        r = self.run_snapshot(d)
        self.assertEqual([x["status"] for x in r["results"]], ["REVIEW", "FAIL", "FAIL", "INCONCLUSIVE"])

    def test_missing_observations(self):
        d = fixture(); d["cells"].pop(0)
        self.assertEqual(self.run_snapshot(d)["results"][-1]["status"], "INCONCLUSIVE")
        d = fixture(); del d["cells"][0]["formula"]; del d["cells"][0]["error"]
        r = self.run_snapshot(d)
        self.assertEqual(r["results"][1]["status"], "INCONCLUSIVE")
        self.assertEqual(r["results"][2]["status"], "INCONCLUSIVE")

    def test_literal_not_formula_error(self):
        d = fixture(); d["cells"][0].update(value="#REF!", formula='="#REF!"')
        r = self.run_snapshot(d)
        self.assertEqual(r["results"][1]["status"], "PASS")
        self.assertEqual(r["results"][2]["status"], "PASS")

    def test_invalid_inputs(self):
        d = fixture(); d["cells"].append(d["cells"][0])
        with self.assertRaises(ValueError): parse_snapshot(json.dumps(d).encode())
        d = fixture(); d["checks"][0]["terms"][0]["address"] = "C1"
        with self.assertRaises(ValueError): parse_snapshot(json.dumps(d).encode())
        d = fixture(); d["cells"][0]["value"] = float("nan")
        with self.assertRaises(ValueError): parse_snapshot(json.dumps(d).encode())
