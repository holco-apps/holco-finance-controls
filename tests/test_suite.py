import json
import tempfile
import unittest
from pathlib import Path

from holco_finance_evals import plan_dataset, run_dataset


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
        self.assertTrue(summary["complete"])

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

    def test_bounded_run_reports_not_run_and_checkpoint(self) -> None:
        case = {
            "expected_amount": 1, "reported_amount": 1, "required_sources": [],
            "cited_sources": [], "rule": "match", "requires_human_approval": False,
            "agent_requested_review": False,
        }
        payload = {"name": "bounded", "cases": [{**case, "case_id": "one"}, {**case, "case_id": "two"}]}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "set.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            report = run_dataset(path, max_cases=1)
        self.assertFalse(report.complete)
        self.assertEqual(report.summary()["outcomes"]["NOT_RUN"], 1)
        self.assertEqual(report.checkpoint()["next_case_index"], 1)

    def test_plan_declares_human_decisions_and_source_hash(self) -> None:
        payload = {"cases": [{
            "case_id": "approval", "expected_amount": 1, "reported_amount": 1,
            "required_sources": [], "cited_sources": [], "rule": "approval",
            "requires_human_approval": True, "agent_requested_review": True,
        }]}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "set.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            plan = plan_dataset(path).as_dict()
        self.assertEqual(plan["human_decisions"], ["approval"])
        self.assertEqual(len(plan["source_sha256"]), 64)
        self.assertTrue(all(not metric["may_override_blocking_failure"] for metric in plan["metrics"]))

    def test_resume_rejects_a_missing_or_wrong_dataset_hash(self) -> None:
        case = {
            "case_id": "one", "expected_amount": 1, "reported_amount": 1,
            "required_sources": [], "cited_sources": [], "rule": "match",
            "requires_human_approval": False, "agent_requested_review": False,
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "set.json"
            path.write_text(json.dumps({"cases": [case]}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "matching dataset"):
                run_dataset(path, start_at=1, expected_source_hash="wrong")
