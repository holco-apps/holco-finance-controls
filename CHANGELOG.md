# Releases

## 0.7.0 (2026-09-28)

- numeric_stability locates its findings. The control reported a count of
  cells above tolerance and no address: a reviewer could not act on it, an
  auditor could not be shown it, and a measurement could only compare a count
  to a count, yielding no precision and a recall that never established that
  the cells found were the cells expected. Results now carry divergences
  (sheet, cell, both values, delta) and uncomparable_locations (sheet, cell,
  reason), the latter because that set is what bounds the control's recall
  ceiling and must be auditable.
- Evidence lists are capped at 100 inline, matching the snapshot controls, and
  report divergences_omitted and uncomparable_omitted: the cap never hides its
  own effect. Counts are never capped.
- Deterministic evidence. Cells were walked in set-union order, which varies
  between processes, so a capped list reported a different hundred cells per
  run from identical inputs. The walk is now sorted by sheet, then column
  width and letters, then row, which is also the order a reviewer reads.
  Constrained by a test across two PYTHONHASHSEED values.
- New optional workbook_comparison policy field evidence_cap (1..10000) for
  callers auditing every location. Refused rather than clamped, and validated
  at planning time: a caller silently receiving a truncated set would compute
  a recall against it and never know. It is resolved outside the handler that
  maps ValueError to INVALID_INPUT, so a caller error is not reported as an
  uninterpretable client workbook.
- No new runtime dependency. Protocol version unchanged: the additions are
  additive fields on observed.
- New databases/plans required: implementation identity changed.

## 0.6.0 (2026-09-20)

- Default-deny universal control layer: a plan may only exclude controls its
  pack explicitly lists as excludable; each exclusion is a typed, authored,
  engine-timestamped record surfacing as NOT_RUN, kept in the denominator,
  blocking a global PASS and sign-off. Trusted operator API only, not MCP.
- Mandatory machine-readable reason_code on every INCONCLUSIVE or NOT_RUN
  result (INVALID_INPUT, INPUT_LIMIT_EXCEEDED, MISSING_EVIDENCE,
  PRECONDITION_FAILED, EXCLUDED_BY_PLAN, NOT_EXECUTED); reports expose
  not_run_reasons.
- aggregate_amounts reconciliation control: signed drifts summed overall and
  per optional group column, REVIEW when above tolerance, closing the
  sub-tolerance splitting exploit. Metamorphic invariant tests added.
- Doctrine mapping (DOCTRINE.md) and measurement protocol (docs/MEASUREMENT.md)
  published; protocol non-goals recorded in CONTROL_PROTOCOL.md section 13.
- New databases/plans required: implementation identity and catalogue changed.

## 0.5.0 — 2026-09-14

- Protocol 1.3.0: understanding and explicit human confirmation before execution.
- Forty stable control requirements: 33 reference-tested and 7 host requirements.
- Twenty-four synthetic domain vectors and portable conformance CLI.
- Public-source discovery index and contribution templates.
- No production service, live connectors, private data or calibration added.
- New databases/plans required: package implementation identity changed.


## 0.4.1 — 2026-09-14

- Missing mandatory escalation is a blocking FAIL; correctly requested approval
  remains REVIEW. A failure does not erase the human-review requirement.
- FEC amount validity and entry balance publish distinct named counters. Negative
  or simultaneous debit/credit amounts FAIL; unreadable numbers are INCONCLUSIVE.
- Unknown pack/control calls fail before execution. Unexpected missing internal
  keys propagate; missing OOXML fields are classified at the parser boundary.
  Table/archive/cell ceilings report INPUT_LIMIT_EXCEEDED with name and maximum;
  malformed supported input reports INVALID_INPUT without echoing source values.
- MCP discovery describes all ten packs, ordered sources, required policy and
  input formats, including holco.control-context/1. No new MCP authority.
- Equations and mapped comparisons require explicit numeric/error observations.
  Nested Python modules now participate in implementation identity.
- A fourth Golden Set case isolates missed escalation. Eight new regression tests
  were observed failing before correction; 94 tests pass, including real MCP.

### Compatibility

Use **new plans and a separate database**. Version and source fingerprints reject
0.4.0 runs under 0.4.1. Retain the original package/environment and database to read
historical reports; do not overwrite or silently migrate their evidence. Consumers
of FEC `observed` must handle named objects instead of scalar counts. The four-case
Golden Set now contains two expected FAILs, one PASS and one REVIEW. It is synthetic
and does not establish expert calibration.


## 0.4.0 — 2026-09-14

- Integrate the advanced public branch: ten packs, including observed Excel
  equations, explicit two-sheet reconciliation, structured CSV/XLSX review and
  bounded free-workbook mapping. Exact contracts remain in REFERENCE.md/MCP.md.
- Fix Golden Set money handling: Decimal through parsing and comparison, strict
  monetary/boolean inputs, exact tolerance boundaries, no lost large-amount deltas.
- Fix XLSX comparison: identical missing caches, errors or unsupported nonnumeric
  cells count as uncomparable; they cannot silently establish numeric stability.
  A known numeric mismatch remains FAIL even with incomplete other evidence.
- Bind plans to a manifest of installed Python implementation files and version.
- Add an offline, self-checking walkthrough and a dependency-free Node.js caller.
- Document architecture, language-independent interfaces and public/private boundaries.

### Compatibility

This is a new runner/rule version. Use a **new database and new plans** for 0.4.
0.3 plans are rejected rather than silently resumed under changed rules. Preserve
old databases and their compatible environment for historical inspection; no
in-place migration or production deployment is performed by installing this release.

The plan's source manifest identifies installed Python files, not the full Python
runtime/dependency environment. No code-signing or remote attestation is claimed.
`Case` normalizes amounts to Decimal; JSON reports keep money in explanation strings
and display scores as floats. Prefer decimal strings for financial input; a float
rounded before reaching this package cannot be reconstructed.

The full-workbook numeric comparison is deliberately conservative: unsupported
text/shared-string cells are uncomparable. For a specific financial comparison,
use the explicit worksheet mapping pack rather than treating a whole workbook's
technical PASS as a financial opinion.

## 0.3.0 and additive advanced branch

Persistent engine, local MCP and initial five packs, followed by five advanced
packs on `cdx/holco-control-lot3`. The historical `holco-control-2026.09.12` tag
identifies the earlier advanced implementation. Prior tests established technical
behaviour; independent domain calibration was not claimed.
