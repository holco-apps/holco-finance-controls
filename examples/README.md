# Examples — what to run first

[Repository home](../README.md) · [Documentation](../docs/README.md)

All examples are synthetic. Install the package and activate its environment first.

| Example | Command or file | What it demonstrates |
|---|---|---|
| Complete workflow | `holco-controls-demo --output demo-evidence` | Failure, interruption, restart, correction lineage and human review pending |
| Portable conformance | `holco-controls-conformance --self-test` | 24 fixed verdicts across four domains |
| Node.js caller | `node examples/node-client.mjs demo-node` | Subprocess integration and JSON checking, with no npm dependency |
| Original Golden Set | [golden_set.json](golden_set.json) | Four readable agent-behaviour cases, including intentional failures |
| ERP/agent contract | [erp_snapshot.json](erp_snapshot.json) + [agent_claims.json](agent_claims.json) | Shape of captured records and claimed totals; not a real ERP connector |

Use a new output directory for each demo. The Node client invokes the demo CLI;
it is not an MCP client. Follow [MCP.md](../MCP.md) for stdio tool integration.

To run the original Golden Set:

```sh
holco-finance-controls examples/golden_set.json --format summary
```

**Expected exit code: 1**, because the dataset intentionally contains failures.
By contrast, the demo and conformance self-test exit **0** when the expected
behaviour is reproduced, including correct rejection of negative cases.

An ERP-shaped JSON file does not prove independent acquisition. Trusted capture
receipts belong to the integrating host; see the [trust boundaries](../ARCHITECTURE.md).
