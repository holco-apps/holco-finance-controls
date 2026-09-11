# Contributing

Contributions should keep the benchmark reproducible and safe to publish.

1. Use synthetic or explicitly licensed data only.
2. Never add credentials, customer names, internal endpoints or production logs.
3. Add a regression test for every policy change.
4. Explain whether a new check is blocking and who owns the business rule.
5. Run `python -m unittest discover -s tests -v` before opening a pull request.

Security issues should be reported privately as described in `SECURITY.md`.
