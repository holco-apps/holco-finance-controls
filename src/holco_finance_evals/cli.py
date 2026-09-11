"""Command-line runner for JSON Golden Sets."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from .evaluator import evaluate_case
from .models import Case, Outcome


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("golden_set", type=Path, help="JSON file containing a list of cases")
    args = parser.parse_args(argv)

    raw_cases = json.loads(args.golden_set.read_text(encoding="utf-8"))
    if not isinstance(raw_cases, list):
        parser.error("the Golden Set root must be a JSON list")

    results = [evaluate_case(Case.from_dict(raw_case)) for raw_case in raw_cases]
    for result in results:
        print(json.dumps(result.as_dict(), sort_keys=True))

    return 1 if any(result.outcome is Outcome.FAIL for result in results) else 0
