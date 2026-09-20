# Doctrine and standards mapping

This document maps each mechanism of the HOLCO control framework (the H-VISA
protocol) to the professional, regulatory and security doctrine it is designed
to serve. It is a design-intent mapping written by the maintainers. It is not a
certification, not an audit opinion and not legal advice. Where a reference has
not yet been confirmed against an official primary source, this is stated.

## Why this mapping exists

A control framework for financial AI agents is bought as defensible
compliance, not as software. A DAF, statutory auditor (commissaire aux
comptes) or CISO needs to know which recognised requirement each mechanism
answers. The mapping below links the executable mechanisms of this repository
to those requirements, one by one.

## Mechanism to doctrine matrix

| Mechanism (executable, in this repository) | Where | External anchor |
|---|---|---|
| Five distinct outcomes: `PASS`, `REVIEW`, `FAIL`, `INCONCLUSIVE`, `NOT_RUN`; a planned control that did not execute is never counted as a pass | `models.Outcome`, CLI checkpoint semantics, `CONTROL_PROTOCOL.md` section 5 | SR 11-7 (outcomes analysis as a mandatory validation component); NEP 500 (audit evidence must be probative: an absence of evidence is not evidence) |
| Deterministic checks run first; a probabilistic (AI) review is separately labelled and can never override a blocking deterministic failure | `controls.control_case`, `CONTROL_PROTOCOL.md` invariants | SR 11-7 "effective challenge"; documented LLM-as-judge failure modes (position, verbosity and self-preference biases); NIST AI RMF (Measure and Manage functions) |
| A control plan is declared and hashed before execution; each report is bound to the exact dataset bytes with SHA-256 | `engine.plan` / `engine.start`, checkpoint hash matching | NEP 500 (evidence traceable to its source); EU AI Act transparency obligations (art. 50); ISO/IEC 42001 and NIST AI RMF documentation and traceability expectations |
| Trusted connector adapter: ERP bytes are captured before the agent uses them; an agent's own source declaration cannot establish provenance | `erp_agent_response` pack, `MCP.md` | French professional doctrine direction (CNCC report of December 2024, CNCC practice sheets of June 2025, CNOEC charter 2025): an AI answer is not, by itself, audit evidence, and professional responsibility does not transfer to the AI vendor |
| Accountable human decision: cases marked accountable require a reviewer; `REVIEW` is a first-class outcome | `AccountableDecision` metric, Gate G of the protocol | NEP 240 (auditor response to fraud risk, including review of journal entries); CNCC and CNOEC position that final responsibility remains with the professional |
| Technical FEC controls (column presence, `YYYYMMDD` dates, debit/credit validity, per-entry balance, duplicates) | `fec_tsv` pack in this repository; the companion repository `holco-fec-controls` | Article A.47 A-1 of the French Livre des procédures fiscales and the arrêté of 29 July 2013 (18 normative FEC fields in a fixed order); the DGFiP open-source checker "Test Compta Demat" (CeCILL licence); sanction defined by article 1729 D of the CGI |
| Untrusted content (ledger labels, attachments, free text) is treated as data, never as instructions; no tool access is granted from within analysed content | `SECURITY.md` prompt injection posture; text inputs only, no filesystem paths from callers | OWASP Top 10 for LLM applications (2025), LLM01 Prompt Injection; industry consensus that indirect injection cannot be fully solved in the model and requires defence in depth |
| Statistical or anomaly signals must be framed as `REVIEW`, never as automatic `FAIL` | `CONTROL_PROTOCOL.md` non-goals | ISA 240 / NEP 240 journal entry testing practice: anomaly detection signals risk, it does not prove misstatement |

## Calibration of claims

The DGFiP states that its own FEC checker does not constitute an attestation of
conformity and does not bind the administration. The same calibration applies
here: a green run of these controls is a reproducible technical statement about
the supplied bytes, not a professional certification. `CONTROL_PROTOCOL.md`
states explicitly which guarantees are implemented and which require separate,
independently validated integrations.

## Verification status of external references

Confirmed against primary or official sources:

- Article A.47 A-1 LPF and the 18-field FEC structure (Legifrance,
  impots.gouv.fr); "Test Compta Demat" published by DGFiP on GitHub under
  CeCILL; article 1729 D CGI.
- NEP 240 and NEP 500 are homologated by ministerial order and therefore
  opposable in France.
- SR 11-7 (Federal Reserve and OCC guidance on model risk management).
- OWASP Top 10 for LLM applications, 2025 edition.

Pending confirmation before any citation in a client-facing or contractual
document:

- The exact wording attributed to the revised NEP 315 ("an answer produced by
  an AI system does not, by itself, constitute audit evidence") must be
  verified against the official text on h2a.fr or the homologation order.
- The precise arithmetic checks performed by "Test Compta Demat" (beyond
  structural checks) must be read in the DGFiP source code before being
  asserted.
- The EU AI Act risk classification of accounting control tools and the
  post-Omnibus timeline evolve quickly; reconfirm against the Official Journal
  of the EU at the time of communication. This framework is designed for
  transparency obligations either way.
