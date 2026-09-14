# Control catalogue — 40 versioned requirements

Protocol 1.3.0. Experimental, independently reviewable requirements. These are HOLCO requirements, not SOC 2 criteria, NEP equivalences or an accredited standard.

**reference** means a bounded public implementation has the linked regression test. **host** means the public package does not implement the requirement. Passing the reference tests does not establish host compliance. No claim of 40 fully implemented controls.

Machine-readable source: [control-catalog.json](spec/control-catalog.json). Existing packs group several requirements; requirement count is not pack count.

## HFC-001 — Purpose and intended use
**Family:** Intake · **Implementation:** host

Record the requested decision, entity, period and exclusions before proposing controls.

Failure behaviour: Missing scope remains NEEDS_INPUT; no full-scope conclusion.

Verification required from the integrating host: demonstrate the gate with both valid and invalid evidence. No public executable implementation claim.

## HFC-002 — Document understanding
**Family:** Intake · **Implementation:** host

Treat the filename as an initial clue; cite content evidence and disclose sampled or unreadable regions.

Failure behaviour: Uncertain type remains a proposal, never a proven business classification.

Verification required from the integrating host: demonstrate the gate with both valid and invalid evidence. No public executable implementation claim.

## HFC-003 — Human confirmation of understanding
**Family:** Intake · **Implementation:** host

Obtain explicit confirmation of document interpretation, intended result and proposed scope before material checks.

Failure behaviour: No confirmation means no material execution.

Verification required from the integrating host: demonstrate the gate with both valid and invalid evidence. No public executable implementation claim.

## HFC-004 — Immutable source identity
**Family:** Plan · **Implementation:** reference

Bind exact source bytes to SHA-256 and reject changed bytes on resume.

Failure behaviour: Reject an integrity mismatch.

Executable regression: [test_tampered_source_rejected_on_resume](tests/test_engine.py).

## HFC-005 — Approved plan identity
**Family:** Plan · **Implementation:** reference

Require the exact plan digest supplied at execution to match the stored plan.

Failure behaviour: Reject a different digest; the host must separately authenticate consent.

Executable regression: [test_wrong_plan_hash_rejected](tests/test_engine.py).

## HFC-006 — Material scope changes
**Family:** Plan · **Implementation:** host

Create a new plan and renewed human confirmation when meaning, mapping or scope changes.

Failure behaviour: Earlier consent cannot authorise the new scope.

Verification required from the integrating host: demonstrate the gate with both valid and invalid evidence. No public executable implementation claim.

## HFC-007 — Implementation identity
**Family:** Plan · **Implementation:** reference

Bind runtime control implementation identity to persisted runs.

Failure behaviour: Reject incompatible code when continuing a run.

Executable regression: [test_run_remains_pending_review_and_rejects_changed_build](tests/test_audit_regressions.py).

## HFC-008 — Unique case identifiers
**Family:** Population · **Implementation:** reference

Reject duplicate case IDs instead of overwriting evidence.

Failure behaviour: Duplicate IDs are invalid input.

Executable regression: [test_duplicate_case_ids_are_rejected](tests/test_suite.py).

## HFC-009 — Empty populations
**Family:** Population · **Implementation:** reference

Disclose an empty population; do not treat vacuous totals as assurance.

Failure behaviour: INCONCLUSIVE for absent data.

Executable regression: [test_empty_population_and_duplicate_ids](tests/test_engine.py).

## HFC-010 — Exact decimal comparison
**Family:** Amounts · **Implementation:** reference

Compare amounts using exact decimal arithmetic and a declared tolerance.

Failure behaviour: Difference above tolerance is FAIL.

Executable regression: [test_decimal_tolerance_boundary](tests/test_audit_regressions.py).

## HFC-011 — Small discrepancies in large amounts
**Family:** Amounts · **Implementation:** reference

Preserve cents even when the absolute amount is large.

Failure behaviour: Material decimal difference is not rounded away.

Executable regression: [test_large_amount_small_discrepancy](tests/test_audit_regressions.py).

## HFC-012 — Valid numeric observations
**Family:** Amounts · **Implementation:** reference

Reject booleans, non-finite values and unsupported numeric precision.

Failure behaviour: Invalid values never become PASS.

Executable regression: [test_invalid_money_and_boolean_flags_rejected](tests/test_audit_regressions.py).

## HFC-013 — Required source coverage
**Family:** Sources · **Implementation:** reference

