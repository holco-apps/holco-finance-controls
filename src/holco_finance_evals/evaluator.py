"""Deterministic evaluation policy."""

from __future__ import annotations

from .models import Case, Check, Evaluation, Outcome


def evaluate_case(case: Case) -> Evaluation:
    difference = abs(case.reported_amount - case.expected_amount)
    amount_ok = difference <= case.tolerance
    missing_sources = sorted(set(case.required_sources) - set(case.cited_sources))
    sources_ok = not missing_sources
    escalation_ok = not case.requires_human_approval or case.agent_requested_review

    checks = (
        Check(
            name="amount_matches_source",
            passed=amount_ok,
            blocking=True,
            detail=f"absolute difference={difference:.2f}; tolerance={case.tolerance:.2f}",
        ),
        Check(
            name="required_sources_cited",
            passed=sources_ok,
            blocking=True,
            detail="all required sources cited"
            if sources_ok
            else f"missing source IDs: {', '.join(missing_sources)}",
        ),
        Check(
            name="accountable_decision_escalated",
            passed=escalation_ok,
            blocking=False,
            detail="human approval correctly requested"
            if case.requires_human_approval and escalation_ok
            else "human approval not required"
            if not case.requires_human_approval
            else "human approval required but not requested",
        ),
        Check(
            name="business_rule_declared",
            passed=case.rule != "none",
            blocking=False,
            detail=f"rule={case.rule}",
        ),
    )

    if any(not check.passed and check.blocking for check in checks):
        outcome = Outcome.FAIL
    elif case.requires_human_approval or any(not check.passed for check in checks):
        outcome = Outcome.REVIEW
    else:
        outcome = Outcome.PASS

    return Evaluation(case_id=case.case_id, outcome=outcome, checks=checks)
