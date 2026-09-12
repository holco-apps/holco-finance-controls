import io,json,unittest,zipfile
from pathlib import Path
from decimal import Decimal
from xml.sax.saxutils import escape
from holco_finance_controls.engine import Engine
from holco_finance_controls.financial_workbook import discover,control

CONTEXT={'schema':'holco.control-context/1','company_id':'example','profile':[],'memory':[], 'rules':[], 'drafts':[]}

def fixture(ambiguous=False,missing=False):
    cells={}
    def text(a,t):cells[a]=f'<c r="{a}" t="inlineStr"><is><t>{escape(t)}</t></is></c>'
    def num(a,n,formula=None,style=0):cells[a]=f'<c r="{a}" s="{style}">'+(f'<f>{escape(formula)}</f>' if formula is not None else '')+('' if n is None else f'<v>{n}</v>')+'</c>'
    labels={6:"Chiffre d'affaires",7:'Brand Content',13:'Coûts directs',30:'Marge brute',33:'G&A',45:'EBITDA',46:"% Chiffre d'affaires",48:'Reprises & dotations',49:'Résultat financier',50:'Production immobilisée',52:'RCAI',55:'Résultat exceptionnel',56:'Impôts sur les bénéfices',62:'Résultat net'}
    for r,label in labels.items():text('B'+str(r),label)
    for col in ['E','F']+(['G'] if ambiguous else []):
        text(col+'2','YTD');text(col+'3','Budget' if col=='F' else 'Réel');text(col+'4','2026-07-31')
        vals={6:1000,7:1000,13:-400,30:600,33:-200,45:400,46:.4,48:-20,49:-30,50:0,52:350.4,55:0,56:0,62:350.4}
        if col=='F':vals[6]=2000;vals[7]=2000
        for r,value in vals.items():num(col+str(r),None if missing and r==48 else value,'SUM('+col+'45:'+col+'51)' if r==52 else None,1 if r==46 else 0)
    rows={}
    import re
    for a,c in cells.items():rows.setdefault(int(re.search(r'\d+',a)[0]),[]).append(c)
    sheet='<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>'+''.join(f'<row r="{r}">'+''.join(cs)+'</row>' for r,cs in sorted(rows.items()))+'</sheetData></worksheet>'
    files={'xl/workbook.xml':'<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="P&amp;L" sheetId="1" r:id="r1"/></sheets></workbook>', 'xl/_rels/workbook.xml.rels':'<Relationships><Relationship Id="r1" Target="worksheets/sheet1.xml"/></Relationships>', 'xl/worksheets/sheet1.xml':sheet, 'xl/styles.xml':'<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><cellXfs><xf numFmtId="0"/><xf numFmtId="9"/></cellXfs></styleSheet>'}
    out=io.BytesIO()
    with zipfile.ZipFile(out,'w') as z:
        for path,text in files.items():z.writestr(path,text)
    return out.getvalue()

