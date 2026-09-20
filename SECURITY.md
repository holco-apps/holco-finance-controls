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

## Prompt injection posture

Indirect prompt injection (OWASP Top 10 for LLM applications, 2025, LLM01) is
the primary threat model for any agent that reads accounting content: ledger
labels, memo fields, attachments and imported documents can carry hostile
instructions. The posture of this framework is:

- **Analysed content is data, never instructions.** Ledger rows, workbook
  cells, labels and free-text context are parsed by deterministic code into
  typed values. No analysed byte is ever interpreted as a command to the
  engine.
- **No tool reachability from content.** The engine performs no network call
  and grants no tool, filesystem or state access on the basis of anything
  found inside a source. Callers pass content as text or bytes, never as
  paths.
- **Verdicts are computed, not persuaded.** Control outcomes are produced by
  deterministic code from registered bytes. A model reading a hostile label
  cannot change a blocking deterministic result, because no model sits on
  that path.
- **Findings quote minimally.** Reports reference locators and hashes rather
  than echoing free text, which limits second-order injection through
  findings that are later read by a model.

The security consensus is that indirect injection cannot be fully solved at
the model level; the defence is structural (separation of data and
instructions, least privilege, read-only access, bounded outputs). This
framework implements the structural part for the control path. Host
applications embedding a model remain responsible for their own surface.
