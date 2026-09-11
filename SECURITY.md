# Security policy

Do not open a public issue for a vulnerability or suspected data exposure.
Report it to [privacy@holco.co](mailto:privacy@holco.co) with the repository,
affected version, reproduction steps and impact. Do not include credentials or
personal data in the report.

This repository provides a local single-operator control engine and synthetic
fixtures. It does not provide authenticated multi-tenant remote hosting. Source
bytes are stored in a private SQLite database; storage encryption, retention
and backups remain the operator's responsibility. MCP callers cannot supply
filesystem paths, invoke ERP writes or issue human sign-off. Reports may still
contain sensitive derived financial information. See MCP.md for boundaries.
