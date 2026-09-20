"""Counterexamples found by the September 2026 developer-readiness audit."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from holco_finance_controls import Case, Outcome, control_case, run_dataset
from holco_finance_controls.engine import Engine
from holco_finance_controls.packs import execute
from test_engine import xlsx


class AuditRegressions(unittest.TestCase):
    def test_decimal_tolerance_boundary(self):
        for observed, expected in [('100.01', Outcome.PASS), ('100.0101', Outcome.FAIL)]:
            c = Case.from_dict(dict(case_id='boundary', expected_amount='100',
                                    reported_amount=observed, tolerance='0.01'))
            self.assertEqual(control_case(c).outcome, expected)

    def test_large_amount_small_discrepancy(self):
        c = Case.from_dict(dict(case_id='large', expected_amount='10000000000000000',
                                reported_amount='10000000000000001', tolerance='0.01'))
        self.assertEqual(control_case(c).outcome, Outcome.FAIL)

    def test_json_decimal_tokens_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'cases.json'
            path.write_text('[{"case_id":"exact","expected_amount":10000000000000000.00,'
                            '"reported_amount":10000000000000000.01,"tolerance":0.001}]')
            self.assertEqual(run_dataset(path).results[0].outcome, Outcome.FAIL)

    def test_invalid_money_and_boolean_flags_rejected(self):
        for field in ('expected_amount', 'reported_amount', 'tolerance'):
            for value in (True, False, None, 'NaN', 'Infinity', '1e1000'):
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    Case.from_dict(dict(case_id='invalid', expected_amount=1,
                                        reported_amount=1, tolerance=0, **{}) | {field: value})
        for field in ('requires_human_approval', 'agent_requested_review'):
            with self.assertRaises(ValueError):
                Case.from_dict(dict(case_id='invalid', expected_amount=1, reported_amount=1) | {field: 'false'})

    def test_missing_formula_cache_in_both_snapshots_is_inconclusive(self):
        raw = xlsx('100', '<c r="B1"><f>50+50</f></c>')
        r = execute('workbook_comparison', 'numeric_stability', [raw, raw], '0.01')
        self.assertEqual(r['status'], 'INCONCLUSIVE')
        self.assertEqual(r['observed']['uncomparable'], 1)
        self.assertEqual(r['observed']['compared'], 1)

    def test_identical_errors_and_unsupported_text_are_not_verified(self):
        for cell in ('<c r="B1" t="e"><v>#REF!</v></c>',
                     '<c r="B1" t="s"><v>0</v></c>',
                     '<c r="B1" t="inlineStr"><is><t>Label</t></is></c>'):
            raw = xlsx('100', cell)
            self.assertEqual(execute('workbook_comparison', 'numeric_stability', [raw, raw], '0.01')['status'], 'INCONCLUSIVE')

    def test_numeric_failure_still_dominates_missing_cache(self):
        extra = '<c r="B1"><f>50+50</f></c>'
        r = execute('workbook_comparison', 'numeric_stability', [xlsx('100', extra), xlsx('101', extra)], '0.01')
        self.assertEqual(r['status'], 'FAIL')
        self.assertEqual(r['observed']['uncomparable'], 1)

    def test_run_remains_pending_review_and_rejects_changed_build(self):
        e = Engine(Path(':memory:'))
        try:
            s = e.register(b'id,expected,observed\na,1,1\n')
            p = e.plan([s['source_id']], 'reconciliation_csv')
            self.assertEqual(len(p['implementation']['source_sha256']), 64)
            r = e.start(p['plan_id'], p['plan_sha256'])
            self.assertEqual(e.advance(r['run_id'], 8)['outcome'], 'REVIEW')
            with patch('holco_finance_controls.engine.implementation_manifest', return_value={'version': 'changed'}):
                with self.assertRaisesRegex(ValueError, 'implementation'):
                    e.get(r['run_id'])
        finally:
            e.close()
