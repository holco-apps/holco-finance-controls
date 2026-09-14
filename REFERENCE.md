# Control packs and API reference

A small, reproducible control framework for verifying that financial AI agents
follow the numbers, sources and business rules — not just that they sound right.

> Deterministic when possible. AI when necessary. Human when accountable.

This public reference contains the local engine and synthetic examples.
Private hosting, credentials, customer data and internal endpoints are excluded.
Start with the runnable walkthrough in [README.md](README.md).

## Persistent engine and MCP (0.4)

The executable protocol engine now accepts CSV reconciliation data, technical
FEC extracts, Excel workbooks and ERP snapshots paired with agent answers.
It stores immutable source bytes, hashed plans and cumulative control results
in a private SQLite database. Resuming a run preserves earlier results.

The six-tool local MCP interface is documented in [MCP.md](MCP.md), including
installation, input contracts, trusted ERP capture and deployment boundaries.
An agent's own source declaration cannot establish ERP provenance. The trusted
connector adapter captures the raw response before the agent uses it.

```python
from pathlib import Path
from holco_finance_controls.engine import Engine

engine = Engine(Path("/tmp/synthetic-holco-controls.db"))
try:
    source = engine.register(b"id,expected,observed\na,100,101\n")
    plan = engine.plan([source["source_id"]], "reconciliation_csv")
    run = engine.start(plan["plan_id"], plan["plan_sha256"])
    report = engine.advance(run["run_id"], max_controls=2)
    assert report["deterministic_outcome"] == "FAIL"
finally:
    engine.close()
```

The engine provides technical controls and trusted local review recording.
`excel_reconciliation` adds explicit amount comparisons between two observed
worksheets, with missing evidence kept inconclusive and no implicit rounding.
An independent professional or adversarial assessment is still a distinct
step: repeating the same code only establishes repeatability. No production
console or remote HOLCO MCP service is changed by installing this package.

## Structured dossier review

The additive `dossier_review` pack expects UTF-8 semicolon CSV with exact columns:
`poste;periode;n_1;n;reporting;explication;montant_explique;piece`.
Supply `policy={"required_period": "2025", "required_currency": "EUR"}` when
planning. Five families cover declared period, reconciliations, variations,
quantified explanations and review coverage. The approved plan records v1
thresholds: 0.01 EUR reconciliation; variation at least 1,000 EUR and 20% (zero
base: amount only). At most 2,000 unique rows are accepted.

All compared values come from the supplied table. Document references are
unverified declarations and never suffice for an automatic professional sign-off.
Missing evidence is inconclusive; arithmetic contradictions fail; human review
remains necessary even when the numerical checks pass.

The `dossier_review_xlsx` pack accepts the downloadable XLSX equivalent: one
visible sheet named `Revue HOLCO`, with the exact eight French headers generated
by the template below. The plan records its range, included row count and excluded
sheets; findings retain original worksheet/row references and the XLSX hash.
Hidden/filtered rows are included. Formulas, merged cells, error values and data
outside A:H or beyond 2,000 rows are rejected; formulas must be pasted as values.
Other worksheets are outside this financial review. A workbook without the named
sheet can still use the existing technical workbook pack.

Generate a reproducible fictitious template (with a separate instruction sheet):

```bash
python -m holco_finance_controls.review_template /tmp/review-template.xlsx
```

## Control flow

```mermaid
flowchart LR
  A[Financial workflow] --> B[Deterministic checks]
  B --> C[Source checks]
  C --> D[Business rules]
  D --> E[Labelled AI review]
  E --> F[Human review]
  F --> G[Regression suite]
```

The included reference implementation covers the deterministic core through
small, composable control objects. An AI review may add context, but it
cannot silently override a failed control.

```python
from holco_finance_controls import AmountAccuracy, EvidenceCoverage, control_case

result = control_case(case, metrics=[AmountAccuracy(), EvidenceCoverage()])
assert result.outcome.value == "PASS"
```

## What is controlled

Each synthetic case contains source facts, an agent answer and explicit
tolerances. The runner controls:

- numerical agreement with the source facts;
- source identifiers and evidence coverage;
- business-rule compliance;
- escalation when the decision is materially ambiguous.
- required and forbidden tool use in an agent trajectory.

The control outcome distinguishes:

- `PASS`: all blocking controls pass;
- `REVIEW`: no blocking failure, but human judgement is required;
- `FAIL`: at least one blocking control failed.
- `INCONCLUSIVE`: evidence or an executable method is missing;
- `NOT_RUN`: a planned control did not execute.

