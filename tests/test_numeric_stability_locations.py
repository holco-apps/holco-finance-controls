"""HOL-177: numeric_stability must say WHERE, not only how many.

Why these tests exist. The control used to report `above_tolerance=521` and no address. A
reviewer cannot act on that, an auditor cannot be shown it, and a golden set cannot be scored
against it: recall could only be computed by comparing a count to a count, never by matching
locations, and precision could not be computed at all.

The determinism test is the load-bearing one. Findings are drawn from a set union, and set
iteration order over tuples of strings varies between Python processes. A capped list built
from an unordered walk would report a different 100 cells on each run from identical inputs.
"""
import io
import json
import subprocess
import sys
import unittest
import zipfile
from pathlib import Path

from holco_finance_controls.packs import EVIDENCE_CAP, cell_order, execute

SHEET_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"


def grid(cells, sheet="Synthetic"):
    """Workbook carrying exactly the given {A1 reference: stored value} cells."""
    rows = {}
    for coord, value in cells.items():
        row = "".join(filter(str.isdigit, coord))
        rows.setdefault(row, []).append(f'<c r="{coord}"><v>{value}</v></c>')
    body = "".join(f'<row r="{r}">' + "".join(cs) + "</row>"
                   for r, cs in sorted(rows.items(), key=lambda kv: int(kv[0])))
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as z:
        z.writestr("xl/workbook.xml",
                   f'<workbook xmlns="{SHEET_NS}" xmlns:r="http://schemas.openxmlformats.org'
                   f'/officeDocument/2006/relationships"><sheets><sheet name="{sheet}" '
                   f'sheetId="1" r:id="r1"/></sheets></workbook>')
        z.writestr("xl/_rels/workbook.xml.rels",
                   '<Relationships><Relationship Id="r1" Target="worksheets/sheet1.xml"/></Relationships>')
        z.writestr("xl/worksheets/sheet1.xml",
                   f'<worksheet xmlns="{SHEET_NS}"><sheetData>{body}</sheetData></worksheet>')
    return stream.getvalue()


def stability(left, right, tolerance="0.00"):
    return execute("workbook_comparison", "numeric_stability", [grid(left), grid(right)], tolerance)


class Locations(unittest.TestCase):
    def test_a_divergence_names_its_cell_and_both_values(self):
        r = stability({"A1": "100", "B1": "200"}, {"A1": "100", "B1": "250"})
        self.assertEqual(r["status"], "FAIL")
        self.assertEqual(r["observed"]["above_tolerance"], 1)
        self.assertEqual(r["observed"]["divergences"],
                         [dict(sheet="Synthetic", cell="B1", left="200", right="250", delta="50")])

    def test_a_stable_workbook_reports_no_location(self):
        r = stability({"A1": "100", "B1": "200"}, {"A1": "100", "B1": "200"})
        self.assertEqual(r["status"], "PASS")
        self.assertEqual(r["observed"]["divergences"], [])
        self.assertEqual(r["observed"]["divergences_omitted"], 0)
        self.assertEqual(r["observed"]["uncomparable_locations"], [])

    def test_tolerance_is_honoured_before_a_cell_is_located(self):
        # A cell inside tolerance is not a finding, so it must not be reported as one.
        r = stability({"A1": "100"}, {"A1": "100.004"}, tolerance="0.01")
        self.assertEqual(r["status"], "PASS")
        self.assertEqual(r["observed"]["divergences"], [])

    def test_uncomparable_cells_are_located_too(self):
        # 810 uncomparable cells is as unactionable as 521 unnamed divergences, and it is what
        # bounds the recall ceiling: a reviewer must be able to audit that boundary.
        r = stability({"A1": "100", "B1": "200"}, {"A1": "100"})
        self.assertEqual(r["observed"]["uncomparable"], 1)
        self.assertEqual(r["observed"]["uncomparable_locations"],
                         [dict(sheet="Synthetic", cell="B1", reason="absent from one workbook")])

    def test_cells_are_walked_in_reading_order_not_string_order(self):
        left = {f"V{n}": "1" for n in range(1, 13)}
        right = {f"V{n}": "2" for n in range(1, 13)}
        cells = [d["cell"] for d in stability(left, right)["observed"]["divergences"]]
        self.assertEqual(cells, [f"V{n}" for n in range(1, 13)])
        self.assertLess(cell_order(("S", "V9")), cell_order(("S", "V10")))

    def test_columns_are_ordered_by_width_then_letters(self):
        self.assertLess(cell_order(("S", "Z1")), cell_order(("S", "AA1")))


