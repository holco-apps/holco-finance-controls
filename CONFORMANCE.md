# Test a control implementation against HOLCO

**Profile `holco.golden-verdict/1` · Protocol 1.3.0 · 24 synthetic vectors.**
No account, API key, production connector or model-provider dependency.

## One command to challenge the reference

```sh
python -m pip install -e .
holco-controls-conformance --self-test
```

Exit 0 means every published oracle matched, including intentional FAIL and
INCONCLUSIVE cases. Exit 1 means a mismatch or missing response; exit 2 means an
invalid command/input. No case is silently skipped. This differs from the older
`holco-finance-controls` CLI, whose exit 1 signals a failing financial result.

| Domain | Vectors | Scope |
|---|---:|---|
| [Reconciliation](src/holco_finance_controls/conformance_data/reconciliation.json) | 6 | Exact match, wrong total, inclusive tolerance, excess, large amount, missing observation |
| [FEC](src/holco_finance_controls/conformance_data/fec.json) | 6 | Entry balance, mismatch, negative/dual-sided line, invalid date, valid amounts distinct from balance |
| [Cash](src/holco_finance_controls/conformance_data/cash.json) | 6 | Opening + movement = closing; discrepancy, missing value, error coverage and reference |
| [Closing](src/holco_finance_controls/conformance_data/closing.json) | 6 | Provision roll-forward and missing/error observations |

Cash and closing share an arithmetic capability; domain labels do not establish
distinct professional calibration. FEC is a technical subset, not statutory
compliance. Each JSON vector includes a fixed expected status and a human-readable
arithmetic/contract oracle. Those expectations are not derived from the latest run.

## Bring your implementation — Python, JVM, JS or another runtime

```sh
holco-controls-conformance --tasks > tasks.json
# Your implementation reads each task and emits the response contract below.
holco-controls-conformance --check your-responses.json
```

Tasks contain `case_id`, `pack`, `control_id`, UTF-8 source strings, tolerance,
policy and `case_sha256`. They exclude oracle answers. Reference answers remain
public in the vectors: this is an interoperability suite, not a hidden benchmark.
The digest is SHA-256 of the task without `case_sha256`, encoded as UTF-8 JSON with
sorted keys, compact separators and unescaped Unicode. Echo the supplied digest
for the exact input you processed; do not substitute another task or edited file.

Response document:

```json
{
  "profile": "holco.golden-verdict/1",
  "implementation": "your-control-adapter@revision",
  "responses": []
}
```

Populate `responses` with one object per task: `case_id`, `case_sha256`, `status`
(PASS, FAIL, REVIEW, INCONCLUSIVE or NOT_RUN), `observed` and `expected` evidence.
The empty document above fails all 24 vectors. Unknown or duplicate IDs are invalid;
missing responses fail. To inspect a complete executable example:

```sh
holco-controls-conformance --reference > reference-responses.json
holco-controls-conformance --check reference-responses.json
```

This checker compares the verdict and input binding and requires evidence fields.
It does **not** verify the truth of an arbitrary implementation's evidence, observe
its internal tool execution, authenticate a human or certify ERP provenance. A
model could memorise public answers. Attach traces and an independently reviewed
unseen dataset for an effectiveness claim. A finance agent can integrate this
profile through its control adapter; generating plausible prose is not the interface.

## Report only what was tested

Suggested claim: “Implementation X at revision Y matched 24/24 synthetic vectors
of HOLCO golden-verdict/1 on DATE; broader protocol and business validation pending.”
Never replace that with “HOLCO certified”, “SOC 2 equivalent”, “NEP compliant”,
“financial accuracy 100%” or a claim about professional liability.

The broader [catalogue](CONTROL_CATALOG.md) links reference regression tests for
33 requirements and marks 7 host requirements. Passing these 24 vectors does not
cover all 40 requirements. CI runs the full reference tests separately.
