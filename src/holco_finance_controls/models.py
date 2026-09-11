"""Typed domain objects for the control framework."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import math
from typing import Any


class Outcome(StrEnum):
    PASS = "PASS"
    REVIEW = "REVIEW"
    FAIL = "FAIL"
    INCONCLUSIVE = "INCONCLUSIVE"
    NOT_RUN = "NOT_RUN"


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
    expected_tools: tuple[str, ...] = ()
    called_tools: tuple[str, ...] = ()
    forbidden_tools: tuple[str, ...] = ()
    evidence_hashes: tuple[tuple[str, str], ...] = ()

    def __post_init__(self):
        if any(isinstance(v, bool) or not math.isfinite(v) for v in
               (self.expected_amount, self.reported_amount, self.tolerance)) or self.tolerance < 0:
            raise ValueError("amounts must be finite and tolerance nonnegative")

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
            expected_tools=tuple(map(str, value.get("expected_tools", []))),
            called_tools=tuple(map(str, value.get("called_tools", []))),
            forbidden_tools=tuple(map(str, value.get("forbidden_tools", []))),
            evidence_hashes=tuple(sorted((str(key), str(item)) for key, item in value.get("evidence_hashes", {}).items())),
        )


@dataclass(frozen=True)
class Check:
    name: str
    status: Outcome
    blocking: bool
    detail: str
    score: float
    evidence: tuple[dict[str, str], ...] = ()

    @property
    def passed(self) -> bool:
        return self.status is Outcome.PASS


@dataclass(frozen=True)
class ControlResult:
    case_id: str
    outcome: Outcome
    checks: tuple[Check, ...]
    deterministic_outcome: Outcome
    human_review_required: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "outcome": self.outcome.value,
            "checks": [
                {
                    "name": check.name,
                    "passed": check.passed,
                    "status": check.status.value,
                    "blocking": check.blocking,
                    "detail": check.detail,
                    "score": check.score,
                    "evidence": list(check.evidence),
                }
                for check in self.checks
            ],
            "deterministic_outcome": self.deterministic_outcome.value,
            "human_review_required": self.human_review_required,
        }
