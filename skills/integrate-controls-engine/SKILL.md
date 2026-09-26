---
name: integrate-controls-engine
description: Integrate the holco-finance-controls engine into an application, a CI pipeline, or an MCP-capable host (Java, TypeScript, Python or any process-capable caller). Use when the user wants to call the controls engine from their own code, run the Golden Set in CI, or expose the engine's six tools over MCP stdio. Keeps one authoritative rules engine; never reimplement the checks in another language.
---

# Integrate the controls engine

Python is the reference implementation, not a requirement for the calling
application. Keep one authoritative rules engine and exchange structured data.
This repository does not ship a Java SDK or an HTTP service; do not invent one.

## Choose the interface

| Caller | Interface | What to implement |
|---|---|---|
| Python | `Engine` local API | Register, plan, start, advance, read; trusted adapter and reviewer boundary |
| MCP-capable host (JVM, TypeScript, other) | MCP over local stdio | Launch `holco-controls-mcp`, discover the six tools, call them with the documented JSON arguments |
| Any process-capable application | CLI + JSON output | Run the demo or Golden Set command, check the exit status, parse the JSON |

Authoritative documents in the repository: INTEGRATION.md (callers and
boundaries), REFERENCE.md (API), MCP.md (tool schemas), CONFORMANCE.md (Golden
Set and acceptance).

## MCP stdio server

Install the MCP extra, then launch the server from the host:

```sh
python -m pip install -e ".[mcp]"
holco-controls-mcp
```

The host discovers the six tools over stdio. Use MCP for normal persisted tool
calls; the demo CLI is an acceptance walkthrough, not an API for arbitrary
uploaded documents.

## JavaScript callers

A runnable example with no npm dependencies ships in the repository:

```sh
node examples/node-client.mjs demo-node
```

It invokes the Python engine through a subprocess and validates its JSON
summary. Set `HOLCO_CONTROLS_DEMO` to the absolute installed demo executable if
it is not on PATH.

## CI integration

Run the conformance demo or the Golden Set command in the pipeline and gate on
the exit status. Exit `0` means the expected workflow is verified, including
the intentional failure. Parse `summary.json` for the acceptance checks rather
than grepping logs.

## Boundaries to preserve

- One engine: the caller adapts data in and decisions out; the checks live in
  the Python engine only.
- Evidence is immutable: corrections supersede, they never rewrite a report.
- The reviewer boundary is part of the integration: a deterministic PASS must
  reach a human as a pending decision, not as an approval.
