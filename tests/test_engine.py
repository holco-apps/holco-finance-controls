import io
import tempfile
import unittest
import zipfile
from pathlib import Path

from holco_finance_controls.engine import Engine
from holco_finance_controls.packs import execute, workbook
from holco_finance_controls import Case, Outcome, control_case
from holco_finance_controls.models import Check


def xlsx(value="100", extra=""):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as z:
        z.writestr("xl/workbook.xml", '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Synthetic" sheetId="1" r:id="r1"/></sheets></workbook>')
        z.writestr("xl/_rels/workbook.xml.rels", '<Relationships><Relationship Id="r1" Target="worksheets/sheet1.xml"/></Relationships>')
        z.writestr("xl/worksheets/sheet1.xml", '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData><row r="1"><c r="A1"><f>50+50</f><v>' + value + '</v></c>' + extra + '</row></sheetData></worksheet>')
    return stream.getvalue()


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "controls.db"
        self.engine = Engine(self.path)

    def tearDown(self):
        self.engine.close()
        self.tmp.cleanup()

    def plan(self, raw=b"id,expected,observed\na,100,100\n"):
        source = self.engine.register(raw)
        return self.engine.plan([source["source_id"]], "reconciliation_csv")

    def start(self, plan):
        return self.engine.start(plan["plan_id"], plan["plan_sha256"])["run_id"]

    def test_resume_preserves_results_and_denominator_across_restart(self):
        rid = self.start(self.plan())
        first = self.engine.advance(rid, 1)
        self.assertEqual(first["counts"]["NOT_RUN"], 1)
        self.assertEqual(first["outcome"], "INCONCLUSIVE")
        self.engine.close()
        self.engine = Engine(self.path)
        end = self.engine.advance(rid, 1)
        self.assertEqual(end["results"][0], first["results"][0])
        self.assertEqual(sum(end["counts"].values()), end["planned"])
        self.assertEqual(end["outcome"], "REVIEW")
        self.assertEqual(end, self.engine.advance(rid))

    def test_wrong_plan_hash_rejected(self):
        plan = self.plan()
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            self.engine.start(plan["plan_id"], "wrong")

    def test_tampered_source_rejected_on_resume(self):
        plan = self.plan()
        rid = self.start(plan)
        self.engine.advance(rid, 1)
        self.engine.db.execute("UPDATE sources SET content=?", (b"changed",))
        with self.assertRaisesRegex(ValueError, "integrity"):
            self.engine.advance(rid)

    def test_invalid_decimal_never_passes(self):
        for val in ("NaN", "Infinity", "", "false"):
            with self.subTest(value=val):
                r = execute("reconciliation_csv", "amounts", [f"id,expected,observed\na,1,{val}\n".encode()], "0.01")
                self.assertEqual(r["status"], "INCONCLUSIVE")

    def test_empty_population_and_duplicate_ids(self):
        for raw in (b"id,expected,observed\n", b"id,expected,observed\na,1,1\na,1,1\n"):
            end = self.engine.advance(self.start(self.plan(raw)), 8)
            self.assertEqual(end["deterministic_outcome"], "INCONCLUSIVE")

    def test_failure_cannot_be_signed_off(self):
        plan = self.plan(b"id,expected,observed\na,100,200\n")
        a, b = self.start(plan), self.start(plan)
        for rid in (a, b):
            self.engine.advance(rid, 8)
        with self.assertRaisesRegex(ValueError, "cannot be signed off"):
            self.engine.sign_off(a, "Synthetic reviewer", b, "Reviewed")

    def test_human_closure_requires_separate_run_and_is_immutable(self):
        plan = self.plan()
        a, b = self.start(plan), self.start(plan)
        for rid in (a, b):
            self.engine.advance(rid, 8)
        with self.assertRaises(ValueError):
            self.engine.sign_off(a, "Reviewer", a, "Reviewed")
        closed = self.engine.sign_off(a, "Reviewer", b, "Compared source and rules manually")
        self.assertEqual(closed["outcome"], "PASS")
        self.assertEqual(closed["state"], "CLOSED")
        with self.assertRaisesRegex(ValueError, "immutable"):
            self.engine.sign_off(a, "Another", b, "Replaced")
        successor = self.plan()
        successor = self.engine.plan([successor["sources"][0]["source_id"]], "reconciliation_csv", supersedes=a)
        self.assertEqual(successor["supersedes"], a)

    def test_unknown_ids_and_paths(self):
        with self.assertRaises(ValueError):
            self.engine.plan(["/etc/passwd"], "reconciliation_csv")

    def test_report_does_not_echo_client_records(self):
        report = self.engine.advance(self.start(self.plan(b"id,expected,observed\nPRIVATE-CUSTOMER,100,101\n")), 8)
        self.assertNotIn("PRIVATE-CUSTOMER", str(report))

    def test_erp_capture_receipt_cannot_be_forged_by_json(self):
        import json
        examples = Path(__file__).resolve().parents[1] / "examples"
        snapshot = json.loads((examples / "erp_snapshot.json").read_text())
        answer = self.engine.register((examples / "agent_claims.json").read_bytes())
        fake = self.engine.register(json.dumps(snapshot).encode())
        real = self.engine.capture_erp_response(b'{"synthetic_provider_data":true}',
            snapshot["records"], snapshot["coverage"], snapshot["tool_calls"])
        policy = {"allowed_tools": ["list_invoices"], "required_tools": ["list_invoices"],
                  "required_period": "2026-09", "required_currency": "EUR", "required_scope": "all_period_records"}
        for source, expected in ((fake, "INCONCLUSIVE"), (real, "PASS")):
            p = self.engine.plan([source["source_id"], answer["source_id"]], "erp_agent_response", policy=policy)
            r = self.engine.advance(self.start(p), 8)
            self.assertEqual(r["deterministic_outcome"], expected)
            self.assertEqual(r["results"][0]["status"], expected)