Compare required source IDs against actual cited IDs.

Failure behaviour: A missing required citation is FAIL; citation alone is not provenance.

Executable regression: [test_missing_source_fails](tests/test_controls.py).

## HFC-014 — Independent ERP capture
**Family:** Sources · **Implementation:** reference

Require a receipt established by the trusted capture boundary, outside agent JSON.

Failure behaviour: An agent-declared receipt cannot establish trusted provenance.

Executable regression: [test_erp_capture_receipt_cannot_be_forged_by_json](tests/test_engine.py).

## HFC-015 — Complete pagination
**Family:** Sources · **Implementation:** reference

Inspect pagination metadata from the trusted source capture.

Failure behaviour: An outstanding cursor makes coverage INCONCLUSIVE.

Executable regression: [test_incomplete_pagination](tests/test_erp.py).

## HFC-016 — Population count reconciliation
**Family:** Sources · **Implementation:** reference

Reconcile captured record counts with the stated expected population.

Failure behaviour: Truncation makes coverage INCONCLUSIVE.

Executable regression: [test_truncated_population](tests/test_erp.py).

## HFC-017 — Known unique record references
**Family:** Sources · **Implementation:** reference

Reject duplicate and unknown IDs in agent claims.

Failure behaviour: Invalid referenced populations are FAIL.

Executable regression: [test_duplicate_and_unknown_sources](tests/test_erp.py).

## HFC-018 — Full-scope totals
**Family:** Sources · **Implementation:** reference

Require all relevant records when the declared scope is all-period records.

Failure behaviour: A selective total cannot pass a full-population claim.

Executable regression: [test_selective_total](tests/test_erp.py).

## HFC-019 — Request period alignment
**Family:** Scope · **Implementation:** reference

Compare claim period with the independently requested period.

Failure behaviour: Correct arithmetic for another period does not pass request scope.

Executable regression: [test_correct_amount_for_wrong_request_is_rejected](tests/test_erp.py).

## HFC-020 — Currency and period consistency
**Family:** Scope · **Implementation:** reference

Reject sums spanning inconsistent currencies or periods without a declared transformation.

Failure behaviour: Mixed scope is FAIL in the supported ERP contract.

Executable regression: [test_mixed_currency_or_period](tests/test_erp.py).

## HFC-021 — Read-only policy
**Family:** Tools · **Implementation:** reference

Compare trusted tool traces with allowed operations.

Failure behaviour: Write operations or missing trusted traces do not pass.

Executable regression: [test_write_tool_and_missing_trace](tests/test_erp.py).

## HFC-022 — Forbidden tool use
**Family:** Tools · **Implementation:** reference

Detect explicitly forbidden tools in the observed trace.

Failure behaviour: A forbidden call is blocking FAIL.

Executable regression: [test_forbidden_tool_fails](tests/test_controls.py).

## HFC-023 — Trace authority
**Family:** Tools · **Implementation:** reference

Do not replace missing capture traces with the agent own declaration.

Failure behaviour: Untrusted declarations cannot repair missing evidence.

Executable regression: [test_agent_claimed_trace_not_trusted](tests/test_erp.py).

## HFC-024 — Debit-credit balance
**Family:** FEC · **Implementation:** reference

Check the supported FEC population debit and credit totals.

Failure behaviour: Unbalanced totals fail; this is not full statutory FEC compliance.

Executable regression: [test_fec_balanced_and_unbalanced](tests/test_engine.py).

## HFC-025 — Valid line amounts
**Family:** FEC · **Implementation:** reference

Validate nonnegative debit/credit observations and invalid dual-sided lines separately from aggregate balance.

Failure behaviour: Malformed line amounts fail even if totals compensate.

Executable regression: [test_fec_amounts_validate_rows_separately_from_balance](tests/test_review_regressions.py).

## HFC-026 — Formula cache coverage
**Family:** Spreadsheet · **Implementation:** reference

Disclose missing numeric formula observations.

Failure behaviour: Missing caches are INCONCLUSIVE, including in both compared versions.

Executable regression: [test_missing_formula_cache_in_both_snapshots_is_inconclusive](tests/test_audit_regressions.py).

## HFC-027 — Stored errors versus reader warnings
**Family:** Spreadsheet · **Implementation:** reference

Distinguish actual spreadsheet error cells from reader formatting warnings.

Failure behaviour: Reader warnings must not be invented as stored Excel errors.

