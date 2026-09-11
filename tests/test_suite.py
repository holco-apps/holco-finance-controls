import json
import tempfile
import unittest
from pathlib import Path

from holco_finance_evals import run_dataset


class SuiteTests(unittest.TestCase):
    def test_versioned_dataset_summary(self) -> None:
        payload = {
            "schema_version": "1.0",
            "name": "tiny",
            "cases": [{
                "case_id": "one", "expected_amount": 10, "reported_amount": 10,
                "required_sources": ["ledger"], "cited_sources": ["ledger"],
                "rule": "match", "requires_human_approval": False,
                "agent_requested_review": False,
            }],
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "set.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            summary = run_dataset(path).summary()
        self.assertEqual(summary["outcomes"]["PASS"], 1)
        self.assertEqual(summary["mean_metric_score"], 1.0)

    def test_duplicate_case_ids_are_rejected(self) -> None:
        case = {
            "case_id": "same", "expected_amount": 1, "reported_amount": 1,
            "required_sources": [], "cited_sources": [], "rule": "match",
            "requires_human_approval": False, "agent_requested_review": False,
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "set.json"
            path.write_text(json.dumps({"cases": [case, case]}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "unique"):
                run_dataset(path)