class PackTests(unittest.TestCase):
    def test_large_decimal_small_discrepancy_is_not_rounded_away(self):
        data = b"id,expected,observed\na,10000000000000000000000000000,10000000000000000000000000001\n"
        self.assertEqual(execute("reconciliation_csv", "amounts", [data], "0.01")["status"], "FAIL")

    def test_excel_engine_difference_and_no_source_mutation(self):
        a, b = xlsx("100"), xlsx("200")
        r = execute("workbook_comparison", "numeric_stability", [a,b], "0.01")
        self.assertEqual(r["status"], "FAIL")
        self.assertEqual(r["observed"]["above_tolerance"], 1)
        self.assertEqual(a, xlsx("100"))

    def test_excel_raw_error_separate_from_bad_date_format(self):
        raw = xlsx("100000000", '<c r="B1" t="e"><v>#REF!</v></c>')
        _, stats = workbook(raw)
        self.assertEqual(stats["stored_errors"], 1)
        self.assertEqual(stats["formulas"], 1)

    def test_excel_missing_cache_cannot_pass(self):
        r = execute("workbook_xlsx", "formula_caches", [xlsx("")], "0.01")
        self.assertEqual(r["status"], "FAIL")

    def test_excel_empty_numeric_comparison_inconclusive(self):
        raw = b"not a workbook"
        self.assertEqual(execute("workbook_xlsx", "population", [raw], "0.01")["status"], "INCONCLUSIVE")

    def test_fec_balanced_and_unbalanced(self):
        head = "JournalCode\tEcritureNum\tEcritureDate\tDebit\tCredit\n"
        a = (head + "AC\t1\t20260911\t100\t0\nAC\t1\t20260911\t0\t100\n").encode()
        self.assertEqual(execute("fec_tsv", "entry_balance", [a], "0.01")["status"], "PASS")
        b = a.replace(b"0\t100", b"0\t90")
        self.assertEqual(execute("fec_tsv", "entry_balance", [b], "0.01")["status"], "FAIL")

    def test_empty_metrics_and_inconclusive_legacy_result(self):
        case = Case("s", 1, 1, 0, (), (), "none", False, False)
        self.assertEqual(control_case(case, []).outcome, Outcome.INCONCLUSIVE)
        class Missing:
            def measure(self, case):
                return Check("missing", Outcome.INCONCLUSIVE, True, "missing", 0)
        self.assertEqual(control_case(case, [Missing()]).outcome, Outcome.INCONCLUSIVE)