## Run locally

Python 3.11+ is sufficient; the package has no runtime dependency.

```bash
python -m holco_finance_controls examples/golden_set.json
python -m holco_finance_controls examples/golden_set.json --format summary
python -m holco_finance_controls examples/golden_set.json --plan
python -m holco_finance_controls examples/golden_set.json --max-cases 2
python -m unittest discover -s tests -v
```

From a fresh clone, either install the package or expose `src`:

```bash
python -m pip install -e .
holco-finance-controls examples/golden_set.json
```

The command emits JSON Lines plus an aggregate summary so results can be
archived and compared in CI. It exits with code `1` when any case fails; use
`--fail-on-review` for a stricter release gate.

Bounded runs emit a checkpoint containing the dataset hash and next case index.
Resume with `--resume-from INDEX --checkpoint-sha256 HASH`. The hash must match
the exact dataset bytes, preventing a checkpoint from being applied to another
version. An interrupted run is incomplete and exits non-zero; cases not
executed are counted as `NOT_RUN`, never as passes.

The Golden Set CLI is stateless: resuming recomputes the earlier prefix to
retain its outcomes. Use the persistent engine/MCP for checkpointed file and
ERP workflows without recomputing prior controls.

## Control protocol

The normative workflow is documented in
[`CONTROL_PROTOCOL.md`](CONTROL_PROTOCOL.md). It formalises intake, planning,
deterministic execution, separately labelled probabilistic review, accountable
human decision and proof-bearing closure.

- A plan declares metrics and accountable cases before execution.
- Each report is bound to the exact dataset bytes with SHA-256.
- Evidence links stable source IDs to optional source hashes without embedding
  customer content.
- Deterministic blocking failures cannot be overridden by an AI judge.
- `deterministic_outcome` is distinct from the global review decision.
- Checkpoints preserve partial work after a quota, timeout or manual pause.

## Why this is not a general-purpose LLM judge

General LLM quality frameworks are useful for relevancy, style and qualitative
judgement. HOLCO Finance Controls starts elsewhere: amounts, source coverage,
forbidden actions and approval boundaries are executable invariants. These
checks are local, deterministic and model-independent. Probabilistic metrics
can be added later as explicitly labelled, calibrated evidence.

## Golden Set

[`examples/golden_set.json`](examples/golden_set.json) is intentionally small
and readable. It demonstrates:

1. a fully grounded cash-position answer (`PASS`);
2. an answer that is numerically correct but needs accountable approval
   (`REVIEW`);
3. a plausible answer that contradicts the ledger (`FAIL`).

Real benchmarks should be versioned, reviewed by domain owners and extended
with every material production incident. They should never be built from
customer data without a documented legal basis and publication review.

## Design boundaries

- Control is separate from generation.
- Deterministic controls run before probabilistic judgement.
- Evidence is identified by stable source IDs, not prose alone.
- A reviewer is required for decisions marked accountable.
- No network call, telemetry or model provider is embedded in this example.

See [SECURITY.md](SECURITY.md) for responsible disclosure and
[CONTRIBUTING.md](CONTRIBUTING.md) for the publication rules.

## Licence

MIT. Copyright © 2026 HOLCO INVEST.

## Free P&L workbook review

The `financial_workbook` pack accepts **two immutable sources**: original XLSX
bytes and a JSON `holco.control-context/1` snapshot with `profile`, `memory`,
`rules` and `drafts` arrays. Context provenance and access control belong to the
trusted host adapter; registering JSON alone does not establish authenticity.

A plan requires `required_period` and exposes `workbook_scope`: exact recognized
labels, row references, period headers and actual/budget column candidates.
Merged headers preserve cumulative versus monthly distinctions. Multiple
candidates require a new plan with `policy.pnl_mapping` set to a candidate ID
before starting; a unique candidate is still a proposal approved with the plan.
Unrecognized workbooks retain technical controls and explicit missing coverage.

Six families cover source scope, stored errors/missing caches, vertical SUM unit
mixes (including shared SUM formulas), four signed P&L equation patterns,
actual/budget differences for labelled rows, and separately inconclusive business
rules. No materiality threshold suppresses recognized rows. Numeric blanks are
never silently replaced with zero. Free-text memories can be associated by
keywords, explicitly as navigation aids, without determining cause or resolution.

No Excel recalculation, external ledger retrieval, arbitrary formula evaluation,
automatic semantic rule execution, or professional assurance is provided. The
mapping assumes revenues positive and expenses negative and requires review.
Tests remain fully synthetic; customer acceptance evidence is managed separately.
