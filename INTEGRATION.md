# Integrating from Java, TypeScript and other languages

Python is the reference implementation, not a requirement for the calling
application. Keep one authoritative rules engine and exchange structured data.

| Caller | Interface | What to implement |
|---|---|---|
| Python | `Engine` local API | Register, plan, start, advance, read; trusted adapter/reviewer boundary |
| MCP-capable host in Java/JVM, TypeScript or another language | MCP over local stdio | Launch `holco-controls-mcp`, discover the six tools, call with documented JSON arguments |
| Any process-capable application | CLI and JSON output | Run the demo or Golden Set command, check exit status and parse JSON |

**The Node example is executable; this repository does not ship a Java SDK or
an HTTP service.** It does not duplicate the checks in another language.

## Runnable JavaScript example (no npm dependencies)

After installation with the virtual environment activated:

```sh
node examples/node-client.mjs demo-node
```

Set `HOLCO_CONTROLS_DEMO` to the absolute installed demo executable if it is not
on PATH. The example invokes the same Python engine through a subprocess and
validates its JSON summary. Use MCP for normal persisted tool calls; the demo
CLI is an acceptance walkthrough, not an API for arbitrary uploaded documents.

## Java/JVM integration

An MCP host launches the executable and speaks MCP JSON-RPC over stdio according
to [MCP.md](MCP.md). The host's language does not change tool names or input/output
contracts. Select an MCP client library compatible with your host; no particular
Java SDK or transport version is certified by this repository.

For an initial Java smoke test, `ProcessBuilder` can invoke the installed
`holco-controls-demo --output <new-directory> --format json`, with each argument
as a separate list element. Check the exit code, parse stdout as JSON, and handle
stderr separately. Bound execution time and drain streams to avoid deadlocks.
Do not construct a shell command by interpolating user input.

For Golden Set batches, the `holco-finance-controls` command accepts a dataset
path controlled by your host. An exit code of 1 may be an expected detected
financial failure, while the demo exits 0 only if its acceptance checks succeed.
See [REFERENCE](REFERENCE.md) for flags and explicit review gating.

## Production host obligations

Use private per-operator storage, authenticated tenant context, source authorization,
request limits and process deadlines before exposing any remote interface. An
agent cannot approve its own plan merely by echoing a hash. Public contracts can
be documented and reviewed without publishing your credentials, routing, ERP
mapping code or deployment infrastructure.
