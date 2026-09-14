"""Typed domain objects for the control framework."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from decimal import Decimal, InvalidOperation
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
    expected_amount: Decimal
    reported_amount: Decimal
    tolerance: Decimal
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
        # Keep exact decimal input; float callers retain their displayed decimal value.
        # Prefer decimal strings at boundaries, since an already-rounded float cannot be recovered.
        for field in ("expected_amount", "reported_amount", "tolerance"):
            value = getattr(self, field)
            if isinstance(value, bool) or not isinstance(value, (str, int, float, Decimal)):
                raise ValueError("amounts must be decimal numbers, not booleans")
            try:
                amount = Decimal(str(value))
            except InvalidOperation:
                raise ValueError("invalid decimal amount") from None
            if not amount.is_finite() or amount.copy_abs() > Decimal("1e30") or amount.as_tuple().exponent < -100:
                raise ValueError("amounts must be finite and within supported precision")
            object.__setattr__(self, field, amount)
        if self.tolerance < 0:
            raise ValueError("tolerance must be nonnegative")
        for field in ("requires_human_approval", "agent_requested_review"):
            if type(getattr(self, field)) is not bool:
                raise ValueError("approval flags must be JSON booleans")

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Case":
        return cls(
            case_id=str(value["case_id"]),
            expected_amount=value["expected_amount"],
            reported_amount=value["reported_amount"],
            tolerance=value.get("tolerance", 0),
            required_sources=tuple(map(str, value.get("required_sources", []))),
            cited_sources=tuple(map(str, value.get("cited_sources", []))),
            rule=str(value.get("rule", "none")),
            requires_human_approval=value.get("requires_human_approval", False),
            agent_requested_review=value.get("agent_requested_review", False),
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
