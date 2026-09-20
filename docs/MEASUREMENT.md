# Measurement protocol: from repeatable to proven

Repeating the same deterministic code establishes repeatability, not validity.
This document defines the measurement protocol that turns these controls into
an evidenced claim: published error rates per control family, on a labelled
truth set, with method and limits stated.

## Principles

1. Metrics are published per control family, never as a single global
   reliability score. A global score hides failure modes and gives false
   assurance.
2. The truth set is labelled by an accountable professional (each case marked
   `PASS`, `REVIEW` or `FAIL` with a short justification), versioned, and
   grown from real incidents.
3. The method and its limits (sample size, domain, non-generalisability) are
   published together with the numbers.
4. Arithmetic is verified by deterministic code and metamorphic tests, never
   by a second language model.

## Metrics

For each control family:

- **Precision** and **recall** against the labelled truth set, and the raw
  false positive and false negative counts.
- **Seeded-anomaly recall**: known errors are injected into otherwise clean
  datasets; the proportion detected is reported per anomaly type.
- **Evidence coverage**: the percentage of reported figures bound to a stable
  source identifier (and hash where available).
- **Justified escalation rate**: the proportion of `REVIEW` outcomes that a
  professional reviewer confirms as worth reviewing.
- **Silence tests**: runs where a planned control is deliberately omitted must
  surface it as `NOT_RUN`; a silent omission is a measurement failure of the
  framework itself.

Operational quality of alerting, tracked internally per rule:

- false positive rate per rule (the alert-fatigue literature places the trust
  collapse threshold near one false alert in two);
- alert-to-incident conversion rate;
- share of alerts never investigated;
- triage time.

## Truth set construction

- Start from the versioned golden set in `examples/` and extend it with every
  material production incident, reformulated as a minimal reproducible case.
- Anonymisation is a review step, not a find-and-replace: a pseudonymised
  ledger can remain re-identifiable through labels, counterparty names,
  invoice numbers or bank references. No case derived from customer data is
  published without a documented legal basis and a publication review, as
  required by `CONTRIBUTING.md`.
- Every case records who labelled it and when. Disagreements between labellers
  are kept, not averaged away.

## Metamorphic invariants

Because the correct answer is not always known (the oracle problem), the test
suite also asserts properties that must hold for any input:

- per-entry debit equals credit on balanced synthetic ledgers, and a single
  unbalanced entry is detected;
- additivity: splitting an amount into parts that sum to the original does not
  change a balance verdict;
- permutation invariance: reordering rows never changes a verdict;
- tolerance monotonicity: increasing a tolerance can never turn a pass into a
  failure;
- a blocking deterministic failure survives any combination of non-blocking
  review signals.

See `tests/test_metamorphic_invariants.py` for the executable form.

## Regression gate

The golden set CLI exits non-zero on any failure and `--fail-on-review`
provides a stricter release gate. Continuous integration runs the full unit
suite and the golden set on every change; published metrics are recomputed
when the truth set version changes, and each published table cites the truth
set version it was computed on.
