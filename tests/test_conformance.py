import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from holco_finance_controls.conformance import cases, task, check_responses, reference_responses


class ConformanceTests(unittest.TestCase):
    def test_independent_domain_oracles(self):
        data=reference_responses()
        report=check_responses(data)
        self.assertTrue(report['conforms'])
        self.assertEqual(report['planned'],24)
        for domain in ('reconciliation','fec','cash','closing'):
            self.assertEqual(sum(c['case_id'].startswith(domain+'-') for c in cases()),6)
        self.assertIn('FAIL',{r['status'] for r in data['responses']})
        self.assertIn('INCONCLUSIVE',{r['status'] for r in data['responses']})

    def test_blanket_pass_and_missing_case_do_not_conform(self):
        responses=reference_responses()
        for r in responses['responses']:r['status']='PASS'
        self.assertFalse(check_responses(responses)['conforms'])
        responses=reference_responses();responses['responses'].pop()
        report=check_responses(responses)
        self.assertFalse(report['complete']);self.assertFalse(report['conforms'])
        self.assertEqual(report['planned'],24)

    def test_changed_input_missing_evidence_and_duplicate_id(self):
        for field in ('case_sha256','observed','expected'):
            responses=reference_responses();del responses['responses'][0][field]
            self.assertFalse(check_responses(responses)['conforms'])
        responses=reference_responses();responses['responses'].append(copy.deepcopy(responses['responses'][0]))
        with self.assertRaises(ValueError):check_responses(responses)
        responses=reference_responses();responses['responses'][0]['case_id']='invented'
        with self.assertRaises(ValueError):check_responses(responses)

    def test_exported_inputs_exclude_oracles_and_hash_changes_with_source(self):
        c=copy.deepcopy(cases()[0]);first=task(c)
        self.assertNotIn('expected_status',first);self.assertNotIn('oracle',first)
        c['sources'][0]+='\n'
        self.assertNotEqual(task(c)['case_sha256'],first['case_sha256'])

    def test_cli_invalid_and_empty_results_exit_nonzero_even_with_optimization(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'answers.json';p.write_text(json.dumps({'profile':'holco.golden-verdict/1','responses':[]}))
            r=subprocess.run([sys.executable,'-O','-m','holco_finance_controls.conformance','--check',str(p)],capture_output=True,text=True)
            self.assertEqual(r.returncode,1);self.assertEqual(json.loads(r.stdout)['passed'],0)
            p.write_text('{')
            r=subprocess.run([sys.executable,'-m','holco_finance_controls.conformance','--check',str(p)],capture_output=True)
            self.assertEqual(r.returncode,2)

    def test_catalogue_has_stable_ids_and_actual_reference_tests(self):
        root=Path(__file__).resolve().parents[1]
        rows=json.loads((root/'spec/control-catalog.json').read_text())['controls']
        self.assertEqual([r['id'] for r in rows],[f'HFC-{i:03}' for i in range(1,41)])
        for row in rows:
            if row['implementation']=='reference':
                path,method=row['verification'].split(':')
                self.assertIn('def '+method+'(',(root/path).read_text())
            else:self.assertEqual(row['implementation'],'host');self.assertIsNone(row['verification'])

    def test_versioned_spec_manifest_identifies_exact_documents(self):
        root=Path(__file__).resolve().parents[1]
        manifest=json.loads((root/'spec/protocol-release.json').read_text())
        self.assertEqual(manifest['protocol_version'],'1.3.0')
        for name,digest in manifest['documents'].items():
            self.assertEqual(hashlib.sha256((root/name).read_bytes()).hexdigest(),digest)
