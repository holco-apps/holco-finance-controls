# Releases

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
