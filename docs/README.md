# Documentation map

[Repository home](../README.md) · [Français](../README.fr.md)

## Three reading paths

| Reader | Suggested order |
|---|---|
| First-time visitor | [Run the demo](../README.md#try-it-locally) → [read its results](../WALKTHROUGH.md) → [understand the limits](../ARCHITECTURE.md) |
| Agent or application builder | [Integration](../INTEGRATION.md) → [input packs](../REFERENCE.md) → [MCP contract](../MCP.md) → [conformance tasks](../CONFORMANCE.md) |
| Reviewer or contributor | [Protocol](../CONTROL_PROTOCOL.md) → [requirements](../CONTROL_CATALOG.md) → [test oracles](../CONFORMANCE.md) → [contributing](../CONTRIBUTING.md) |

## Find the right document

| Document | Answers |
|---|---|
| [Walkthrough](../WALKTHROUGH.md) | What does the example do, and what do its report fields mean? |
| [Architecture](../ARCHITECTURE.md) | What is trusted? Where do persistence, identity and human authority stop? |
| [Protocol](../CONTROL_PROTOCOL.md) | What must a conforming host implement throughout the lifecycle? |
| [Control catalogue](../CONTROL_CATALOG.md) | Which requirement applies, how should it fail, and is it implemented? |
| [Pack reference](../REFERENCE.md) | Which input structures and checks does the reference accept? |
| [Integration](../INTEGRATION.md) | How do Python, Java/JVM, JavaScript and other callers connect? |
| [MCP](../MCP.md) | Which stdio tools and JSON contracts are available? |
| [Conformance](../CONFORMANCE.md) | How do I export tasks and check another implementation's responses? |
| [Examples](../examples/README.md) | Which sample should I run or inspect first? |
| [Public data](../PUBLIC_DATA_INDEX.md) | Where can I discover institutional financial sources? |
| [Releases](../CHANGELOG.md) | What changed, and which historical environments must I preserve? |
| [Security](../SECURITY.md) | How do I report a vulnerability privately? |

## Machine-readable entry points

- [Control catalogue](../spec/control-catalog.json): stable HFC identifiers and coverage.
- [Protocol release manifest](../spec/protocol-release.json): exact normative document hashes.
- [Reconciliation vectors](../src/holco_finance_controls/conformance_data/reconciliation.json).
- [FEC vectors](../src/holco_finance_controls/conformance_data/fec.json).
- [Cash vectors](../src/holco_finance_controls/conformance_data/cash.json).
- [Closing vectors](../src/holco_finance_controls/conformance_data/closing.json).

## Keep these distinctions clear

A **requirement** states expected behaviour. A **pack** groups executable checks.
A **golden vector** supplies a fixed input and expected result. A **conformance
profile** tests only its declared scope. None of these counts is a reliability
percentage or a professional certification.
