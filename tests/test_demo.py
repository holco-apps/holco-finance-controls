import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from holco_finance_controls.demo import walkthrough, require


class DemoTests(unittest.TestCase):
    def test_walkthrough_preserves_failure_and_never_approves(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'demo'
            summary = walkthrough(path)
            self.assertEqual([s['actual'] for s in summary['stages']], ['INCONCLUSIVE', 'FAIL', 'PASS', 'REVIEW'])
            failed = json.loads((path / 'report-failed.json').read_text())
            fixed = json.loads((path / 'report-corrected.json').read_text())
            self.assertEqual(fixed['supersedes'], failed['run_id'])
            self.assertIsNone(fixed['review'])
            self.assertNotEqual(fixed['plan']['sources'][0]['sha256'], failed['plan']['sources'][0]['sha256'])
            with self.assertRaises(FileExistsError):
                walkthrough(path)

    def test_cli_json_is_readable_by_other_languages(self):
        with tempfile.TemporaryDirectory() as directory:
            completed = subprocess.run([sys.executable, '-m', 'holco_finance_controls.demo',
                '--output', str(Path(directory) / 'demo'), '--format', 'json'],
                capture_output=True, text=True, check=True, timeout=30)
            report = json.loads(completed.stdout)
            self.assertEqual(report['acceptance'], 'PASS')
            self.assertFalse(report['human_approval_recorded'])

    def test_acceptance_gate_is_not_a_python_assert(self):
        with self.assertRaises(RuntimeError):
            require(False, 'intentional negative case')
