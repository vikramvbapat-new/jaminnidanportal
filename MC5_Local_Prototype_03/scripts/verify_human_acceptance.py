#!/usr/bin/env python3
"""Fail-closed local reviewer gate for FOUR FICTIONAL §5 AI cases.

Never invokes the model or handles real case inputs. Verifies reviewer scores,
exported DOCX integrity, structured QA result status, and audit completeness.
A successful result is **synthetic language QA**, NEVER legal or production approval.
"""
from __future__ import annotations

import argparse
import csv
from datetime import date
import hashlib
import json
import os
from pathlib import Path
import re
import sys

from scripts.live_ai_acceptance_review import RUBRIC

CASES=(
 'S01_OBSTRUCTION_EXISTS',
 'S02_PARTIALLY_REMOVED_URGENT',
 'S03_REMOVED_INJUNCTION_ONLY',
 'S04_LIMITATION_REVIEW_ONLY',
)
EXPECTED={(case,criterion) for case in CASES for criterion,_ in RUBRIC}
ALLOWED_RESULTS={'PASS','FAIL','CORRECTION_REQUIRED','NOT_REVIEWED'}
MAX_INPUT_BYTES=500_000


def sha256(path:Path)->str:
 return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_json(path:Path)->dict:
 if not path.is_file() or path.stat().st_size>MAX_INPUT_BYTES:
  raise ValueError(f'Missing or oversized summary: {path.name}')
 data=json.loads(path.read_text(encoding='utf-8'))
 if type(data) is not dict:
  raise ValueError('Summary must be JSON object.')
 return data


