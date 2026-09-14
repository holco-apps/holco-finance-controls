"""Machine-readable input descriptions; no implicit connector or human authority."""
from copy import deepcopy

SNAPSHOT = dict(format='JSON', required=['workbook', 'sheet', 'scope', 'captured_at', 'cells'],
    cells='1..10000 objects: address, scalar value, formula (string or null), error (string or null). Missing observations are inconclusive.',
    checks='Optional checks: [{id,target,terms:[{address,coefficient:"1"}]}]. Only declared weighted sums are tested.')
REVIEW_COLUMNS = ['poste', 'periode', 'n_1', 'n', 'reporting', 'explication', 'montant_explique', 'piece']
XLSX = dict(format='OOXML XLSX', encoding='base64', limitations='Stored values only; no formula recalculation or macros.')


def input_contracts():
    """Return a fresh description, preserving caller isolation."""
    def contract(sources, required=None, **extra):
        return dict(source_count=len(sources), sources=sources, required_policy=required or {}, **extra)
    def source(role, spec):
        return dict(role=role, **deepcopy(spec))
    snapshot_policy = dict(objective='nonempty string', required_period='nonempty string', required_scope='nonempty string')
    review_policy = dict(required_period='nonempty string', required_currency='EUR')
    return {
        'reconciliation_csv': contract([source('expected_and_observed', dict(format='UTF-8 CSV', columns=['id','expected','observed'], limits=dict(rows=100000), amounts='finite decimal strings; unique nonempty IDs'))]),
        'fec_tsv': contract([source('journal_entries', dict(format='UTF-8 TSV', columns=['JournalCode','EcritureNum','EcritureDate','Debit','Credit'], dates='YYYYMMDD', amounts='finite decimal strings, nonnegative; debit and credit cannot both be nonzero', limits=dict(rows=100000)))]),
        'workbook_xlsx': contract([source('workbook', XLSX)]),
        'workbook_comparison': contract([source('before', XLSX), source('after', XLSX)]),
        'excel_snapshot': contract([source('observed_sheet', SNAPSHOT)], snapshot_policy),
        'excel_reconciliation': contract([
            source('left', dict(**SNAPSHOT, comparisons='Required for meaningful checks: [{id,left:"A1",right:"B1"}]; stored in this left snapshot. Maximum 500.')),
            source('right', SNAPSHOT)], snapshot_policy, constraints='Two distinct source IDs; no same-workbook same-sheet same-address self comparison.'),
        'dossier_review': contract([source('review_table', dict(format='UTF-8 semicolon CSV', columns_in_exact_order=REVIEW_COLUMNS, limits=dict(rows=2000, field_characters=2000)))], review_policy),
        'dossier_review_xlsx': contract([source('review_workbook', dict(**XLSX, worksheet='Revue HOLCO', headers=['Poste','Exercice','N-1','N','Reporting','Explication','Montant expliqué','Pièce'], constraints='Unique visible worksheet with this name; unmerged review cells.'))], review_policy),
        'financial_workbook': contract([source('original_workbook', XLSX), source('control_context', dict(format='JSON', schema='holco.control-context/1', required_lists=['profile','memory','rules','drafts'], maximum_items_per_list=500, minimal_example=dict(schema='holco.control-context/1', profile=[], memory=[], rules=[], drafts=[]), limitations='Free-text context is recorded for human review, not automatically interpreted as executable rules.'))], dict(required_period='nonempty string'), optional_policy=dict(pnl_mapping='explicit mapping name, maximum 200 characters')),
        'erp_agent_response': contract([
            source('independent_erp_snapshot', dict(format='JSON', records='[{id,amount:decimal string,currency,period}]', coverage='{complete:boolean,next_cursor:null or string,expected_records:integer}', tool_calls='[{name,operation:"read",status:"success"}]')),
            source('agent_answer', dict(format='JSON', claims='[{id,amount:decimal string,currency,period,scope:"selected_records" or "all_period_records",record_ids:[id]}]'))],
            policy_for_conclusive_checks=dict(required_period='nonempty string', required_currency='nonempty string', required_scope='selected_records or all_period_records', allowed_tools='nonempty list of read-only tool names', required_tools='list of required tool names'),
            limitations='Planning accepts missing policy, but affected controls are INCONCLUSIVE. Trusted capture receipt must be registered outside MCP; client declarations do not establish provenance.'),
    }
