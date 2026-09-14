"""Offline, synthetic developer walkthrough with executable acceptance criteria."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import tempfile

from .engine import Engine


def require(condition, message):
    if not condition:
        raise RuntimeError("Demo acceptance failed: " + message)


def walkthrough(output: Path) -> dict:
    """Use a new directory; never overwrite an existing database or report."""
    output.mkdir(parents=True, mode=0o700, exist_ok=False)
    database = output / "controls.sqlite"
    wrong = b"id,expected,observed\nsynthetic-acquisitions,12400.00,12900.00\n"
    corrected = b"id,expected,observed\nsynthetic-acquisitions,12400.00,12400.00\n"
    (output / "source-wrong.csv").write_bytes(wrong)
    (output / "source-corrected.csv").write_bytes(corrected)

    engine = Engine(database)
    try:
        source = engine.register(wrong)
        plan = engine.plan([source["source_id"]], "reconciliation_csv", tolerance="0.01")
        initial = engine.start(plan["plan_id"], plan["plan_sha256"])
        partial = engine.advance(initial["run_id"], max_controls=1)
        require(partial["counts"]["NOT_RUN"] == 1, "unfinished control must be visible")
        require(partial["outcome"] == "INCONCLUSIVE", "partial run must not pass")
    finally:
        engine.close()

    # A new engine connection, as after a process restart; same persisted run.
    engine = Engine(database)
    try:
        failed = engine.advance(initial["run_id"], max_controls=8)
        require(failed["results"][0] == partial["results"][0], "previous result changed on resume")
        require(failed["deterministic_outcome"] == "FAIL", "500 EUR discrepancy must fail")
        source2 = engine.register(corrected)
        plan2 = engine.plan([source2["source_id"]], "reconciliation_csv", tolerance="0.01", supersedes=failed["run_id"])
        replacement = engine.start(plan2["plan_id"], plan2["plan_sha256"])
        reviewed = engine.advance(replacement["run_id"], max_controls=8)
        require(reviewed["deterministic_outcome"] == "PASS", "corrected arithmetic must pass")
        require(reviewed["outcome"] == "REVIEW" and reviewed["review"] is None, "do not invent human approval")
        require(engine.get(failed["run_id"])["report_sha256"] == failed["report_sha256"], "old evidence must remain unchanged")
        require(reviewed["supersedes"] == failed["run_id"], "correction lineage required")
        require(source["sha256"] != source2["sha256"], "changed source must have a new hash")
    finally:
        engine.close()

    artefacts = {"plan-wrong": plan, "report-partial": partial, "report-failed": failed,
                "plan-corrected": plan2, "report-corrected": reviewed}
    for name, value in artefacts.items():
        (output / f"{name}.json").write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    summary = dict(schema="holco.demo/v1", synthetic=True, acceptance="PASS",
                   implementation=plan["implementation"],
                   stages=[dict(name="interrupted", expected="INCONCLUSIVE", actual=partial["outcome"]),
                           dict(name="resumed_wrong_answer", expected="FAIL", actual=failed["outcome"]),
                           dict(name="corrected_arithmetic", expected="PASS", actual=reviewed["deterministic_outcome"]),
                           dict(name="human_decision", expected="REVIEW", actual=reviewed["outcome"])],
                   previous_result_preserved=True, failed_report_preserved=True,
                   correction_linked=True, human_approval_recorded=False,
                   artifacts=[name + ".json" for name in artefacts],
                   limits=["Synthetic CSV: declared expected amounts, not an independent ERP capture",
                           "No LLM, provider, accounting opinion or independent expert review"])
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="New output directory (must not already exist)")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args()
    output = args.output or Path(tempfile.mkdtemp(prefix="holco-demo-")) / "evidence"
    summary = walkthrough(output)
    if args.format == "json":
        print(json.dumps(summary))
    else:
        print("HOLCO Finance Controls — synthetic acceptance walkthrough")
        for stage in summary["stages"]:
            print(f"  {stage['name']}: {stage['actual']} (expected {stage['expected']})")
        print("  Original failure preserved; correction linked; no human approval recorded.")
        print(f"Evidence: {output.resolve()}")
        print("PASS means this demonstration behaved as expected, not financial certification.")


if __name__ == "__main__":
    main()
