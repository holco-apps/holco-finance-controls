# Maintainer handoff

Current public release: **0.4.0**, 2026-09-14.

Start with [README](README.md), then [ARCHITECTURE](ARCHITECTURE.md),
[MCP](MCP.md) and the exact [pack reference](REFERENCE.md).
[CHANGELOG](CHANGELOG.md) records compatibility and the prior advanced branch.

## Delivered in the public package

- Ten bounded deterministic packs; local persistent orchestration and six MCP tools.
- Exact-decimal Golden Set verdicts and explicit incomplete XLSX comparisons.
- Source/plan/implementation identities and per-control persistence.
- Self-checking synthetic walkthrough, JSON artefacts and a Node.js subprocess client.
- Tests for original audit counterexamples, real stdio/restart, demo and existing packs.

## Before accepting a change

Install `.[mcp]` and run unittest discovery. Build and install the wheel into a
clean environment, execute the demo there, and exercise the Node caller.
The CI matrix does this on Python 3.11 and 3.12. Do not count an optional skipped
MCP test as an executed transport check.

Rule changes require regression cases, a version/compatibility decision and an
explanation of what the new finding proves. Preserve the original failing expected
case. Tests should fail for the old bug, not simply mirror the new implementation.

## Open boundaries

Independent expert calibration, semantic/LLM evaluation, authenticated human
identity and shared remote hosting are separate projects. This package does not
establish false-positive/negative rates or a professional assurance level.
Trusted ERP capture still requires independently validated provider normalization.
The demo's independent expected statuses test engineering behaviour, not domain expertise.

0.3 databases require their original compatible environment; 0.4 uses new plans
and a new database. Never delete an old database merely to make an upgrade pass.
Private deployments and customer operations are outside this repository's handoff.
