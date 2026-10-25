#!/usr/bin/env python3
"""Opt-in LIVE provider smoke tests using ONLY four built-in fictional §5 fixtures.

This script NEVER accepts an external case-file path or claimant-entered facts.
No full AI responses are logged or saved.  All results are REQUIRES HUMAN REVIEW.
"""
from __future__ import annotations
import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT/'tests'))

from app.engine import validate
from app.controlled_ai import (controlled_draft, configured_provider,
    provider_is_configured, AIUnavailable, DraftRejected)
from test_engine import fixture


def synthetic_cases() -> list[tuple[str,dict[str,Any]]]:
    """Trusted in-repository fictional sample only, not user-supplied case data."""
    first=fixture(status=1,urgency=False)
    second=fixture(status=2,urgency=True)
    third=fixture(status=3,urgency=False)
    fourth=fixture(status=1,urgency=False,filing_date='2027-08-01')
    return [('S01_OBSTRUCTION_EXISTS',first),
            ('S02_PARTIALLY_REMOVED_URGENT',second),
            ('S03_REMOVED_INJUNCTION_ONLY',third),
            ('S04_LIMITATION_REVIEW_ONLY',fourth)]


def inspect_candidate(data:dict[str,Any], result:dict[str,Any]) -> list[str]:
    issues=[]
    paras=result['paragraphs']
    no=[p['number'] for p in paras]
    if no!=sorted(set(no)):
        issues.append('paragraph numbering/order changed')
    if 12 not in no or 13 not in no:
        issues.append('required paragraphs absent')
    if data['status']==3:
        if [p['master_prayer_id'] for p in result['prayers']] != ['PR-3']:
            issues.append('status3 prayer mismatch')
    if data['status']==2 and data.get('urgent_hearing') is True:
        if not any(p['master_prayer_id']=='PR-4' for p in result['prayers']):
            issues.append('affirmative urgent hearing missing')
    if data['filing_date']=='2027-08-01':
        if result['limitation']['mode']!='REVIEW_ONLY':
            issues.append('late filing wrongly marked acceptable')
        if any('विहित मुदतीत' in p['text'] for p in paras):
            issues.append('unsupported within-limitation statement')
    return issues


def main(argv:list[str]|None=None)->int:
    parser=argparse.ArgumentParser(description='§5: LIVE AI on FOUR BUILT-IN SYNTHETIC cases only')
    parser.add_argument('--live-synthetic-only',action='store_true',
        help='Explicitly allow API charges and limited fictional route facts to be sent')
    args=parser.parse_args(argv)
    if not args.live_synthetic_only:
        print('BLOCKED: must specify --live-synthetic-only (no network request).')
        return 2
    if os.getenv('MC5_LIVE_SYNTHETIC_TEST_APPROVED')!='YES':
        print('BLOCKED: set MC5_LIVE_SYNTHETIC_TEST_APPROVED=YES (no network request).')
        return 2
    if not provider_is_configured():
        print('NOT RUN: AI model/provider/key/operator opt-in missing; no network request.')
        return 3
    provider=configured_provider()
    rows=[]
    for label, raw in synthetic_cases():
        try:
            data=validate(raw)
            draft=controlled_draft(raw,provider,user_consented=True)
            issues=inspect_candidate(data,draft)
            outcome='NEEDS_HUMAN_REVIEW' if not issues else 'REJECTED_INTERNAL_QA'
            rows.append({'case':label,'outcome':outcome,'issues':issues,
                         'paragraph_count':len(draft['paragraphs']),
                         'mode':draft['limitation']['mode']})
            print(f'{label}: {outcome}; output is NOT filing-ready')
        except (AIUnavailable,DraftRejected) as exc:
            # Error content from validator only. Never log prompt, response or key.
            rows.append({'case':label,'outcome':'REJECTED','issues':[type(exc).__name__]})
            print(f'{label}: REJECTED ({type(exc).__name__}); no unsafe fallback to final Word')
    # Report contains only synthetically named cases, counts, booleans, no draft text.
    report=ROOT/'qa'/'prototype03'/'LIVE_SYNTHETIC_RESULTS_LOCAL_ONLY.json'
    report.parent.mkdir(parents=True,exist_ok=True)
    report.write_text(json.dumps({'notice':'Fictional cases ONLY. Not legal or linguistic approval.',
                                  'results':rows},ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'Sanitized local test record: {report.name}')
    return 0 if all(r['outcome']=='NEEDS_HUMAN_REVIEW' for r in rows) else 1


if __name__=='__main__':
    sys.exit(main())
