# Read the demo as a developer

Run the command in [README](README.md). It uses only a local temporary/new folder,
the engine and synthetic CSV bytes. No network or customer system is involved.

1. **Inspect `plan-wrong.json`.** It lists `population` and `amounts`, the tolerance
   `0.01`, source SHA-256, implementation manifest and review requirement. Changing
   the source or plan invalidates its identity.
2. **Inspect `report-partial.json`.** Population has run, amounts has not. Its
   checkpoint says where to continue and `counts.NOT_RUN` is 1. A short run is
   not represented as a complete success.
3. **Inspect `report-failed.json`.** The database connection was closed and
   reopened before continuing. The original population result, including its
   completion timestamp, is unchanged. The €500 difference produces `FAIL`.
4. **Inspect `report-corrected.json`.** This is a different source and plan.
   `supersedes` references the failed run. Technical arithmetic passes; global
   outcome is `REVIEW`, and `review` is null.
5. **Read the original failure again.** Its report hash is unchanged. The demo
   verifies this, so correction cannot erase the evidence of the first result.

`summary.json` records the acceptance checks. IDs, timestamps and report hashes
vary between executions; the expected statuses and invariants do not.

A shortened report has this shape (placeholders are explanatory, not sample IDs):

```json
{
  "state": "REVIEW",
  "complete": true,
  "planned": 2,
  "executed": 2,
  "deterministic_outcome": "PASS",
  "outcome": "REVIEW",
  "review": null,
  "counts": {"PASS": 2, "FAIL": 0, "REVIEW": 0, "INCONCLUSIVE": 0, "NOT_RUN": 0}
}
```

For actual IDs, evidence and plan/build hashes, read the generated files. A complete
machine-readable report, rather than a screenshot or an LLM narrative, is the
interface for your application.

## Try a counterexample

Use `Engine.register`, `plan`, `start` and `advance` from [REFERENCE](REFERENCE.md).
Try an empty CSV, a duplicate ID, a one-cent difference at the tolerance boundary,
a wrong plan hash, or restarting after only one control. The tests show these cases.
A malformed input must not silently pass. A failure must remain a failure after resume.

For independent ERP evidence, the trusted adapter captures the raw response before
an agent sees it. Uploading an agent-written JSON snapshot cannot attest its origin.
See the two-source example and policy in [MCP.md](MCP.md). This CSV walkthrough
intentionally tests orchestration; it does not prove that its declared expected
amount came from a trustworthy ledger.

## What to review next

- Is the chosen pack adequate for the question, currency, period and scope?
- Are source capture and normalization independently verified?
- Can a missing input, partial extraction or unsupported cell escape coverage?
- Are failure, incompleteness and human approval separate in the host interface?
- Can another person reproduce the finding without trusting the generating agent?

No secret infrastructure is needed to discuss these boundaries or contribute a
synthetic regression. Real domain validation is a separate step.
