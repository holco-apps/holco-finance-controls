"""Command-line runner for JSON Golden Sets."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from .models import Outcome
from .suite import run_dataset


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("golden_set", type=Path, help="JSON file containing a list of cases")
    parser.add_argument("--format", choices=("jsonl", "summary"), default="jsonl")
    parser.add_argument("--fail-on-review", action="store_true", help="return non-zero when review is required")
    args = parser.parse_args(argv)

    try:
        report = run_dataset(args.golden_set)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        parser.error(str(error))
    if args.format == "summary":
        print(json.dumps(report.summary(), indent=2, sort_keys=True))
    else:
        for result in report.evaluations:
            print(json.dumps(result.as_dict(), sort_keys=True))
        print(json.dumps({"summary": report.summary()}, sort_keys=True))
    failed = any(result.outcome is Outcome.FAIL for result in report.evaluations)
    review_blocked = args.fail_on_review and any(result.outcome is Outcome.REVIEW for result in report.evaluations)
    return 1 if failed or review_blocked else 0
