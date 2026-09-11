"""Dataset loading and aggregate reporting."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .evaluator import evaluate_case
from .models import Case, Evaluation, Outcome


@dataclass(frozen=True)
class SuiteReport:
    dataset: str
    schema_version: str
    evaluations: tuple[Evaluation, ...]

    def summary(self) -> dict[str, Any]:
        counts = {outcome.value: 0 for outcome in Outcome}
        for evaluation in self.evaluations:
            counts[evaluation.outcome.value] += 1
        scores = [check.score for result in self.evaluations for check in result.checks]
        return {
            "dataset": self.dataset,
            "schema_version": self.schema_version,
            "cases": len(self.evaluations),
            "outcomes": counts,
            "mean_metric_score": round(sum(scores) / len(scores), 4) if scores else 0.0,
        }


def run_dataset(path: Path) -> SuiteReport:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        name, version, raw_cases = path.stem, "legacy-v0", payload
    elif isinstance(payload, dict) and isinstance(payload.get("cases"), list):
        name = str(payload.get("name", path.stem))
        version = str(payload.get("schema_version", "1.0"))
        raw_cases = payload["cases"]
    else:
        raise ValueError("dataset must be a case list or an object containing a cases list")
    cases = tuple(Case.from_dict(value) for value in raw_cases)
    case_ids = [case.case_id for case in cases]
    if len(case_ids) != len(set(case_ids)):
        raise ValueError("case_id values must be unique")
    return SuiteReport(name, version, tuple(evaluate_case(case) for case in cases))
