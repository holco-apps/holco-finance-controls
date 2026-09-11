"""Source-aware evaluations for financial AI agents."""

from .evaluator import evaluate_case
from .metrics import AccountableDecision, AmountAccuracy, EvidenceCoverage, ToolPolicy
from .models import Case, Evaluation, Outcome
from .suite import SuiteReport, run_dataset

__all__ = [
    "AccountableDecision", "AmountAccuracy", "Case", "Evaluation",
    "EvidenceCoverage", "Outcome", "SuiteReport", "ToolPolicy",
    "evaluate_case", "run_dataset",
]