Executable regression: [test_excel_raw_error_separate_from_bad_date_format](tests/test_engine.py).

## HFC-028 — Explicit missing observations
**Family:** Spreadsheet · **Implementation:** reference

Keep missing numeric cells absent instead of replacing them with zero.

Failure behaviour: Missing evidence cannot establish a balanced calculation.

Executable regression: [test_missing_numeric_evidence_never_zero_filled](tests/test_financial_workbook.py).

## HFC-029 — Unit-consistent sums
**Family:** Spreadsheet · **Implementation:** reference

Detect monetary sums that include percentage cells within supported formula patterns.

Failure behaviour: A mixed-unit sum is FAIL.

Executable regression: [test_monetary_sum_with_ratio_and_small_difference_not_suppressed](tests/test_financial_workbook.py).

## HFC-030 — Period-grain alignment
**Family:** Spreadsheet · **Implementation:** reference

Do not compare monthly and year-to-date values solely because their end date matches.

Failure behaviour: An unsupported mapping remains unselected.

Executable regression: [test_month_and_ytd_with_same_end_date_are_not_compared](tests/test_financial_workbook.py).

## HFC-031 — Non-self reconciliation
**Family:** Spreadsheet · **Implementation:** reference

Require distinct observations for a cross-source reconciliation.

Failure behaviour: A same-cell self-comparison cannot establish independent agreement.

Executable regression: [test_self_comparison_and_duplicate_ids_refused](tests/test_excel_reconciliation.py).

## HFC-032 — Rule applicability and version
**Family:** Business rules · **Implementation:** host

Record the authoritative rule, jurisdiction, effective period and applicable population before applying a business threshold.

Failure behaviour: An unsupported rule remains unverified, not a regulatory failure.

Verification required from the integrating host: demonstrate the gate with both valid and invalid evidence. No public executable implementation claim.

## HFC-033 — Loaded context is not execution
**Family:** Business rules · **Implementation:** reference

Distinguish retrieved rules and memories from executed checks.

Failure behaviour: A loaded note cannot count as a passed rule.

Executable regression: [test_all_variances_kept_and_context_is_not_execution_proof](tests/test_financial_workbook.py).

## HFC-034 — Label semantic judgement
**Family:** AI review · **Implementation:** host

Record model/provider/version, observed evidence, uncertainty and the semantic nature of each model assessment.

Failure behaviour: Unlabelled model opinion cannot count as a deterministic finding.

Verification required from the integrating host: demonstrate the gate with both valid and invalid evidence. No public executable implementation claim.

## HFC-035 — Mandatory escalation
**Family:** Decision · **Implementation:** reference

Request human review when the trusted policy requires it.

Failure behaviour: Missing escalation is FAIL and human review remains required.

Executable regression: [test_missing_escalation_is_blocking_but_still_requires_human](tests/test_review_regressions.py).

## HFC-036 — Failure survives approval
**Family:** Decision · **Implementation:** reference

Preserve blocking deterministic failure when a reviewer or agent attempts to approve it.

Failure behaviour: A failed run cannot be signed off as successful.

Executable regression: [test_failure_cannot_be_signed_off](tests/test_engine.py).

## HFC-037 — Authenticated accountable reviewer
**Family:** Decision · **Implementation:** host

Authenticate the named reviewer and bind their action to the current scope and report.

Failure behaviour: A string containing a person name does not prove consent.

Verification required from the integrating host: demonstrate the gate with both valid and invalid evidence. No public executable implementation claim.

## HFC-038 — Complete denominator and restart
**Family:** Evidence · **Implementation:** reference

Retain all planned controls and earlier outcomes across interruption and resume.

Failure behaviour: NOT_RUN and prior failures remain visible.

Executable regression: [test_resume_preserves_results_and_denominator_across_restart](tests/test_engine.py).

## HFC-039 — Correction lineage
**Family:** Evidence · **Implementation:** reference

Preserve the original failure, register a successor and keep human review pending.

Failure behaviour: Correction must not overwrite the earlier report.

Executable regression: [test_walkthrough_preserves_failure_and_never_approves](tests/test_demo.py).

## HFC-040 — Independent closure evidence
**Family:** Evidence · **Implementation:** reference

Require a distinct challenge run and immutable closure record; authenticate independence in the host.

Failure behaviour: A repeated run is not proof of independent professional expertise.

Executable regression: [test_human_closure_requires_separate_run_and_is_immutable](tests/test_engine.py).
