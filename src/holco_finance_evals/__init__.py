"""Source-aware evaluations for financial AI agents."""

from .evaluator import evaluate_case
from .metrics import AccountableDecision, AmountAccuracy, EvidenceCoverage, ToolPolicy
from .models import Case, Evaluation, Outcome
from .suite import ControlPlan, SuiteReport, plan_dataset, run_dataset

__all__ = [
    "AccountableDecision", "AmountAccuracy", "Case", "Evaluation",
    "ControlPlan", "EvidenceCoverage", "Outcome", "SuiteReport", "ToolPolicy",
    "evaluate_case", "plan_dataset", "run_dataset",
]
