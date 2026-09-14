"""Portable golden-verdict conformance, separate from professional certification."""
from __future__ import annotations
import argparse
import hashlib
import json
from importlib.resources import files
from pathlib import Path
from .packs import execute

PROFILE = 'holco.golden-verdict/1'
DOMAINS = ('reconciliation', 'fec', 'cash', 'closing')


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()


def cases():
    out = []
    for domain in DOMAINS:
        doc = json.loads(files('holco_finance_controls').joinpath('conformance_data', domain+'.json').read_text())
        if doc['synthetic'] is not True or not doc['cases']:
            raise ValueError('invalid or empty golden domain')
        out.extend(doc['cases'])
    if len({c['case_id'] for c in out}) != len(out):
        raise ValueError('duplicate golden case IDs')
    return out


def task(case):
    value = {k: case[k] for k in ('case_id', 'pack', 'control_id', 'sources', 'tolerance', 'policy')}
    return dict(value, case_sha256=hashlib.sha256(canonical(value)).hexdigest())


def reference_responses():
    responses = []
    for c in cases():
        result = execute(c['pack'], c['control_id'], [s.encode() for s in c['sources']], c['tolerance'], c['policy'])
        responses.append(dict(case_id=c['case_id'], case_sha256=task(c)['case_sha256'],
                              status=result['status'], observed=result['observed'], expected=result['expected']))
    return dict(profile=PROFILE, implementation='HOLCO public reference', responses=responses)


def check_responses(document):
    if not isinstance(document, dict) or document.get('profile') != PROFILE or not isinstance(document.get('responses'), list):
        raise ValueError('profile and responses list required')
    actual = {}
    for r in document['responses']:
        if not isinstance(r, dict) or not isinstance(r.get('case_id'), str) or r['case_id'] in actual:
            raise ValueError('invalid or duplicate response ID')
        actual[r['case_id']] = r
    expected = cases()
    unknown = set(actual) - {c['case_id'] for c in expected}
    if unknown:
        raise ValueError('unexpected response IDs')
    results = []
    for c in expected:
        r = actual.get(c['case_id'])
        reasons = []
        if r is None:
            reasons.append('missing response')
        else:
            if r.get('case_sha256') != task(c)['case_sha256']:
                reasons.append('input binding differs')
            if r.get('status') != c['expected_status']:
                reasons.append('verdict differs from published oracle')
            if any(k not in r or r[k] is None for k in ('observed', 'expected')):
                reasons.append('evidence fields absent')
        results.append(dict(case_id=c['case_id'], conforms=not reasons, reasons=reasons,
                            expected_status=c['expected_status'], received_status=r.get('status') if r else None))
    return dict(profile=PROFILE, synthetic=True, complete=len(actual)==len(expected),
                conforms=all(r['conforms'] for r in results), planned=len(expected), received=len(actual),
                passed=sum(r['conforms'] for r in results), results=results,
                limits=['Published, synthetic vectors: not an unseen accuracy benchmark.',
                        'Checks verdict, input binding and presence of evidence, not the truth of arbitrary evidence.',
                        'No ERP provenance, authenticated human identity, fiscal compliance or certification established.'])


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    mode=p.add_mutually_exclusive_group(required=True)
    mode.add_argument('--tasks',action='store_true',help='emit portable JSON inputs, excluding oracle answers')
    mode.add_argument('--reference',action='store_true',help='execute the public reference and emit its responses')
    mode.add_argument('--self-test',action='store_true',help='check the reference against independent published oracles')
    mode.add_argument('--check',type=Path,help='check another implementation responses JSON')
    args=p.parse_args(argv)
    try:
        if args.tasks:
            out=dict(profile=PROFILE,tasks=[task(c) for c in cases()])
        elif args.reference:
            out=reference_responses()
        else:
            if args.check and args.check.stat().st_size>2_000_000:
                raise ValueError('response file exceeds 2 MB')
            out=check_responses(json.loads(args.check.read_text()) if args.check else reference_responses())
        print(json.dumps(out,indent=2,sort_keys=True,allow_nan=False))
        return 0 if out.get('conforms',True) else 1
    except (OSError,ValueError,KeyError,TypeError) as exc:
        p.error(str(exc))


if __name__=='__main__':
    raise SystemExit(main())
