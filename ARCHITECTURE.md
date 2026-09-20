# Architecture and trust boundaries

The public package is a local, single-operator control engine. It deliberately
keeps generation, deterministic checks and accountable review separate.

```mermaid
sequenceDiagram
    participant H as Host / developer
    participant E as Engine (Python or MCP)
    participant S as Private local SQLite
    H->>E: Register read-only source bytes
    E->>S: Store bytes + SHA-256
    H->>E: Prepare pack, scope, tolerance and policy
    E-->>H: Plan + source hashes + implementation hash
    Note over H: Obtain consent outside this package
    H->>E: Start with exact plan hash
    E->>S: Create run
    loop At most max_controls per call
        H->>E: Advance existing run
        E->>S: Verify source/plan/build; commit each result
        E-->>H: Results, counts, checkpoint
    end
    Note over H,E: Connection may close and resume the same run
    E-->>H: Technical verdict + human review pending
    Note over H: Correction means new source and successor plan
```

## Where responsibilities live

| Component | Responsibility |
|---|---|
| `engine.py` | Persistence, identity checks, lifecycle, correction links and trusted local review recording |
| `packs.py` and specialized modules | Pure read-only checks; observed/expected results and explicit limitations |
| `server.py` | Six MCP tools; no filesystem-path upload, ERP write or approval tool |
| `models.py`, `metrics.py`, `suite.py` | Smaller Golden Set runner with exact decimal verdicts and bounded stateless replay |
| Host / connector adapter | Source authorization, user consent, provider mapping, pagination, tenant isolation and budgets |
| Human reviewer | Applicability of rules, missing evidence, judgement and authorization of intended use |

The two runners share principles, not storage. The Golden Set CLI recomputes its
prefix when resumed; the persistent engine retains committed controls. Use the
engine for file/ERP workflows. Do not mistake a text rule in a Golden Set fixture
for an automatically interpreted accounting rule.

## States and outcomes are different

Engine states: `PLANNED` → `INTERRUPTED` → `REVIEW` → trusted `CLOSED`.
`REVIEW` is reached when planned controls finish, even if a technical check fails.
Inspect the report's verdicts and counts, not only its state or `complete` flag.

- `FAIL`: at least one blocking deterministic failure.
- `INCONCLUSIVE`: no known failure, but evidence or an executed control is missing.
- Technical `PASS`: the planned deterministic checks passed within their scope.
- Global `REVIEW`: a technically successful unapproved run still needs review.
- `NOT_RUN`: a planned control has no persisted result yet.

An unfinished run can already be `FAIL`; the denominator still includes what has
not run. `sign_off` rejects failures and incompleteness. A separate repeatability
run is required, but that second execution is **not independent expertise**. The
local API accepts an operator-declared identity and rationale; stronger identity
and separation of duties belong to the host.

## Evidence and implementation identity

Sources and plans are checked on access. Completed controls commit separately;
reconnection does not erase them. A successor uses new source IDs and a
`supersedes` run ID; previous reports remain retrievable.

0.4 plans include a SHA-256 manifest of installed package Python source files,
plus the version. A source-code change requires the original build or new plans.
The manifest is calculated at process start/use and cached; never hot-patch a
running engine. It is not a digital signature, a full environment lockfile or
an assertion that the underlying code is trustworthy. Preserve Python and
optional dependency versions in your own deployment provenance.

SQLite is trusted local storage, not tamper-proof archival storage. Anyone with
write access to the database and code is inside the trust boundary. Keep the
database private; the host owns encryption, retention and backups.

## Bounded execution is not a deadline

`max_controls` bounds the number of completed checks per call. One check may parse
an entire bounded input. It does not impose a CPU deadline, a token budget or a
limit on total runs. Use process limits, quotas and cancellation in any remote
host. The MCP server is not a shared multi-tenant service.

## Independent evidence before stronger claims

The package does not call a semantic judge or autonomously challenge its own
method. Benchmarking requires a separately defined expected result, wrong variants,
coverage by family, and expert review where the expected result is a judgement.
The supplied tests and walkthrough are synthetic engineering evidence only.
