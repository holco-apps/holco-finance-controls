"""Independent counterexamples from the 0.4 review."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from holco_finance_controls import Case, Outcome, control_case
from holco_finance_controls import engine
from holco_finance_controls.packs import execute, CATALOG
from test_engine import xlsx
from test_excel_snapshot import fixture

HEADER = 'JournalCode\tEcritureNum\tEcritureDate\tDebit\tCredit\n'

class ReviewRegressions(unittest.TestCase):
    def test_missing_escalation_is_blocking_but_still_requires_human(self):
        base = dict(case_id='review', expected_amount=100, reported_amount=100, requires_human_approval=True)
        good = control_case(Case.from_dict(dict(base, agent_requested_review=True)))
        bad = control_case(Case.from_dict(dict(base, agent_requested_review=False)))
        self.assertEqual(good.outcome, Outcome.REVIEW)
        self.assertEqual(bad.outcome, Outcome.FAIL)
        self.assertEqual(bad.deterministic_outcome, Outcome.FAIL)
        self.assertTrue(bad.human_review_required)
        check = next(c for c in bad.checks if c.name == 'accountable_decision_escalated')
        self.assertTrue(check.blocking)

    def test_fec_amounts_validate_rows_separately_from_balance(self):
        raw = (HEADER + 'AC\t1\t20260914\t100\t0\n').encode()
        r = execute('fec_tsv', 'amounts', [raw], '.01')
        self.assertEqual(r['status'], 'PASS')
        self.assertEqual(r['observed'], {'checked_rows': 1, 'invalid_amount_rows': 0})
        self.assertEqual(execute('fec_tsv', 'entry_balance', [raw], '.01')['status'], 'FAIL')
        for debit, credit in [('100','50'), ('-1','0')]:
            r = execute('fec_tsv', 'amounts', [(HEADER + f'AC\t1\t20260914\t{debit}\t{credit}\n').encode()], '.01')
            self.assertEqual(r['status'], 'FAIL')
            self.assertEqual(r['observed']['invalid_amount_rows'], 1)

    def test_unknown_control_is_call_error(self):
        with self.assertRaisesRegex(ValueError, 'unknown control'):
            execute('workbook_xlsx', 'stored_errorz', [xlsx('100')], '.01')

    def test_internal_missing_stat_is_not_a_source_error(self):
        with patch('holco_finance_controls.packs.workbook', return_value=({}, {})):
            with self.assertRaises(KeyError):
                execute('workbook_xlsx', 'stored_errors', [xlsx('100')], '.01')

    def test_row_limit_is_distinct_from_malformed_input(self):
        raw = (HEADER + 'AC\t1\t20260914\t100\t0\n' * 100001).encode()
        r = execute('fec_tsv', 'population', [raw], '.01')
        self.assertEqual(r['status'], 'INCONCLUSIVE')
        self.assertEqual(r['reason_code'], 'INPUT_LIMIT_EXCEEDED')
        self.assertEqual(r['limit'], {'name': 'rows', 'maximum': 100000})
        bad = execute('fec_tsv', 'population', [b'bad'], '.01')
        self.assertEqual(bad['reason_code'], 'INVALID_INPUT')

    def test_equations_require_explicit_error_observation(self):
        for error in ('absent', ''):
            data = fixture()
            for cell in data['cells']:
                if error == 'absent': cell.pop('error')
                else: cell['error'] = error
            r = execute('excel_snapshot', 'declared_equations', [json.dumps(data).encode()], '.01')
            self.assertEqual(r['status'], 'INCONCLUSIVE')

    def test_discovery_covers_all_packs(self):
        from holco_finance_controls import server
        # Read the actual tool return without requiring the optional transport.
        class Capture:
            def tool(self):
                def register(fn):
                    setattr(self, fn.__name__, fn)
                    return fn
                return register
        import sys, types
        fake = types.ModuleType('mcp.server'); fake.MCPServer = lambda name: Capture()
        with patch.dict(sys.modules, {'mcp.server': fake}):
            r = server.build_server(None).list_control_protocols()
        self.assertEqual(set(r['formats']), set(CATALOG))
        self.assertEqual(set(r['input_contracts']), set(CATALOG))
        for contract in r['input_contracts'].values():
            self.assertEqual(contract['source_count'], len(contract['sources']))
            self.assertIn('required_policy', contract)
        self.assertIn('holco.control-context/1', json.dumps(r['input_contracts']['financial_workbook']))

    def test_build_identity_includes_nested_sources(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); (root/'engine.py').write_text('original')
            (root/'nested').mkdir(); source = root/'nested'/'control.py'; source.write_text('first')
            try:
                with patch.object(engine, '__file__', str(root/'engine.py')):
                    engine.implementation_source_hash.cache_clear()
                    before = engine.implementation_source_hash()
                    source.write_text('second')
                    engine.implementation_source_hash.cache_clear()
                    self.assertNotEqual(before, engine.implementation_source_hash())
            finally:
                engine.implementation_source_hash.cache_clear()
