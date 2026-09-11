# HOLCO Finance Evals

A small, reproducible benchmark for testing whether financial AI agents follow
the numbers, sources and business rules — not just whether they sound right.

> Deterministic when possible. AI when necessary. Human when accountable.

This public repository is a deliberately isolated technical exhibit. It uses
only synthetic data and contains no HOLCO production code, credentials, client
names or internal endpoints.

## Evaluation flow

```mermaid
flowchart LR
  A[Financial workflow] --> B[Deterministic checks]
  B --> C[Source checks]
  C --> D[Business rules]
  D --> E[AI evaluator]
  E --> F[Human review]
  F --> G[Regression suite]
```

The included reference implementation covers the deterministic core through
small, composable metric objects. An AI evaluator may add context, but it
cannot silently override a failed control.

```python
from holco_finance_evals import AmountAccuracy, EvidenceCoverage, evaluate_case

result = evaluate_case(case, metrics=[AmountAccuracy(), EvidenceCoverage()])
assert result.outcome.value == "PASS"
```

## What is evaluated

Each synthetic case contains source facts, an agent answer and explicit
tolerances. The runner evaluates:

- numerical agreement with the source facts;
- source identifiers and evidence coverage;
- business-rule compliance;
- escalation when the decision is materially ambiguous.
- required and forbidden tool use in an agent trajectory.

The aggregate outcome has three states:

- `PASS`: all blocking controls pass;
- `REVIEW`: no blocking failure, but human judgement is required;
- `FAIL`: at least one blocking control failed.

## Run locally

Python 3.11+ is sufficient; the package has no runtime dependency.

```bash
python -m holco_finance_evals examples/golden_set.json
python -m holco_finance_evals examples/golden_set.json --format summary
python -m unittest discover -s tests -v
```

From a fresh clone, either install the package or expose `src`:

```bash
python -m pip install -e .
holco-finance-evals examples/golden_set.json
```

The command emits JSON Lines plus an aggregate summary so results can be
archived and compared in CI. It exits with code `1` when any case fails; use
`--fail-on-review` for a stricter release gate.

## Why this is not a general-purpose LLM judge

General evaluation frameworks are useful for relevancy, style and qualitative
judgement. HOLCO Finance Evals starts elsewhere: amounts, source coverage,
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

- Evaluation is separate from generation.
- Deterministic controls run before probabilistic judgement.
- Evidence is identified by stable source IDs, not prose alone.
- A reviewer is required for decisions marked accountable.
- No network call, telemetry or model provider is embedded in this example.

See [SECURITY.md](SECURITY.md) for responsible disclosure and
[CONTRIBUTING.md](CONTRIBUTING.md) for the publication rules.

## Licence

MIT. Copyright © 2026 HOLCO INVEST.
