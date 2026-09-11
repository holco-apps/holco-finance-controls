"""Deterministic control policy."""

from __future__ import annotations

from collections.abc import Iterable

from .metrics import DEFAULT_METRICS, Metric
from .models import Case, ControlResult, Outcome


def control_case(case: Case, metrics: Iterable[Metric] = DEFAULT_METRICS) -> ControlResult:
    checks = tuple(metric.measure(case) for metric in metrics)

    if not checks:
        outcome = Outcome.INCONCLUSIVE
    elif any(check.status is Outcome.FAIL and check.blocking for check in checks):
        outcome = Outcome.FAIL
    elif any(check.status in {Outcome.INCONCLUSIVE, Outcome.NOT_RUN} for check in checks):
        outcome = Outcome.INCONCLUSIVE
    elif any(check.status in {Outcome.REVIEW, Outcome.FAIL} for check in checks):
        outcome = Outcome.REVIEW
    else:
        outcome = Outcome.PASS

    deterministic = outcome if outcome is not Outcome.REVIEW else Outcome.PASS
    return ControlResult(case_id=case.case_id, outcome=outcome, checks=checks, deterministic_outcome=deterministic, human_review_required=outcome is Outcome.REVIEW)
