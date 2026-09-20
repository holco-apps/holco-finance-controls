"""Metamorphic invariants for deterministic financial controls.

These tests assert properties that must hold for any input (permutation
invariance, additivity, tolerance monotonicity, single-error detection),
so calculations are verified without a known oracle and without any
language model. Randomness is seeded: every run tests the same cases.
"""

import random
import unittest

from holco_finance_controls import AmountAccuracy, control_case
from holco_finance_controls.models import Case, Outcome
from holco_finance_controls.packs import execute

SEED = 20260920


def cents(value):
    return "{}.{:02d}".format(value // 100, value % 100)


def reconciliation_bytes(rows):
    lines = ["id,expected,observed"]
    lines += ["{},{},{}".format(i, e, o) for i, e, o in rows]
    return ("\n".join(lines) + "\n").encode("utf-8")


def fec_bytes(rows):
    header = "JournalCode\tEcritureNum\tEcritureDate\tDebit\tCredit"
    lines = [header] + ["\t".join(row) for row in rows]
    return ("\n".join(lines) + "\n").encode("utf-8")


def balanced_entries(rng, entries=20, max_lines=4):
    """Synthetic balanced journal: each entry debits N lines and credits one."""
    rows = []
    for entry in range(entries):
        num = "E{:04d}".format(entry)
        date = "2026{:02d}{:02d}".format(rng.randint(1, 12), rng.randint(1, 28))
        debit_lines = [rng.randint(1, 500_000) for _ in range(rng.randint(1, max_lines))]
        for amount in debit_lines:
            rows.append(("VT", num, date, cents(amount), "0.00"))
        rows.append(("VT", num, date, "0.00", cents(sum(debit_lines))))
    return rows


class ReconciliationInvariants(unittest.TestCase):
    def setUp(self):
        self.rng = random.Random(SEED)

    def rows(self, count=50, error_cents=0):
        rows = []
        for i in range(count):
            amount = self.rng.randint(0, 10_000_000)
            rows.append(("row{:03d}".format(i), cents(amount), cents(amount)))
        if error_cents:
            i = self.rng.randrange(count)
            ident, expected, _ = rows[i]
            observed = cents(int(expected.replace(".", "")) + error_cents)
            rows[i] = (ident, expected, observed)
        return rows

    def test_permutation_invariance(self):
        rows = self.rows(error_cents=7)
        shuffled = list(rows)
        self.rng.shuffle(shuffled)
        self.assertNotEqual(rows, shuffled)
        first = execute("reconciliation_csv", "amounts", [reconciliation_bytes(rows)], "0.01")
        second = execute("reconciliation_csv", "amounts", [reconciliation_bytes(shuffled)], "0.01")
        self.assertEqual(first["status"], second["status"])
        self.assertEqual(first["observed"], second["observed"])

    def test_tolerance_monotonicity(self):
        rows = self.rows(error_cents=5)
        source = reconciliation_bytes(rows)
        passed = False
        for tolerance in ("0.00", "0.01", "0.04", "0.05", "1.00"):
            status = execute("reconciliation_csv", "amounts", [source], tolerance)["status"]
            if passed:
                self.assertEqual(status, "PASS", "a pass regressed at a larger tolerance")
            passed = passed or status == "PASS"
        self.assertTrue(passed)

    def test_single_error_detected_and_counted(self):
        clean = self.rows()
        self.assertEqual(
            execute("reconciliation_csv", "amounts", [reconciliation_bytes(clean)], "0.01")["status"],
            "PASS")
        dirty = self.rows(error_cents=2)
        report = execute("reconciliation_csv", "amounts", [reconciliation_bytes(dirty)], "0.01")
        self.assertEqual(report["status"], "FAIL")
        self.assertEqual(report["observed"]["above_tolerance"], 1)


class FecInvariants(unittest.TestCase):
    def setUp(self):
        self.rng = random.Random(SEED)

    def test_balanced_entries_pass(self):
        rows = balanced_entries(self.rng)
        report = execute("fec_tsv", "entry_balance", [fec_bytes(rows)], "0.01")
        self.assertEqual(report["status"], "PASS")

    def test_additivity_splitting_a_line_preserves_balance(self):
        rows = balanced_entries(self.rng)
        for i, row in enumerate(rows):
            amount = int(row[3].replace(".", ""))
            if amount > 1:
                part = self.rng.randint(1, amount - 1)
                split = [row[:3] + (cents(part), "0.00"),
                         row[:3] + (cents(amount - part), "0.00")]
                rows = rows[:i] + split + rows[i + 1:]
                break
        report = execute("fec_tsv", "entry_balance", [fec_bytes(rows)], "0.01")
        self.assertEqual(report["status"], "PASS")

    def test_single_unbalanced_entry_detected(self):
        rows = balanced_entries(self.rng)
        for i, row in enumerate(rows):
            debit = int(row[3].replace(".", ""))
            if debit:
                rows[i] = row[:3] + (cents(debit + 2), "0.00")
                break
        report = execute("fec_tsv", "entry_balance", [fec_bytes(rows)], "0.01")
        self.assertEqual(report["status"], "FAIL")
        self.assertEqual(report["observed"], 1)

    def test_permutation_invariance(self):
        rows = balanced_entries(self.rng)
        shuffled = list(rows)
        self.rng.shuffle(shuffled)
        first = execute("fec_tsv", "entry_balance", [fec_bytes(rows)], "0.01")
        second = execute("fec_tsv", "entry_balance", [fec_bytes(shuffled)], "0.01")
        self.assertEqual(first["status"], second["status"])
        self.assertEqual(first["observed"], second["observed"])

    def test_duplicated_row_is_reported(self):
        rows = balanced_entries(self.rng)
        clean = execute("fec_tsv", "duplicates", [fec_bytes(rows)], "0.01")
        self.assertEqual(clean["status"], "PASS")
        rows.append(rows[0])
        dirty = execute("fec_tsv", "duplicates", [fec_bytes(rows)], "0.01")
        self.assertEqual(dirty["status"], "FAIL")
        self.assertEqual(dirty["observed"], 1)


class ControlCaseInvariants(unittest.TestCase):
    def case(self, reported, tolerance, requested_review=False):
        return Case(
            case_id="metamorphic",
            expected_amount=1000.0,
            reported_amount=reported,
            tolerance=tolerance,
            required_sources=("src-1",),
            cited_sources=("src-1",),
            rule="none",
            requires_human_approval=requested_review,
            agent_requested_review=requested_review,
        )

    def test_amount_tolerance_monotonicity(self):
        rng = random.Random(SEED)
        for _ in range(25):
            reported = 1000.0 + rng.uniform(-5.0, 5.0)
            passed = False
            for tolerance in (0.0, 0.01, 0.5, 1.0, 5.0, 10.0):
                check = AmountAccuracy().measure(self.case(reported, tolerance))
                if passed:
                    self.assertIs(check.status, Outcome.PASS)
                passed = passed or check.status is Outcome.PASS
            self.assertTrue(passed)

    def test_blocking_failure_survives_review_signals(self):
        result = control_case(self.case(1100.0, 0.01, requested_review=True))
        self.assertIs(result.outcome, Outcome.FAIL)
        self.assertIs(result.deterministic_outcome, Outcome.FAIL)


if __name__ == "__main__":
    unittest.main()
