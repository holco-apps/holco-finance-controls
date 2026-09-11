"""Deterministic evaluation policy."""

from __future__ import annotations

from collections.abc import Iterable

from .metrics import DEFAULT_METRICS, Metric
from .models import Case, Evaluation, Outcome


def evaluate_case(case: Case, metrics: Iterable[Metric] = DEFAULT_METRICS) -> Evaluation:
    checks = tuple(metric.measure(case) for metric in metrics)

    if any(not check.passed and check.blocking for check in checks):
        outcome = Outcome.FAIL
    elif case.requires_human_approval or any(not check.passed for check in checks):
        outcome = Outcome.REVIEW
    else:
        outcome = Outcome.PASS

    return Evaluation(case_id=case.case_id, outcome=outcome, checks=checks)
