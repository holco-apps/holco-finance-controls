import json
import unittest
from pathlib import Path
from holco_finance_controls.engine import Engine
from holco_finance_controls.excel_snapshot import parse_snapshot, dependency_findings, scope_addresses


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
            return e.advance(r["run_id"], 5)
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
        self.assertEqual([x["status"] for x in r["results"]], ["REVIEW", "FAIL", "FAIL", "PASS", "INCONCLUSIVE"])

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

    def test_plan_cannot_change_observed_scope(self):
        engine = Engine(Path(":memory:"))
        try:
            source = engine.register(json.dumps(fixture()).encode())
            for scope in ("A1:B1", "A1:Z100"):
                with self.assertRaisesRegex(ValueError, "required scope differs"):
                    engine.plan([source["source_id"]], "excel_snapshot", policy={
                        "objective": "cash tie", "required_period": "2026", "required_scope": scope})
            plan = engine.plan([source["source_id"]], "excel_snapshot", policy={
                "objective": "cash tie", "required_period": "2026", "required_scope": "A1:C1"})
            self.assertEqual(plan["snapshot_scope"]["scope"], "A1:C1")
        finally:
            engine.close()

    def test_scope_rejects_outside_cells_and_oversized_rectangle(self):
        d = fixture(); d['scope'] = 'A1:B1'
        with self.assertRaises(ValueError): parse_snapshot(json.dumps(d).encode())
        with self.assertRaises(ValueError): scope_addresses('A1:ZZZ999999')

    def test_long_dependency_chain_and_cycle(self):
        cells = {f'A{i}': {'formula': f'=A{i+1}'} for i in range(1, 3034)}
        cells['A3034'] = {'formula': None}
        self.assertEqual(dependency_findings(cells)['circular_count'], 0)
        cells['A3034']['formula'] = '=A1'
        self.assertEqual(dependency_findings(cells)['circular_count'], 3034)

    def test_external_and_missing_formula_view_remain_unknown(self):
        findings = dependency_findings({'A1': {'formula': '=Other!A1'}, 'A2': {}})
        self.assertEqual(findings['unsupported_formula_count'], 1)
        self.assertEqual(findings['missing_formula_view'], 1)
        self.assertEqual(findings['circular_count'], 0)

    def test_overlapping_cycles_report_every_member(self):
        cells = {'A1': {'formula': '=B1+C1'}, 'B1': {'formula': '=A1'},
                 'C1': {'formula': '=B1'}}
        self.assertEqual(dependency_findings(cells)['circular_references'], ['A1', 'B1', 'C1'])

    def test_unsupported_expressions_are_unknown(self):
        for formula in ('=SUM(A1:A3)', '=INDIRECT("A1")', '=OFFSET(A1,0,0)', '=NamedRange', '=UnknownFunction()'):
            with self.subTest(formula=formula):
                self.assertEqual(dependency_findings({'A1': {'formula': formula}})['unsupported_formula_count'], 1)
        self.assertEqual(dependency_findings({'A1': {'formula': '=a1'}})['direct_count'], 1)
        self.assertEqual(dependency_findings({'LOG10': {'formula': '=LOG10(100)'}})['direct_count'], 0)

    def test_unobserved_dependency_cannot_prove_no_cycle(self):
        from decimal import Decimal
        from holco_finance_controls.excel_snapshot import snapshot_control
        d = fixture()
        d['scope'] = 'A1:B1'
        d['cells'] = [{'address': 'A1', 'value': 0, 'formula': '=B1', 'error': None}]
        d['checks'] = []
        result = snapshot_control('formula_dependencies', json.dumps(d).encode(), Decimal('0.01'))
        self.assertEqual(result['status'], 'INCONCLUSIVE')
        self.assertEqual(result['reason_code'], 'MISSING_EVIDENCE')
        self.assertEqual(result['observed']['unresolved_reference_addresses'], ['B1'])
