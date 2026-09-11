import copy
import json
import unittest
from pathlib import Path

from holco_finance_controls.packs import execute

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


class ERPTests(unittest.TestCase):
    def setUp(self):
        self.snapshot = json.loads((EXAMPLES / "erp_snapshot.json").read_text())
        self.claims = json.loads((EXAMPLES / "agent_claims.json").read_text())
        self.policy = {"allowed_tools": ["list_invoices"], "required_tools": ["list_invoices"],
                       "required_period": "2026-09", "required_currency": "EUR", "required_scope": "all_period_records"}

    def check(self, code):
        return execute("erp_agent_response", code,
                       [json.dumps(s).encode() for s in (self.snapshot, self.claims)], "0.01", self.policy)["status"]

    def test_correct_answer(self):
        for code in ("extraction_coverage", "claim_sources", "claim_amounts", "tool_policy"):
            self.assertEqual(self.check(code), "PASS")

    def test_wrong_total(self):
        self.claims["claims"][0]["amount"] = "500.00"
        self.assertEqual(self.check("claim_amounts"), "FAIL")

    def test_correct_amount_for_wrong_request_is_rejected(self):
        self.claims["claims"][0]["period"] = "2026-08"
        for record in self.snapshot["records"]:
            record["period"] = "2026-08"
        self.assertEqual(self.check("claim_amounts"), "PASS")
        self.assertEqual(self.check("request_scope"), "FAIL")

    def test_agent_cannot_override_expected_value(self):
        self.claims["claims"][0].update(amount="500.00", expected="500.00", status="PASS")
        self.assertEqual(self.check("claim_amounts"), "FAIL")

    def test_incomplete_pagination(self):
        self.snapshot["coverage"]["next_cursor"] = "next"
        self.assertEqual(self.check("extraction_coverage"), "INCONCLUSIVE")

    def test_truncated_population(self):
        self.snapshot["records"].pop()
        self.assertEqual(self.check("extraction_coverage"), "INCONCLUSIVE")

    def test_duplicate_and_unknown_sources(self):
        for refs in (["invoice-1", "invoice-1"], ["invented"]):
            self.claims["claims"][0]["record_ids"] = refs
            self.assertEqual(self.check("claim_sources"), "FAIL")

    def test_selective_total(self):
        self.claims["claims"][0].update(record_ids=["invoice-1"], amount="100.00")
        self.assertEqual(self.check("claim_amounts"), "FAIL")

    def test_mixed_currency_or_period(self):
        self.snapshot["records"][0]["currency"] = "USD"
        self.assertEqual(self.check("claim_amounts"), "FAIL")

    def test_write_tool_and_missing_trace(self):
        self.snapshot["tool_calls"][0]["operation"] = "write"
        self.assertEqual(self.check("tool_policy"), "FAIL")
        self.snapshot.pop("tool_calls")
        self.assertEqual(self.check("tool_policy"), "INCONCLUSIVE")

    def test_agent_claimed_trace_not_trusted(self):
        self.claims["tool_calls"] = copy.deepcopy(self.snapshot["tool_calls"])
        self.snapshot.pop("tool_calls")
        self.assertEqual(self.check("tool_policy"), "INCONCLUSIVE")
