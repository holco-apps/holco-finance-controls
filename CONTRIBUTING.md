# Contributing

Contributions should keep the benchmark reproducible and safe to publish.

1. Use synthetic or explicitly licensed data only.
2. Never add credentials, customer names, internal endpoints or production logs.
3. Add a regression test for every policy change.
4. Explain whether a new check is blocking and who owns the business rule.
5. Run `python -m unittest discover -s tests -v` before opening a pull request.

Security issues should be reported privately as described in `SECURITY.md`.

## Evolve the public language

Use stable HFC IDs from CONTROL_CATALOG.md. Propose a requirement with its
failure behaviour and evidence contract before writing an adapter. Link actual
regression tests for reference coverage; mark unimplemented host gates explicitly.
A new golden vector needs an oracle fixed independently of the observed output.
Do not update expected verdicts simply to make the current implementation pass.

Run `holco-controls-conformance --self-test` and the full unit suite. Submit
counterexamples and implementation reports through the issue templates. Share a
scoped profile result, not a certification badge. Public sources can be proposed
for PUBLIC_DATA_INDEX.md with access terms and extraction limitations.
