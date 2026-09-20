"""Universal control layer, typed exclusions, reason taxonomy, aggregate drift.

Guards the three audit responses of 2026-09-20: a plan cannot silently weaken
itself, every non-conclusive status says why, and per-line tolerance cannot be
defeated by splitting one drift into many sub-tolerance lines.
"""

import tempfile
import unittest
from pathlib import Path

from holco_finance_controls.engine import Engine
from holco_finance_controls.packs import CATALOG, EXCLUDABLE, REASONS, execute, result

FEC = ("JournalCode\tEcritureNum\tEcritureDate\tDebit\tCredit\n"
       "VT\tE1\t20260115\t100.00\t0.00\n"
       "VT\tE1\t20260115\t0.00\t100.00\n").encode()


class ReasonTaxonomy(unittest.TestCase):
    def test_inconclusive_requires_a_valid_reason_both_directions(self):
        with self.assertRaisesRegex(ValueError, "machine-readable reason"):
            result("c", 0, 0, "INCONCLUSIVE")
        with self.assertRaisesRegex(ValueError, "machine-readable reason"):
            result("c", 0, 0, "INCONCLUSIVE", reason="because")
        item = result("c", 0, 0, "INCONCLUSIVE", reason="missing_evidence")
        self.assertEqual(item["reason"], "missing_evidence")

    def test_conclusive_statuses_refuse_a_reason(self):
        with self.assertRaisesRegex(ValueError, "only INCONCLUSIVE or NOT_RUN"):
            result("c", 0, 0, "PASS", reason="missing_evidence")

    def test_every_pack_failure_path_carries_a_reason(self):
        report = execute("reconciliation_csv", "amounts", [b"not,a,reconciliation\n1,2,3\n"], "0.01")
        self.assertEqual(report["status"], "INCONCLUSIVE")
        self.assertIn(report["reason"], REASONS)


class UniversalLayer(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.engine = Engine(Path(self.tmp.name) / "controls.db")

    def tearDown(self):
        self.engine.close()
        self.tmp.cleanup()

    def fec_plan(self, exclusions=None):
        source = self.engine.register(FEC)
        return self.engine.plan([source["source_id"]], "fec_tsv", control_exclusions=exclusions)

    def test_universal_control_cannot_be_excluded(self):
        for control in ("entry_balance", "dates", "population", "amounts"):
            with self.subTest(control=control), \
                    self.assertRaisesRegex(ValueError, "universal control"):
                self.fec_plan([{"control_id": control, "reason": "trop de bruit", "author": "op"}])

    def test_exclusion_must_be_fully_typed(self):
        for entry in ({"control_id": "duplicates"},
                      {"control_id": "duplicates", "reason": "", "author": "op"},
                      {"control_id": "unknown", "reason": "x", "author": "op"},
                      "duplicates"):
            with self.subTest(entry=entry), self.assertRaises(ValueError):
                self.fec_plan([entry])
        with self.assertRaisesRegex(ValueError, "duplicate exclusion"):
            self.fec_plan([{"control_id": "duplicates", "reason": "a", "author": "op"},
                           {"control_id": "duplicates", "reason": "b", "author": "op"}])

    def test_excluded_control_surfaces_and_blocks_global_pass(self):
        plan = self.fec_plan([{"control_id": "duplicates", "reason": "journal import dédoublonné en amont", "author": "op"}])
        self.assertEqual(plan["control_exclusions"][0]["control_id"], "duplicates")
        self.assertIn("excluded_at", plan["control_exclusions"][0])
        self.assertEqual(plan["controls"], list(CATALOG["fec_tsv"]))
        run = self.engine.start(plan["plan_id"], plan["plan_sha256"])
        report = self.engine.advance(run["run_id"], 8)
        excluded = [r for r in report["results"] if r["control_id"] == "duplicates"]
        self.assertEqual(excluded[0]["status"], "NOT_RUN")
        self.assertEqual(excluded[0]["reason"], "excluded_by_plan")
        self.assertEqual(excluded[0]["observed"]["excluded_by_plan"]["author"], "op")
        self.assertTrue(report["complete"])
        self.assertEqual(report["deterministic_outcome"], "INCONCLUSIVE")
        self.assertIn(dict(control_id="duplicates", reason="excluded_by_plan"),
                      report["not_run_reasons"])

    def test_plan_without_exclusions_is_unchanged(self):
        plan = self.fec_plan()
        run = self.engine.start(plan["plan_id"], plan["plan_sha256"])
        report = self.engine.advance(run["run_id"], 8)
        self.assertEqual(report["deterministic_outcome"], "PASS")
        self.assertEqual(report["not_run_reasons"], [])

    def test_excludable_map_only_names_catalogued_controls(self):
        for pack, controls in EXCLUDABLE.items():
            self.assertLess(set(controls), set(CATALOG[pack]),
                            f"{pack}: excludable set must be a strict subset of the catalogue")


class AggregateDrift(unittest.TestCase):
    def csv(self, rows, header="id,expected,observed"):
        return ("\n".join([header] + rows) + "\n").encode()

    def test_micro_splitting_passes_per_line_but_flags_aggregate(self):
        rows = [f"r{i},100.000,100.009" for i in range(60)]
        source = self.csv(rows)
        self.assertEqual(execute("reconciliation_csv", "amounts", [source], "0.01")["status"], "PASS")
        report = execute("reconciliation_csv", "aggregate_amounts", [source], "0.01")
        self.assertEqual(report["status"], "REVIEW")
        self.assertEqual(report["observed"]["net_signed_drift"], "0.540")

    def test_symmetric_noise_does_not_alert(self):
        rows = [f"r{i},100.000,{'100.009' if i % 2 else '99.991'}" for i in range(60)]
        report = execute("reconciliation_csv", "aggregate_amounts", [self.csv(rows)], "0.01")
        self.assertEqual(report["status"], "PASS")

    def test_group_column_localises_the_drift(self):
        rows = ([f"a{i},100.000,100.009,FOURNISSEUR_X" for i in range(30)] +
                [f"b{i},100.000,99.991,F{i}" for i in range(30)])
        report = execute("reconciliation_csv", "aggregate_amounts",
                         [self.csv(rows, "id,expected,observed,group")], "0.01")
        self.assertEqual(report["status"], "REVIEW")
        self.assertEqual(report["observed"]["groups_above_tolerance"], ["FOURNISSEUR_X"])

    def test_aggregate_is_planned_by_default(self):
        self.assertIn("aggregate_amounts", CATALOG["reconciliation_csv"])


if __name__ == "__main__":
    unittest.main()
