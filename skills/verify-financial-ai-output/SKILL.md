---
name: verify-financial-ai-output
description: Verify a financial answer produced by an AI agent (a total, a balance, a reconciliation, a P&L figure) against its declared sources, with executable controls and retained evidence. Use when the user asks "is this AI-produced number correct?", "check this financial output", or wants proof rather than a narrative. Requires the holco-finance-controls engine installed locally (Python 3.11+, no API key, no network).
---

# Verify a financial AI output

You are applying the HOLCO control protocol: compare an agent's output with
explicit sources and rules, retain the evidence, and leave the accountable
decision with a human. Never present a deterministic PASS as a professional
validation.

## Prerequisites

Check that the engine is installed: `holco-finance-controls --help`.
If it is not, install it from the repository (Python 3.11+ required):

```sh
git clone https://github.com/holco-apps/holco-finance-controls.git
cd holco-finance-controls
python3 -m venv .venv && . .venv/bin/activate
python -m pip install -e .
```

## Method

1. **Identify the claim and its source.** What exact figure did the agent
   produce, and which file or dataset is the declared source? The engine works
   on declared sources with a SHA-256 identity; it is not an independent ERP
   capture. If the user cannot name the source, say so and stop: there is
   nothing to control against.
2. **Build an explicit plan.** A plan lists the controls (for example
   `population` and `amounts`), the tolerance, the SHA-256 of the source and
   the review requirement. Changing the source or the plan invalidates its
   identity. See CONTROL_PROTOCOL.md in the repository for the plan format and
   REFERENCE.md for the API.
3. **Execute and read the report, never paraphrase it.** The report is the
   deliverable. Read `state`, `deterministic_outcome`, `outcome`, `review` and
   `counts` (PASS, FAIL, REVIEW, INCONCLUSIVE, NOT_RUN). A run with
   `NOT_RUN > 0` is incomplete and must be presented as incomplete, never as a
   success.
4. **Interpret outcomes with the protocol's semantics.**
   - `FAIL`: a measured discrepancy, with the evidence retained. Report the
     exact difference.
   - A correction is a new source and a new plan whose report references the
     failed run in `supersedes`. The original failure, its timestamp and its
     report hash remain unchanged: a correction never erases the evidence of
     the first result.
   - Technical PASS with `outcome: REVIEW` and `review: null` means the
     arithmetic passes and a human decision is still pending. Say exactly that.
5. **Hand the decision to a human.** State what was controlled, what was not,
   and what remains for the reviewer. A missing result is inconclusive, not
   compliant.

## What you must not do

- Do not fabricate a control result from reading the file yourself: only the
  engine's report counts as evidence.
- Do not run the demo CLI on arbitrary uploaded documents; it is an acceptance
  walkthrough. Use the engine API or the MCP tools for real runs.
- Do not summarize away limits: tolerances, unexecuted controls and pending
  reviews are part of the answer.