class Cap(unittest.TestCase):
    def test_the_cap_reports_what_it_omitted(self):
        # A silent cap reads as "we found 100"; this one has to say how many it dropped.
        total = EVIDENCE_CAP + 37
        left = {f"A{n}": "1" for n in range(1, total + 1)}
        right = {f"A{n}": "2" for n in range(1, total + 1)}
        observed = stability(left, right)["observed"]
        self.assertEqual(observed["above_tolerance"], total)
        self.assertEqual(len(observed["divergences"]), EVIDENCE_CAP)
        self.assertEqual(observed["divergences_omitted"], 37)
        self.assertEqual(observed["evidence_cap"], EVIDENCE_CAP)

    def test_the_cap_never_understates_the_count(self):
        # The count is the ground truth for scoring; capping evidence must not touch it.
        total = EVIDENCE_CAP * 3
        left = {f"A{n}": "1" for n in range(1, total + 1)}
        right = {f"A{n}": "9" for n in range(1, total + 1)}
        observed = stability(left, right)["observed"]
        self.assertEqual(observed["above_tolerance"], total)
        self.assertEqual(observed["divergences_omitted"] + len(observed["divergences"]), total)


class Determinism(unittest.TestCase):
    """The same inputs must yield the same located evidence, in separate processes."""

    PROGRAM = (
        "import json,sys;sys.path.insert(0,{src!r});sys.path.insert(0,{tests!r});"
        "from test_numeric_stability_locations import stability;"
        "left={{'A%d'%n:'1' for n in range(1,400)}};right={{'A%d'%n:'2' for n in range(1,400)}};"
        "print(json.dumps(stability(left,right)['observed']['divergences']))"
    )

    def run_with_seed(self, seed):
        root = Path(__file__).resolve().parent.parent
        code = self.PROGRAM.format(src=str(root / "src"), tests=str(root / "tests"))
        out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                             env={"PYTHONHASHSEED": seed, "PATH": "/usr/bin:/bin"}, timeout=120)
        self.assertEqual(out.returncode, 0, out.stderr)
        return json.loads(out.stdout)

    def test_capped_evidence_is_identical_under_different_hash_seeds(self):
        # 399 divergences for a cap of 100: which 100 are reported is decided by the walk
        # order. Under set-union order this assertion fails; under a sorted walk it holds.
        first, second = self.run_with_seed("1"), self.run_with_seed("2")
        self.assertEqual(len(first), EVIDENCE_CAP)
        self.assertEqual(first, second)



class RequestedCap(unittest.TestCase):
    """A caller auditing every location may raise the cap, within a hard bound."""

    def stability_with(self, count, policy):
        left = {f"A{n}": "1" for n in range(1, count + 1)}
        right = {f"A{n}": "2" for n in range(1, count + 1)}
        return execute("workbook_comparison", "numeric_stability",
                       [grid(left), grid(right)], "0.00", policy)

    def test_a_raised_cap_locates_more(self):
        observed = self.stability_with(250, dict(evidence_cap=250))["observed"]
        self.assertEqual(len(observed["divergences"]), 250)
        self.assertEqual(observed["divergences_omitted"], 0)
        self.assertEqual(observed["evidence_cap"], 250)

    def test_default_stays_at_one_hundred_when_no_policy_asks(self):
        observed = self.stability_with(250, None)["observed"]
        self.assertEqual(len(observed["divergences"]), EVIDENCE_CAP)
        self.assertEqual(observed["divergences_omitted"], 150)

    def test_an_unusable_cap_is_refused_not_clamped(self):
        # Clamping would let a caller compute recall against a truncated set unknowingly.
        for value in (0, -1, 10_001, "100", 1.5, True, None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.stability_with(3, dict(evidence_cap=value))

    def test_a_plan_refuses_the_cap_before_recording_it(self):
        from holco_finance_controls.engine import Engine
        engine = Engine(Path(":memory:"))
        try:
            left, right = grid({"A1": "1"}), grid({"A1": "2"})
            ids = [engine.register(left)["source_id"], engine.register(right)["source_id"]]
            with self.assertRaises(ValueError):
                engine.plan(ids, "workbook_comparison", tolerance="0.00",
                            policy=dict(evidence_cap=99_999))
            # And it does not belong to a pack that cannot use it.
            single = [engine.register(b"id,expected,observed\na,1,1\n")["source_id"]]
            with self.assertRaises(ValueError):
                engine.plan(single, "reconciliation_csv", policy=dict(evidence_cap=200))
            plan = engine.plan(ids, "workbook_comparison", tolerance="0.00",
                               policy=dict(evidence_cap=200))
            self.assertEqual(plan["policy"]["evidence_cap"], 200)
        finally:
            engine.close()

if __name__ == "__main__":
    unittest.main()
