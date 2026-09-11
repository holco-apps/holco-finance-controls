"""Command-line runner for JSON Golden Sets."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from .models import Outcome
from .suite import plan_dataset, run_dataset


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("golden_set", type=Path, help="JSON file containing a list of cases")
    parser.add_argument("--format", choices=("jsonl", "summary"), default="jsonl")
    parser.add_argument("--fail-on-review", action="store_true", help="return non-zero when review is required")
    parser.add_argument("--plan", action="store_true", help="print the control plan without executing cases")
    parser.add_argument("--max-cases", type=int, help="bound this run and emit a resumable checkpoint")
    parser.add_argument("--resume-from", type=int, default=0, help="resume at a checkpoint case index")
    parser.add_argument("--checkpoint-sha256", help="dataset hash emitted by the checkpoint being resumed")
    args = parser.parse_args(argv)

    try:
        if args.plan:
            print(json.dumps(plan_dataset(args.golden_set).as_dict(), indent=2, sort_keys=True))
            return 0
        report = run_dataset(args.golden_set, start_at=args.resume_from, max_cases=args.max_cases, expected_source_hash=args.checkpoint_sha256)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        parser.error(str(error))
    if args.format == "summary":
        print(json.dumps(report.summary(), indent=2, sort_keys=True))
    else:
        for result in report.results:
            print(json.dumps(result.as_dict(), sort_keys=True))
        print(json.dumps({"summary": report.summary()}, sort_keys=True))
    failed = any(result.outcome in {Outcome.FAIL, Outcome.INCONCLUSIVE, Outcome.NOT_RUN} for result in report.results)
    review_blocked = args.fail_on_review and any(result.outcome is Outcome.REVIEW for result in report.results)
    incomplete = not report.complete
    return 1 if failed or review_blocked or incomplete else 0