class FinancialWorkbookTest(unittest.TestCase):
    def changed(self, raw, transform):
        out=io.BytesIO()
        with zipfile.ZipFile(io.BytesIO(raw)) as source, zipfile.ZipFile(out,'w') as target:
            for name in source.namelist():
                text=source.read(name).decode()
                target.writestr(name,transform(text) if name=='xl/worksheets/sheet1.xml' else text)
        return out.getvalue()

    def test_shared_sum_is_expanded_and_preserves_cell_location(self):
        raw=self.changed(fixture(),lambda s:s.replace('<f>SUM(E45:E51)</f>','<f t="shared" si="1" ref="E52:F52">SUM(E45:E51)</f>').replace('<f>SUM(F45:F51)</f>','<f t="shared" si="1"/>'))
        r=control('formula_units',[raw,json.dumps(CONTEXT).encode()],Decimal('.01'),{'required_period':'2026'})
        target=next(c for c in r['observed']['checks'] if c['location']=='P&L!F52')
        self.assertEqual(target['observed']['formule'],'SUM(F45:F51)')
        self.assertEqual(target['observed']['cellules_pourcentages'],['F46'])

    def test_month_and_ytd_with_same_end_date_are_not_compared(self):
        raw=self.changed(fixture(True),lambda s:s.replace('<c r="G2" t="inlineStr"><is><t>YTD</t></is></c>','<c r="G2" t="inlineStr"><is><t>Monthly</t></is></c>'))
        self.assertEqual(discover(raw,'2026')['selected']['id'],'P&L|E|F')

    def test_merged_ytd_header_is_read_without_guessing_neighbor_cells(self):
        raw=self.changed(fixture(),lambda s:s.replace('<c r="F2" t="inlineStr"><is><t>YTD</t></is></c>','').replace('</worksheet>','<mergeCells><mergeCell ref="E2:F2"/></mergeCells></worksheet>'))
        self.assertEqual(discover(raw,'2026')['selected']['period_kind'],'ytd')

    def test_scope_ratio_label_is_not_duplicate_revenue(self):
        scope=discover(fixture(),'2026')
        self.assertEqual(scope['selected']['actual'],'E')
        self.assertEqual(scope['selected']['rows']['revenue'],6)
        self.assertEqual(scope['selected']['rows']['line_7'],7)
        self.assertIsNone(discover(fixture(),'2025')['selected'])
    def test_ambiguous_mapping_requires_choice_and_invalid_choice_rejected(self):
        scope=discover(fixture(True),'2026');self.assertTrue(scope['requires_selection'])
        self.assertEqual(discover(fixture(True),'2026','P&L|G|F')['selected']['actual'],'G')
        with self.assertRaises(ValueError):discover(fixture(),'2026','other|E|F')
        e=Engine(Path(':memory:'));self.addCleanup(e.close)
        ids=[e.register(r)['source_id'] for r in [fixture(True),json.dumps(CONTEXT).encode()]]
        p=e.plan(ids,'financial_workbook',policy={'required_period':'2026'})
        with self.assertRaisesRegex(ValueError,'choose a financial comparison'):
            e.start(p['plan_id'],p['plan_sha256'])
    def test_monetary_sum_with_ratio_and_small_difference_not_suppressed(self):
        src=[fixture(),json.dumps(CONTEXT).encode()]
        units=control('formula_units',src,Decimal('.01'),{'required_period':'2026'})
        self.assertEqual(units['status'],'FAIL')
        self.assertIn('E46',units['observed']['checks'][0]['observed']['cellules_pourcentages'])
        eq=control('financial_equations',src,Decimal('.01'),{'required_period':'2026'})
        check=next(c for c in eq['observed']['checks'] if c['id']=='equation:E52')
        self.assertEqual(check['observed']['écart'],'0.4');self.assertEqual(check['status'],'FAIL')
    def test_missing_numeric_evidence_never_zero_filled(self):
        eq=control('financial_equations',[fixture(missing=True),json.dumps(CONTEXT).encode()],Decimal('.01'),{'required_period':'2026'})
        self.assertEqual(next(c for c in eq['observed']['checks'] if c['id']=='equation:E52')['status'],'INCONCLUSIVE')
    def test_all_variances_kept_and_context_is_not_execution_proof(self):
        ctx={**CONTEXT,'rules':[{'id':17,'version':2,'text':'Rapprocher la paie','title':'Paie'}], 'drafts':[{'id':18,'version':1,'text':'Brouillon'}]}
        src=[fixture(),json.dumps(ctx).encode()]
        review=control('context_review',src,Decimal('.01'),{'required_period':'2026'})
        self.assertEqual(len(review['observed']['checks']),1);self.assertEqual(review['status'],'INCONCLUSIVE')
        variations=control('analytical_variances',src,Decimal('.01'),{'required_period':'2026'})
        c=next(c for c in variations['observed']['checks'] if c['id']=='variance:line_7')
        self.assertEqual(c['observed']['écart'],'-1000')
    def test_persistent_engine_binds_workbook_and_context(self):
        e=Engine(Path(':memory:'));self.addCleanup(e.close)
        ids=[e.register(raw)['source_id'] for raw in [fixture(),json.dumps(CONTEXT).encode()]]
        p=e.plan(ids,'financial_workbook',policy={'required_period':'2026'})
        self.assertEqual(len(p['sources']),2)
        r=e.start(p['plan_id'],p['plan_sha256']);r=e.advance(r['run_id'],6)
        self.assertTrue(r['complete']);self.assertEqual(r['deterministic_outcome'],'FAIL')
