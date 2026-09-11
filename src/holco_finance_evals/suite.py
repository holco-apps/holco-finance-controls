"""Versioned plans, bounded execution and resumable aggregate reports."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .evaluator import evaluate_case
from .metrics import DEFAULT_METRICS
from .models import Case, Evaluation, Outcome

REPORT_SCHEMA = "holco.finance-eval-run/v1"


@dataclass(frozen=True)
class Dataset:
    name: str
    schema_version: str
    source_hash: str
    cases: tuple[Case, ...]


@dataclass(frozen=True)
class ControlPlan:
    dataset: str
    schema_version: str
    source_hash: str
    case_ids: tuple[str, ...]
    human_decisions: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "report_schema": REPORT_SCHEMA,
            "mode": "plan",
            "dataset": self.dataset,
            "schema_version": self.schema_version,
            "source_sha256": self.source_hash,
            "planned_cases": len(self.case_ids),
            "metrics": [
                {"name": metric.name, "kind": "deterministic", "may_override_blocking_failure": False}
                for metric in DEFAULT_METRICS
            ],
            "human_decisions": list(self.human_decisions),
            "boundary": "Deterministic failures cannot be overridden by a probabilistic evaluator.",
        }


@dataclass(frozen=True)
class SuiteReport:
    dataset: str
    schema_version: str
    source_hash: str
    evaluations: tuple[Evaluation, ...]
    planned_cases: int
    next_case_index: int
    stop_reason: str
    start_case_index: int
    completed_case_ids: tuple[str, ...]

    @property
    def complete(self) -> bool:
        return self.next_case_index >= self.planned_cases

    def checkpoint(self) -> dict[str, Any]:
        return {
            "dataset_sha256": self.source_hash,
            "next_case_index": self.next_case_index,
            "completed_case_ids": list(self.completed_case_ids),
        }

    def summary(self) -> dict[str, Any]:
        counts = {outcome.value: 0 for outcome in Outcome}
        for evaluation in self.evaluations:
            counts[evaluation.outcome.value] += 1
        counts[Outcome.NOT_RUN.value] += self.planned_cases - self.next_case_index
        scores = [check.score for result in self.evaluations for check in result.checks]
        return {
            "report_schema": REPORT_SCHEMA,
            "dataset": self.dataset,
            "schema_version": self.schema_version,
            "source_sha256": self.source_hash,
            "planned_cases": self.planned_cases,
            "executed_cases": len(self.evaluations),
            "prior_cases_from_checkpoint": self.start_case_index,
            "complete": self.complete,
            "stop_reason": self.stop_reason,
            "outcomes": counts,
            "mean_metric_score": round(sum(scores) / len(scores), 4) if scores else None,
            "checkpoint": self.checkpoint(),
        }


def load_dataset(path: Path) -> Dataset:
    raw = path.read_bytes()
    payload = json.loads(raw)
    if isinstance(payload, list):
        name, version, raw_cases = path.stem, "legacy-v0", payload
    elif isinstance(payload, dict) and isinstance(payload.get("cases"), list):
        name, version, raw_cases = str(payload.get("name", path.stem)), str(payload.get("schema_version", "1.0")), payload["cases"]
    else:
        raise ValueError("dataset must be a case list or an object containing a cases list")
    cases = tuple(Case.from_dict(value) for value in raw_cases)
    case_ids = [case.case_id for case in cases]
    if len(case_ids) != len(set(case_ids)):
        raise ValueError("case_id values must be unique")
    return Dataset(name, version, hashlib.sha256(raw).hexdigest(), cases)


def plan_dataset(path: Path) -> ControlPlan:
    dataset = load_dataset(path)
    human_cases = tuple(case.case_id for case in dataset.cases if case.requires_human_approval)
    return ControlPlan(dataset.name, dataset.schema_version, dataset.source_hash, tuple(case.case_id for case in dataset.cases), human_cases)


def run_dataset(path: Path, *, start_at: int = 0, max_cases: int | None = None, expected_source_hash: str | None = None, stop_reason: str | None = None) -> SuiteReport:
    dataset = load_dataset(path)
    if start_at < 0 or start_at > len(dataset.cases):
        raise ValueError("start_at must identify a position inside the dataset")
    if start_at and expected_source_hash != dataset.source_hash:
        raise ValueError("resume requires the matching dataset SHA-256 checkpoint")
    end = len(dataset.cases) if max_cases is None else min(len(dataset.cases), start_at + max(0, max_cases))
    evaluations = tuple(evaluate_case(case) for case in dataset.cases[start_at:end])
    complete = end >= len(dataset.cases)
    reason = "complete" if complete else stop_reason or "case_budget_reached"
    return SuiteReport(dataset.name, dataset.schema_version, dataset.source_hash, evaluations, len(dataset.cases), end, reason, start_at, tuple(case.case_id for case in dataset.cases[:end]))
