# Control engine handoff

Updated 2026-09-11. Release 0.3.0.

## Delivered

- Persistent single-operator protocol engine with source and plan integrity checks,
  cumulative results, bounded control execution and resume after process restart.
- Seven packs: reconciliation CSV, technical FEC subset, raw XLSX inspection,
  XLSX snapshot comparison, ERP snapshot versus structured agent claims,
  observed Excel equations and explicitly mapped cross-sheet reconciliation.
- Trusted adapter capture of raw ERP bytes, normalized records, pagination and
  tool trace. General MCP uploads cannot forge connector capture receipts.
- Six stdio MCP tools and a real subprocess transport test, including restart.
- Trusted local sign-off and superseding runs. No approval endpoint in MCP.

No production console, deployed ERP connector or remote gateway changed.
Real-source development checks remain outside Git; public tests are synthetic.

## Evidence and limits

Run `python -m pip install -e '.[mcp]'` and
`python -m unittest discover -s tests -v`.
Tests cover incorrect answers, invented references, missing pages, omitted
records, wrong currency, disallowed tool use, source tampering, interrupted
runs, previous failures on resume, empty controls, non-finite amounts,
decimal precision and a complete MCP subprocess exchange.

Observation verification and the condition of the underlying financial model
are separate conclusions. Raw OOXML inspection also distinguishes stored errors
from conversion errors introduced by higher-level readers. These distinctions
supersede the earlier interpretation of the reference application's PASS labels.

The protocol document remains a target beyond the implemented engine. Repeating
the same checks is repeatability, not independent adversarial expertise. No
automatic professional sign-off, regulatory certification or LLM judge exists.
The ERP pack verifies referenced sums; it does not automatically extract every
claim from prose or verify the correctness of provider-specific normalization.

## Next integration work

1. Private ERP adapter: capture directly from an authorised read response,
   map actual provider fields and pagination, and validate against fixtures.
   Completion evidence: agent result checked against connector-captured data,
   with existing account/dossier authorisation enforced. Owner: to assign.
2. Independent challenge: define reviewer input, independent checks and identity
   attestation. Completion evidence: an intentionally wrong result is rejected
   by an independent method. Owner: to assign.
3. Remote MCP gateway: authenticate tenant context and add storage isolation,
   process deadlines and quotas before enabling shared access. Completion
   evidence: cross-tenant and timeout tests plus a real client call. No public
   remote deployment authorised or performed in this lot. Owner: to assign.

Review these integration decisions on the next connector work session.
Additive cross-sheet update, 2026-09-11: protocol document 1.2; engine contract
version remains 0.3.0 so existing source-bound plans remain readable. Comparisons
are bound to two immutable sources and exposed in the approved plan. Missing
mapping, numeric data or error-type observations cannot pass. Same-cell comparisons
are rejected. 51 Python tests pass; the stdio test is skipped in the deployment
environment because the optional MCP SDK is absent. Remote integration and its
HTTPS tests belong to the separately managed private gateway, not this repository.

Rollback: revert the 0.3 change commit and use 0.2's Golden Set runner. Keep
private 0.3 databases for evidence; 0.2 does not consume their protocol records.

## Additive dossier review pack — 2026-09-12

`dossier_review` accepts a strict semicolon CSV of declared prior/current/reporting
amounts and explanations. Five families check period, per-line and aggregate
reconciliation, variations, explained amounts and review coverage. Fixed v1
thresholds are bound into the approved plan. Missing values remain inconclusive;
an explanation matching the arithmetic still requires human evidence review.
The pack does not retrieve cited documents or compare an independent ERP source.
No semantic LLM or professional assurance is implemented. Existing 0.3 contracts
are retained. The surrounding private web integration is managed separately.

Validation: 2026-09-12, unittest discovery: 59 pass, one optional stdio SDK test
skipped. Eight new tests include compensating differences, zero bases, missing
explanations, contradictory amounts, malformed/duplicate input and period scope.
Next: authorized real-case calibration with a named reviewer (to assign), then
measure family-specific false positives/negatives. No deployment in this lot.

## Additive XLSX review intake — 2026-09-12, lot 2

The new `dossier_review_xlsx` pack uses the same financial method with an explicit
named-sheet contract and raw XLSX source evidence. No guessed column mapping,
formula recalculation or semantic claim. A reproducible fictitious template is
provided by `review_template`. Detailed scope and original locations are preserved;
formulas with even apparently valid caches cannot become verified inputs.

Validation: 66 discovered tests, 65 pass and one optional MCP SDK test skipped.
Six new tests cover exact source/scope, formula caches, shared strings, hidden rows,
missing values, invalid named tables and XML declarations. Independent openpyxl
read/write of the template and reimport passed locally (not a runtime dependency).
No actual Excel desktop session or real-client method calibration claimed.
