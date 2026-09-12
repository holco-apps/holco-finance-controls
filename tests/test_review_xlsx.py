import hashlib
import io
import unittest
import zipfile
from pathlib import Path
from holco_finance_controls.engine import Engine
from holco_finance_controls.review_template import template_bytes
from holco_finance_controls.review_xlsx import read_xlsx_review, ReviewFormatError


def changed(files):
    out = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(template_bytes())) as original, zipfile.ZipFile(out, 'w') as target:
        for name in original.namelist():
            text = original.read(name).decode()
            target.writestr(name, files.get(name, lambda s: s)(text))
        for name, value in files.items():
            if name not in original.namelist():
                target.writestr(name, value(''))
    return out.getvalue()


class ReviewXlsxTest(unittest.TestCase):
    def test_actual_template_exact_amounts_scope_and_original_proof(self):
        raw = template_bytes()
        self.assertEqual(raw, template_bytes())
        engine = Engine(Path(':memory:'))
        self.addCleanup(engine.close)
        source = engine.register(raw)
        with self.assertRaisesRegex(ValueError, 'explicit worksheet scope'):
            engine.plan([source['source_id']], 'dossier_review', policy={'required_period':'2025','required_currency':'EUR'})
        plan = engine.plan([source['source_id']], 'dossier_review_xlsx', policy={'required_period':'2025','required_currency':'EUR'})
        self.assertEqual(source['sha256'], hashlib.sha256(raw).hexdigest())
        self.assertEqual(plan['review_scope']['excluded_sheets'], ['Mode emploi'])
        self.assertEqual(plan['review_scope']['range'], 'A1:H4')
        run = engine.start(plan['plan_id'], plan['plan_sha256'])
        report = engine.advance(run['run_id'], 5)
        self.assertEqual(report['deterministic_outcome'], 'FAIL')
        checks = report['results'][1]['observed']['checks']
        self.assertEqual(checks[1]['observed'], '41000')
        self.assertEqual(checks[1]['expected'], '42000')
        self.assertIn('Revue HOLCO!A3:H3', checks[1]['location'])
        self.assertEqual(report['results'][3]['status'], 'FAIL')

    def test_cached_formula_cannot_become_verified_input(self):
        for cached in ['<v>42000</v>', '']:
            raw = changed({'xl/worksheets/sheet1.xml': lambda s: s.replace('<c r="D3"><v>42000</v></c>', f'<c r="D3"><f>C3+12000</f>{cached}</c>')})
            with self.assertRaisesRegex(ReviewFormatError, 'formules'):
                read_xlsx_review(raw)

    def test_shared_strings_and_hidden_rows_keep_original_location(self):
        raw = changed({
            'xl/worksheets/sheet1.xml': lambda s: s.replace('<c r="A2" t="inlineStr" s="0"><is><t xml:space="preserve">Ventes</t></is></c>', '<c r="A2" t="s"><v>0</v></c>').replace('<row r="3">', '<row r="3" hidden="1">'),
            'xl/sharedStrings.xml': lambda _: '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><si><r><t>Ven</t></r><r><t>tes</t></r></si></sst>'})
        rows, scope = read_xlsx_review(raw)
        self.assertEqual(rows[0]['poste'], 'Ventes')
        self.assertEqual(rows[1]['line'], 3)
        self.assertEqual(len(rows), 3)
        self.assertTrue(scope['hidden_rows_included'])

    def test_unrecognized_workbook_falls_back_but_invalid_named_table_does_not(self):
        raw = changed({'xl/workbook.xml':lambda s:s.replace('Revue HOLCO', 'Bilan')})
        self.assertIsNone(read_xlsx_review(raw, required=False))
        for transform in [lambda s:s.replace('Montant expliqué', 'Montant'),
                          lambda s:s.replace('</worksheet>', '<mergeCells count="1"><mergeCell ref="A2:B2"/></mergeCells></worksheet>'),
                          lambda s:s.replace('r="D3"', 'r="I3"'),
                          lambda s:s.replace('<c r="D3"><v>42000</v></c>', '<c r="D3" t="e"><v>#REF!</v></c>')]:
            with self.assertRaises(ValueError):
                read_xlsx_review(changed({'xl/worksheets/sheet1.xml':transform}), required=False)

    def test_missing_value_is_preserved_not_replaced_by_zero(self):
        raw = changed({'xl/worksheets/sheet1.xml':lambda s:s.replace('<c r="D3"><v>42000</v></c>', '')})
        rows, _ = read_xlsx_review(raw)
        self.assertIsNone(rows[1]['n'])

    def test_shared_string_xml_and_hidden_review_are_rejected(self):
        for files in [
            {'xl/sharedStrings.xml':lambda _: '<!DOCTYPE s [<!ENTITY x "boom">]><sst/>'},
            {'xl/workbook.xml':lambda s:s.replace('name="Revue HOLCO"', 'name="Revue HOLCO" state="hidden"')},
            {'xl/worksheets/sheet1.xml':lambda s:s.replace('<c r="A2" t="inlineStr" s="0"><is><t xml:space="preserve">Ventes</t></is></c>', '<c r="A2" t="s"><v>-1</v></c>')},
        ]:
            with self.assertRaises(ValueError):
                read_xlsx_review(changed(files))
