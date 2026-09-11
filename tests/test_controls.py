import unittest

from holco_finance_controls import Case, Outcome, control_case


def make_case(**overrides: object) -> Case:
    values = {
        "case_id": "test",
        "expected_amount": 100.0,
        "reported_amount": 100.0,
        "tolerance": 0.01,
        "required_sources": ("ledger:1",),
        "cited_sources": ("ledger:1",),
        "rule": "amount must match",
        "requires_human_approval": False,
        "agent_requested_review": False,
    }
    values.update(overrides)
    return Case(**values)


class ControlTests(unittest.TestCase):
    def test_grounded_answer_passes(self) -> None:
        self.assertEqual(control_case(make_case()).outcome, Outcome.PASS)

    def test_wrong_amount_fails(self) -> None:
        result = control_case(make_case(reported_amount=101.0))
        self.assertEqual(result.outcome, Outcome.FAIL)

    def test_missing_source_fails(self) -> None:
        result = control_case(make_case(cited_sources=()))
        self.assertEqual(result.outcome, Outcome.FAIL)

    def test_accountable_decision_is_reviewed(self) -> None:
        result = control_case(
            make_case(requires_human_approval=True, agent_requested_review=True)
        )
        self.assertEqual(result.outcome, Outcome.REVIEW)

    def test_missing_escalation_is_reviewed(self) -> None:
        result = control_case(
            make_case(requires_human_approval=True, agent_requested_review=False)
        )
        self.assertEqual(result.outcome, Outcome.REVIEW)
        escalation = next(
            check for check in result.checks if check.name == "accountable_decision_escalated"
        )
        self.assertFalse(escalation.passed)

    def test_forbidden_tool_fails(self) -> None:
        result = control_case(make_case(forbidden_tools=("pay",), called_tools=("pay",)))
        self.assertEqual(result.outcome, Outcome.FAIL)
        self.assertEqual(next(check for check in result.checks if check.name == "tool_policy").score, 0.0)

    def test_evidence_is_linked_without_source_content(self) -> None:
        result = control_case(make_case(evidence_hashes=(("ledger:1", "a" * 64),)))
        evidence = result.checks[0].evidence[0]
        self.assertEqual(evidence, {"source_id": "ledger:1", "sha256": "a" * 64})

    def test_approved_human_escalation_remains_review(self) -> None:
        result = control_case(make_case(requires_human_approval=True, agent_requested_review=True))
        self.assertEqual(result.deterministic_outcome, Outcome.PASS)
        self.assertTrue(result.human_review_required)


if __name__ == "__main__":
    unittest.main()
