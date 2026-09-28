# HOLCO Finance Controls

[![Tests](https://github.com/holco-apps/holco-finance-controls/actions/workflows/tests.yml/badge.svg?branch=main)](https://github.com/holco-apps/holco-finance-controls/actions/workflows/tests.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Status: alpha](https://img.shields.io/badge/status-alpha-orange.svg)](https://github.com/holco-apps/holco-finance-controls/releases)

**An AI agent gives you a financial answer. What proves it is correct?**

HOLCO publishes a control protocol, executable checks and synthetic test cases.
Compare an agent's output with explicit sources and rules, retain the evidence,
and leave the accountable decision with a human.

[**Try it ↓**](#try-it-locally) · [**Integrate**](INTEGRATION.md) · [**Read the protocol**](CONTROL_PROTOCOL.md) · [**Documentation**](docs/README.md) · [**Français**](README.fr.md)

## One concrete example

The included demo compares a declared source amount with an agent observation:

| Source | Agent observation | What the control records |
|---|---|---|
| €12,400 | €12,900 | `FAIL` — €500 discrepancy |
| €12,400 | €12,400, submitted as a correction | Technical `PASS`; final `REVIEW` pending a human decision |

It interrupts and resumes the run, retains the original failure and links the
correction. These are synthetic examples with declared expected values, not an
independent ERP capture. [See the complete walkthrough](WALKTHROUGH.md).

## Try it locally

**Python 3.11+ required. No API key, LLM, ERP connection or Docker needed.**

```sh
git clone https://github.com/holco-apps/holco-finance-controls.git
cd holco-finance-controls
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
holco-controls-demo --output demo-evidence
```

Open `demo-evidence/summary.json`, `report-failed.json` and
`report-corrected.json`. The demo exits **0** when the expected workflow is verified,
including the intentional failure. Use a new output directory for each run, or
omit `--output` for a fresh temporary directory.

<details>
<summary>Windows / PowerShell</summary>

```powershell
git clone https://github.com/holco-apps/holco-finance-controls.git
cd holco-finance-controls
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e .
holco-controls-demo --output demo-evidence
```

</details>

## Choose your next step

| You want to… | Start here | What you get |
|---|---|---|
| Understand the process | [Control protocol](CONTROL_PROTOCOL.md) | Lifecycle, evidence requirements and human gates |
| Inspect a particular requirement | [40-control catalogue](CONTROL_CATALOG.md) | Stable IDs, failure behaviour and implementation coverage |
| Test your control implementation | [Conformance guide](CONFORMANCE.md) | 24 synthetic vectors, portable JSON tasks and result checking |
| Connect an application or agent | [Integration guide](INTEGRATION.md) | Python API, MCP, CLI/JSON and JVM integration boundaries |
| Choose a file format | [Pack reference](REFERENCE.md) | Exact inputs, controls and exclusions for 10 packs |
| Find public financial sources | [Data index](PUBLIC_DATA_INDEX.md) | Institutional links, access notes and limitations |
| Map controls to regulation | [Doctrine mapping](DOCTRINE.md) | SR 11-7, NEP 240/500, AI Act art. 50, ISO 42001, NIST AI RMF, OWASP LLM01, FEC |
| Measure real error rates | [Measurement protocol](docs/MEASUREMENT.md) | Per-family precision/recall plan, seeded anomalies, silence tests |

## Test an implementation

After installation:

```sh
holco-controls-conformance --self-test
holco-controls-conformance --tasks > tasks.json
```

Run your implementation on `tasks.json`, then check its response document:

```sh
holco-controls-conformance --check your-responses.json
```

The [response contract and runnable reference adapter](CONFORMANCE.md) explain
what to emit. A deliberately incorrect input must receive the expected negative
verdict. Returning `PASS` everywhere fails the suite.

## What is implemented?

**Reference 0.7.1 · Protocol 1.3.0 · Alpha · MIT.**

New in 0.7.1: bounded Excel scope guards and local formula dependency checks;
unsupported references stay inconclusive. [Review follow-up](docs/REVIEW-FOLLOWUP.md)
records the verified fixes, evidence limits and work still open.

New in 0.7.0: `numeric_stability` says **where**. It reported a count of cells
above tolerance and no address, which a reviewer cannot act on and an auditor
cannot be shown, and which reduces any measurement to comparing a count to a
count. Results now carry `divergences` (sheet, cell, both values, delta) and
`uncomparable_locations`, the latter because that set is what bounds the
control's recall ceiling. Evidence is capped at 100 inline and reports what it
omitted; counts are never capped, and an optional `evidence_cap` policy
(1..10000) serves callers auditing every location. The walk is sorted, because
set-union order varies between processes and a capped list would otherwise
report a different hundred cells per run from identical inputs.

New in 0.6.0: a default-deny universal control layer (a plan may only exclude
explicitly excludable controls, through typed, authored, timestamped exclusion
records that surface as `NOT_RUN` and block a global `PASS`); a mandatory
machine-readable `reason_code` on every `INCONCLUSIVE` or `NOT_RUN` result,
with `not_run_reasons` in reports; and an `aggregate_amounts` reconciliation
control that closes the sub-tolerance splitting exploit. Metamorphic
invariants guard the deterministic core
([`tests/test_metamorphic_invariants.py`](tests/test_metamorphic_invariants.py)).

| Layer | Available here | Boundary |
|---|---|---|
| Protocol | 40 versioned requirements | 33 have bounded reference tests; 7 require host implementation |
| Checks | 10 deterministic packs, persistence, restart and correction lineage | Local single-operator reference; no hosted production service |
| Conformance | 24 synthetic vectors: reconciliation, FEC, cash and closing | Verdict, input binding and evidence-field presence; not certification |
| Integration | Python, six MCP stdio tools, CLI/JSON and a Node subprocess example | No bundled Java SDK or HTTP server |
| AI and human review | Specified roles and trusted local review API | No LLM service or authenticated human identity in this package |

The production console, live ERP adapters, customer records and private calibration
are outside this repository. A hash identifies bytes; it does not establish source
truth or human consent. Technical success does not imply professional assurance.
[Architecture and trust boundaries](ARCHITECTURE.md).

## Help improve the controls

- [Report a reproducible bug](https://github.com/holco-apps/holco-finance-controls/issues/new?template=bug.yml).
- [Challenge a requirement](https://github.com/holco-apps/holco-finance-controls/issues/new?template=control-counterexample.yml) with synthetic input and an independent expected result.
- [Share an implementation report](https://github.com/holco-apps/holco-finance-controls/issues/new?template=integration.yml).
- [Ask an integration question](https://github.com/holco-apps/holco-finance-controls/discussions).

[Contribution guide](CONTRIBUTING.md) · [Security reporting](SECURITY.md) ·
[Releases and downloads](https://github.com/holco-apps/holco-finance-controls/releases) ·
[Compatibility notes](CHANGELOG.md)

For 0.5.0, use a new database and plans. Keep original compatible environments for
historical runs. CI tests Python 3.11/3.12, the installed wheel, MCP and the demo;
passing tests is not a financial-accuracy benchmark.
