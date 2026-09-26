---
name: run-conformance-demo
description: Install the holco-finance-controls engine and run its local conformance demo, then read the generated evidence files (plan, partial report, failed report, corrected report, summary). Use when the user wants to try HOLCO Finance Controls, see how evidence retention works, or check that their installation behaves as specified. Local only, Python 3.11+, no API key, no LLM, no network access needed.
---

# Run the conformance demo and read its evidence

The demo is a self-contained acceptance walkthrough on synthetic data. It shows
the whole protocol: an explicit plan, an interrupted run, a measured failure, a
correction that supersedes without erasing, and a machine-readable summary.

## Run it

```sh
git clone https://github.com/holco-apps/holco-finance-controls.git
cd holco-finance-controls
python3 -m venv .venv && . .venv/bin/activate
python -m pip install -e .
holco-controls-demo --output demo-evidence
```

The demo exits `0` when the expected workflow is verified, including the
intentional failure. Use a new output directory for each run, or omit
`--output` for a fresh temporary directory. On Windows, see the PowerShell
variant in README.md.

## Read the evidence, in this order

1. `plan-wrong.json`: the explicit plan (controls, tolerance 0.01, source
   SHA-256, implementation manifest, review requirement). Changing the source
   or the plan invalidates its identity.
2. `report-partial.json`: one control has run, one has not. The checkpoint says
   where to continue and `counts.NOT_RUN` is 1. A short run is never presented
   as a complete success.
3. `report-failed.json`: the run was interrupted and resumed; the original
   result and its completion timestamp are unchanged. The EUR 500 discrepancy
   between the declared source (12,400) and the agent observation (12,900)
   produces `FAIL`.
4. `report-corrected.json`: a different source and plan, whose `supersedes`
   field references the failed run. The arithmetic passes technically; the
   global outcome is `REVIEW` and `review` is null, because the accountable
   decision belongs to a human.
5. `summary.json`: the acceptance checks. IDs, timestamps and report hashes
   vary between executions; the expected statuses and invariants do not. The
   demo re-reads the original failure and verifies its report hash is
   unchanged, proving a correction cannot erase the first result.

## How to present the results

- Quote statuses from the files (`state`, `outcome`, `counts`), do not
  paraphrase them from memory.
- Say explicitly that the data is synthetic with declared expected values, not
  an independent ERP capture.
- If the demo exits non-zero, report the exact exit code and the first failing
  acceptance check from `summary.json`; do not retry blindly.
