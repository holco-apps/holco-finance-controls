# Maintainer handoff

Current public release: **0.5.0**, 2026-09-14.

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


## Review follow-up — 2026-09-14

The 0.4 review exposed gaps not covered by the prior 86 tests. Added counterexamples
for escalation, FEC row validity, errors/limits, MCP discovery, missing observations
and nested build identity. Each new test was observed failing before its fix.
Keep amount validity distinct from entry balance; neither synthetic checks nor a
passing CI establishes expert calibration. Current suite: 94 tests including MCP.
For 0.4.1, use a new database and plans; preserve historical environments/reports.
Next: independent expert cases and calibration remain open; no private deployment.


## Protocol distribution release — 0.5.0

Protocol 1.3.0, 40 stable requirements (33 reference-tested, 7 host-only), 24
synthetic domain vectors and portable golden-verdict/1 CLI. The versioned spec
manifest hashes the normative documents; CI rejects untracked document drift.
Public data index contains links to institutional sources, not downloaded data,
customer records or validated calibration. New contribution forms accept scoped
implementation reports and synthetic counterexamples. Hosted code remains outside
this package; the existing MIT reference implementation stays independently usable.

Local validation: 101 unittest cases including the real MCP transport; 24/24 golden
verdicts matched their fixed oracles. Installed wheel conformance and demo verified
outside the checkout. CI separately validates Python 3.11 and 3.12 on publication.
These engineering checks do not establish complete protocol conformance, unseen
agent accuracy, certification, professional assurance or a production SLA.

Next: independent builder integrations and counterexamples; expand domain oracles
with reviewed, publishable evidence. Do not infer adoption from publishing volume.

## GitHub readability — 2026-09-14

Repository landing page shortened from 164 to 120 lines: concrete failure/correction
example, installation first, then purpose-based navigation. Added a French entry,
documentation map and examples index with explicit exit-code guidance. Normative
protocol/catalogue and implementation are unchanged; no new release required.
GitHub description simplified and Discussions enabled. Added a bug issue form,
question/security/documentation routing and a PR template. No discussion, outreach
message or community adoption claim was posted.

Verification: 64 local links/anchors checked across the five new/rewritten entry
and navigation documents; GitHub YAML parsed, diff whitespace checked. Check CI
on the published revision and preserve all existing spec fingerprints.
