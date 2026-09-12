import tempfile
import unittest
from pathlib import Path
from holco_finance_controls.engine import Engine

HEADER = 'poste;periode;n_1;n;reporting;explication;montant_explique;piece\n'


class DossierReviewTest(unittest.TestCase):
    def run_case(self, text):
        engine = Engine(Path(':memory:'))
        self.addCleanup(engine.close)
        source = engine.register((HEADER + text).encode())
        plan = engine.plan([source['source_id']], 'dossier_review', policy={'required_period':'2025','required_currency':'EUR'})
        run = engine.start(plan['plan_id'],plan['plan_sha256'])
        return engine.advance(run['run_id'],8)

    def test_healthy_still_requires_review(self):
        report = self.run_case('A;2025;10000;10100;10100;;;\n')
        self.assertEqual(report['deterministic_outcome'],'REVIEW')
        self.assertEqual([r['status'] for r in report['results'][:4]],['PASS']*4)

    def test_compensated_errors_are_not_hidden_by_total(self):
        report = self.run_case('A;2025;100;100;110;;;\nB;2025;100;100;90;;;\n')
        checks = report['results'][1]['observed']['checks']
        self.assertEqual([c['status'] for c in checks],['FAIL','FAIL','PASS'])

    def test_missing_source_never_passes(self):
        report = self.run_case('A;2025;;2000;2000;;;\n')
        self.assertEqual(report['deterministic_outcome'],'INCONCLUSIVE')

    def test_contradiction_is_arithmetic_not_semantic(self):
        report = self.run_case('A;2025;10000;15000;15000;Hausse;3000;Contrat\n')
        self.assertEqual(report['results'][3]['status'],'FAIL')

    def test_declared_evidence_requires_human_examination(self):
        report = self.run_case('A;2025;10000;15000;15000;Hausse;5000;Contrat\n')
        self.assertEqual(report['results'][3]['status'],'REVIEW')

    def test_period_mismatch(self):
        report = self.run_case('A;2024;100;100;100;;;\n')
        self.assertEqual(report['results'][0]['status'],'FAIL')

    def test_resume_retains_earlier_failure(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'engine.db'
            e=Engine(path)
            source=e.register((HEADER+'A;2025;100;100;101;;;\n').encode())
            plan=e.plan([source['source_id']],'dossier_review',policy={'required_period':'2025','required_currency':'EUR'})
            run=e.start(plan['plan_id'],plan['plan_sha256'])
            e.advance(run['run_id'],2)
            e.close()
            e=Engine(path)
            report=e.advance(run['run_id'],8)
            e.close()
            self.assertEqual(report['deterministic_outcome'],'FAIL')
            self.assertEqual(report['executed'],5)

    def test_bad_headers_and_non_finite_rejected(self):
        for data in ['a,b\n1,2','A;2025;NaN;100;100;;;\n','A;2025;100;100;100;;;\nA;2025;100;100;100;;;\n']:
            with self.assertRaises(ValueError):self.run_case(data)
