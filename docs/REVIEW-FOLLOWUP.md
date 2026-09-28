# Review follow-up — 28 September 2026

Scope: public reference package 0.7.1. The September Claude code review and Gemini
adversarial review supply counterexamples and questions, not independent professional
assurance. Findings below are checked against code/tests; model opinions alone are
not treated as evidence. Private hosting, identities and customer cases are excluded.

## Verified findings and disposition

| Finding | Current disposition | Evidence or remaining boundary |
|---|---|---|
| Missing mandatory human escalation looked like compliant escalation | Fixed before 0.7.1: omission is blocking `FAIL`; requesting review remains distinct | `tests/test_review_regressions.py`, escalation counterexample |
| FEC amount validity always passed | Fixed before 0.7.1: invalid debit/credit rows fail independently of entry balance | `tests/test_review_regressions.py` |
| Invalid control, input limit and malformed input had one misleading error | Fixed before 0.7.1: unknown controls raise; bounded inputs and malformed data have distinct reasons | `tests/test_review_regressions.py` |
| MCP advertised packs without complete input contracts | All ten packs described; 0.7.1 also exposes exact snapshot scope constraints | `tests/test_review_regressions.py`, `tests/test_mcp.py`, `contracts.py` |
| Missing error observation treated inconsistently | Shared numeric observation validation; absence remains inconclusive | `tests/test_review_regressions.py` |
| Implementation identity missed nested Python modules | Recursive manifest and changed-build rejection | `tests/test_review_regressions.py`, `tests/test_audit_regressions.py` |
| Exclusions could silently weaken a plan | Mandatory controls cannot be excluded; permitted exclusions remain `NOT_RUN` and cannot yield global `PASS` | `tests/test_universal_layer.py`; 0.7.1 adds plan transformations over tolerance, exclusion and row order |
| Non-conclusive outcomes lacked machine-readable causes | Mandatory `reason_code`, with explicit report reasons | `tests/test_universal_layer.py` |
| Many small discrepancies evaded per-line tolerance | Aggregate signed drift and explicit group checks, reported as `REVIEW` | `tests/test_universal_layer.py`; opposite drifts can cancel globally, so meaningful grouping remains a caller responsibility |
| Findings counted discrepancies without locating them | 0.7.0 added deterministic locations, values, deltas and explicit evidence truncation | `tests/test_numeric_stability_locations.py`; this does not measure detection accuracy on expert cases |
| Excel scope and dependency coverage lagged integration needs | 0.7.1 bounds the rectangle, binds the requested scope and checks local dependencies without recursion | `tests/test_excel_snapshot.py`; cross-sheet/structured references, ranges, dynamic references and named expressions remain unresolved |
| A numerical alert-fatigue threshold was attributed to unspecified literature | Removed; metrics now state denominators, unavailable cases and selection bias | [Measurement protocol](MEASUREMENT.md); no replacement threshold or domain performance claim |
| A snapshot might be stale or an ERP identifier reused | Explicit boundary documented; stored byte integrity does not establish current state or correct normalization | [Snapshot validity](../SECURITY.md#snapshot-validity-and-adapter-trust); generic freshness enforcement remains open |
| Imported text might manipulate a human reviewer | Host rendering and semantic trust boundary documented | [Human-facing source text](../SECURITY.md#text-presented-to-a-human-reviewer); escaping is not truth validation |

## Still open

1. Independent expert-labelled calibration, holdout cases, localized precision/recall
   and human triage cost. Synthetic test counts do not satisfy this requirement.
2. General cross-sheet formula analysis and semantic adequacy of a chosen plan.
   The plan invariants above detect bounded technical weakening, not fraud concealed
   in an insufficient business scope or incorrect source-selection policy.
3. Trusted extraction time, source-version semantics and freshness policy in each
   host adapter. Existing declared Excel capture times are not attested timestamps.

No automatic sign-off, same-model self-certification, composite trust score or new
runtime framework has been introduced. The deterministic control path remains
network-free. A host may add separately labelled semantic review, with its own
independence and calibration evidence.

## Reproduce the engineering checks

Install `.[mcp]`, then run `python -m unittest discover -s tests -v` and
`holco-controls-conformance --self-test`. The stdio test must execute, not skip,
for a transport claim. See [CI](../.github/workflows/tests.yml) for Python 3.11/3.12,
clean-wheel installation, the demo and Node subprocess checks. These are synthetic
engineering checks, not a regulatory or financial assurance benchmark.

Older plans require their original version/build. Create new plans for 0.7.1;
never change a saved plan hash to make it pass an upgrade.

## Implementation assessment

The reviewed changes are suitable for a reference-engine release within the limits
above. Tolerance, bounded evidence caps and explicitly permitted exclusions remain
configurable. Plan hashes, mandatory controls and fail-closed missing evidence are
intentional invariants. The exact snapshot rectangle and bounded expression grammar
are real constraints: broader inputs require a new explicit scope or parser support,
not a silent relaxation. This release does not certify the hosted service or support
arbitrary Excel formulas. A separate diff review found an unobserved-dependency gap;
a regression now requires `INCONCLUSIVE` for it.