def evaluate(folder:Path, *, reviewer_code:str='',review_date:str='')->dict:
 """Validate local LIVE synthetic artifacts; no calls, no file modifications."""
 problems=[]
 if folder.name!='live_synthetic_local_only':
  problems.append('Only genuine live_synthetic_local_only output can enter live QA gate.')
 try:
  summary=_read_json(folder/'SUMMARY.json')
 except (ValueError,OSError,json.JSONDecodeError) as exc:
  return {'status':'BLOCKED','problems':[str(exc)],'checks':0}
 if summary.get('run_mode')!='LIVE_PROVIDER_SYNTHETIC_ONLY':
  problems.append('Not a live synthetic provider run.')
 if summary.get('review_artifacts_exported') is not True:
  problems.append('Exported comparison and Word documents are required.')
 results=summary.get('results')
 if type(results) is not list or len(results)!=4:
  problems.append('Four source cases required.')
  results=[]
 if [x.get('case') for x in results if isinstance(x,dict)]!=list(CASES):
  problems.append('Fixed four case labels/order mismatch.')
 total_changes=0
 expected_paragraphs=set()
 for x in results:
  if not isinstance(x,dict):
   problems.append('Invalid case result object.');continue
  if x.get('status')!='STRUCTURAL_OK_HUMAN_REVIEW_PENDING':
   problems.append(f'{x.get("case","?")}: failed structural check.')
  if x.get('review_only') is not True or x.get('word_exported') is not True:
   problems.append(f'{x.get("case","?")}: not an exported review-only Word result.')
  if x.get('linguistic_approval') is not False or x.get('legal_approval') is not False:
   problems.append('Summary must NOT claim automated linguistic/legal approval.')
  numbers=x.get('paragraph_numbers')
  if (type(numbers) is not list or not numbers or any(type(n) is not int or n<1 or n>13 for n in numbers)
      or numbers!=sorted(set(numbers)) or 12 not in numbers or 13 not in numbers
      or len(numbers)!=x.get('paragraphs')):
   problems.append(f'{x.get("case","?")}: invalid paragraph set/order.')
  else:
   expected_paragraphs.update((x['case'],str(n)) for n in numbers)
  changed=x.get('rewritten_changed_paragraphs')
  if type(changed) is not int or changed<0:
   problems.append(f'{x.get("case","?")}: invalid changed paragraph count.')
  else:total_changes+=changed
  case=x.get('case','')
  if case not in CASES:continue
  for name,key in ((f'{case}_REVIEW_ONLY.docx','word_sha256'),
                   (f'{case}_PARAGRAPH_COMPARISON.docx','comparison_sha256')):
   artifact=folder/name
   if not artifact.is_file() or artifact.is_symlink() or artifact.stat().st_size<500:
    problems.append(f'Missing/invalid review artifact: {name}')
   elif not re.fullmatch(r'[a-f0-9]{64}',str(x.get(key,''))):
    problems.append(f'Missing integrity binding for {name}: rerun with updated acceptance runner.')
   elif sha256(artifact)!=x[key]:
    problems.append(f'Artifact modified after AI generation: {name}')
 if total_changes==0:
  problems.append('No AI paragraph changes in any scenario; no live linguistic rewriting demonstrated.')
 scorepath=folder/'HUMAN_SCORECARD.csv'
 try:
  if not scorepath.is_file() or scorepath.stat().st_size>MAX_INPUT_BYTES:
   raise ValueError('Scorecard missing or oversized.')
  with scorepath.open(encoding='utf-8-sig',newline='') as f:
   reader=csv.DictReader(f)
   if reader.fieldnames != ['case','criterion','check','human_result','reviewer_notes']:
    raise ValueError('Scorecard headers do not match expected format.')
   rows=list(reader)
  seen=set()
  for row in rows:
   key=(row['case'],row['criterion'])
   if key not in EXPECTED or key in seen:
    problems.append(f'Unexpected or duplicate scorecard row: {key}')
   seen.add(key)
   if row['human_result'] not in ALLOWED_RESULTS:
    problems.append(f'Invalid result for {key}')
   elif row['human_result']!='PASS':
    problems.append(f'{key}: {row["human_result"]}')
   if row['human_result'] in ('FAIL','CORRECTION_REQUIRED') and not row['reviewer_notes'].strip():
    problems.append(f'{key}: rejection must explain correction needed.')
  if seen!=EXPECTED or len(rows)!=len(EXPECTED):
   problems.append(f'Incomplete scorecard: {len(seen)}/{len(EXPECTED)} criteria.')
 except (OSError,UnicodeError,ValueError,csv.Error) as exc:
  problems.append(f'Scorecard invalid: {exc}')
 paragraph_path=folder/'PARAGRAPH_SCORECARD.csv'
 try:
  if not paragraph_path.is_file() or paragraph_path.stat().st_size>MAX_INPUT_BYTES:
   raise ValueError('Paragraph-level scorecard missing or oversized.')
  with paragraph_path.open(encoding='utf-8-sig',newline='') as f:
   reader=csv.DictReader(f)
   if reader.fieldnames!=['case','paragraph_number','subject','source_field_ids','human_result','reviewer_notes']:
    raise ValueError('Paragraph scorecard headers invalid.')
   paragraph_rows=list(reader)
  seen_paragraphs=set()
  for row in paragraph_rows:
   pair=(row['case'],row['paragraph_number'])
   if pair not in expected_paragraphs or pair in seen_paragraphs:
    problems.append(f'Unexpected or duplicate paragraph review row: {pair}')
   seen_paragraphs.add(pair)
   if row['human_result'] not in ALLOWED_RESULTS:
    problems.append(f'Invalid paragraph review result for {pair}')
   elif row['human_result']!='PASS':
    problems.append(f'{pair}: {row["human_result"]}')
  if seen_paragraphs!=expected_paragraphs or len(paragraph_rows)!=len(expected_paragraphs):
   problems.append(f'Incomplete paragraph review: {len(seen_paragraphs)}/{len(expected_paragraphs)} paragraphs.')
 except (OSError,UnicodeError,ValueError,csv.Error) as exc:
  problems.append(f'Paragraph scorecard invalid: {exc}')
 if not re.fullmatch(r'[A-Za-z0-9_-]{4,60}',reviewer_code):
  problems.append('Explicit reviewer code (4–60 ASCII letters/digits/_/-) required.')
 try:
  value=date.fromisoformat(review_date)
  if value>date.today():problems.append('Review date cannot be in the future.')
 except ValueError:problems.append('Explicit ISO YYYY-MM-DD review date required.')
 return {
  'status':'SYNTHETIC_LINGUISTIC_REVIEW_COMPLETED_NOT_PRODUCTION_APPROVED' if not problems else 'BLOCKED',
  'reviewer_code':reviewer_code if not problems else 'NOT_RECORDED',
  'review_date':review_date if not problems else 'NOT_RECORDED',
  'checked_criteria':len(EXPECTED),
  'expected_paragraph_reviews':len(expected_paragraphs),
  'verified_artifact_count':8 if not problems else 0,
  'reviewed_case_count':4 if not problems else 0,
  'changed_paragraphs':total_changes,
  'problems':problems,
  'notice':'For four fictional cases only; NOT approval of legal advice, live user data processing, or production release.'
 }


def main(argv:list[str]|None=None)->int:
 ap=argparse.ArgumentParser(description='Manual live-AI review gate: local fictional cases only.')
 ap.add_argument('--folder',type=Path,default=Path(__file__).resolve().parents[1]/'qa/live_acceptance/live_synthetic_local_only')
 ap.add_argument('--reviewer-code',default='')
 ap.add_argument('--review-date',default='')
 ns=ap.parse_args(argv)
 result=evaluate(ns.folder,reviewer_code=ns.reviewer_code,review_date=ns.review_date)
 # Do not overwrite generated QA evidence or signed drafts. Read-only verification.
 print(json.dumps(result,ensure_ascii=False,indent=2))
 return 0 if not result['problems'] else 2

if __name__=='__main__':raise SystemExit(main())
