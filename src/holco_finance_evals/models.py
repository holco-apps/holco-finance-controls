"""Typed domain objects for the benchmark."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class Outcome(StrEnum):
    PASS = "PASS"
    REVIEW = "REVIEW"
    FAIL = "FAIL"


@dataclass(frozen=True)
class Case:
    case_id: str
    expected_amount: float
    reported_amount: float
    tolerance: float
    required_sources: tuple[str, ...]
    cited_sources: tuple[str, ...]
    rule: str
    requires_human_approval: bool
    agent_requested_review: bool

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Case":
        return cls(
            case_id=str(value["case_id"]),
            expected_amount=float(value["expected_amount"]),
            reported_amount=float(value["reported_amount"]),
            tolerance=float(value.get("tolerance", 0)),
            required_sources=tuple(map(str, value.get("required_sources", []))),
            cited_sources=tuple(map(str, value.get("cited_sources", []))),
            rule=str(value.get("rule", "none")),
            requires_human_approval=bool(value.get("requires_human_approval", False)),
            agent_requested_review=bool(value.get("agent_requested_review", False)),
        )


@dataclass(frozen=True)
class Check:
    name: str
    passed: bool
    blocking: bool
    detail: str


@dataclass(frozen=True)
class Evaluation:
    case_id: str
    outcome: Outcome
    checks: tuple[Check, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "outcome": self.outcome.value,
            "checks": [
                {
                    "name": check.name,
                    "passed": check.passed,
                    "blocking": check.blocking,
                    "detail": check.detail,
                }
                for check in self.checks
            ],
        }
