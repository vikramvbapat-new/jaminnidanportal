"""Safety: the human gate cannot falsely approve offline fake, incomplete or tampered runs."""
import csv
import hashlib
import json
from pathlib import Path
from scripts.verify_human_acceptance import CASES, RUBRIC, evaluate
from scripts.live_ai_acceptance_review import go

DATE='2026-10-24'
CODE='DEV_REVIEWER'

def write_fixture(folder:Path, *, live:bool=True, passed:bool=True,changed:int=1):
 folder.mkdir(parents=True,exist_ok=True)
 results=[]
 for case in CASES:
  hashed={}
  for suffix,key in [('_REVIEW_ONLY.docx','word_sha256'),('_PARAGRAPH_COMPARISON.docx','comparison_sha256')]:
   content=(case+suffix).encode()*60
   p=folder/(case+suffix);p.write_bytes(content)
   hashed[key]=hashlib.sha256(content).hexdigest()
  results.append({'case':case,'status':'STRUCTURAL_OK_HUMAN_REVIEW_PENDING',
   'review_only':True,'word_exported':True,'rewritten_changed_paragraphs':changed,
   'paragraphs':3,'paragraph_numbers':[1,12,13],
   'linguistic_approval':False,'legal_approval':False,**hashed})
 (folder/'SUMMARY.json').write_text(json.dumps({'run_mode':'LIVE_PROVIDER_SYNTHETIC_ONLY' if live else 'OFFLINE_FAKE_ZERO_NETWORK',
 'review_artifacts_exported':True,'results':results}),encoding='utf-8')
 with (folder/'HUMAN_SCORECARD.csv').open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=['case','criterion','check','human_result','reviewer_notes']);w.writeheader()
  for case in CASES:
   for criterion,descr in RUBRIC:
    w.writerow({'case':case,'criterion':criterion,'check':descr,
     'human_result':'PASS' if passed else 'NOT_REVIEWED','reviewer_notes':''})
 with (folder/'PARAGRAPH_SCORECARD.csv').open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=['case','paragraph_number','subject','source_field_ids','human_result','reviewer_notes']);w.writeheader()
  for case in CASES:
   for paragraph_no in (1,12,13):
    w.writerow({'case':case,'paragraph_number':paragraph_no,'subject':'Synthetic test paragraph',
     'source_field_ids':'MC5_STATUS','human_result':'PASS' if passed else 'NOT_REVIEWED','reviewer_notes':''})

def test_offline_fake_always_denied(tmp_path):
 f=tmp_path/'live_synthetic_local_only';write_fixture(f,live=False)
 result=evaluate(f,reviewer_code=CODE,review_date=DATE)
 assert result['status']=='BLOCKED' and any('Not a live' in e for e in result['problems'])

def test_incomplete_review_denied(tmp_path):
 f=tmp_path/'live_synthetic_local_only';write_fixture(f,passed=False)
 assert evaluate(f,reviewer_code=CODE,review_date=DATE)['status']=='BLOCKED'

def test_success_simulated_parser_only(tmp_path):
 f=tmp_path/'live_synthetic_local_only';write_fixture(f)
 result=evaluate(f,reviewer_code=CODE,review_date=DATE)
 assert result['status']=='SYNTHETIC_LINGUISTIC_REVIEW_COMPLETED_NOT_PRODUCTION_APPROVED'
 assert result['checked_criteria']==36 and result['verified_artifact_count']==8

def test_review_doc_tamper_denied(tmp_path):
 f=tmp_path/'live_synthetic_local_only';write_fixture(f)
 p=f/(CASES[0]+'_REVIEW_ONLY.docx');p.write_bytes(p.read_bytes()+b'tamper')
 r=evaluate(f,reviewer_code=CODE,review_date=DATE)
 assert r['status']=='BLOCKED' and any('modified' in s for s in r['problems'])

def test_no_actual_rewrite_denied(tmp_path):
 f=tmp_path/'live_synthetic_local_only';write_fixture(f,changed=0)
 r=evaluate(f,reviewer_code=CODE,review_date=DATE)
 assert r['status']=='BLOCKED' and any('No AI paragraph changes' in s for s in r['problems'])

def test_missing_reviewer_or_date_denied(tmp_path):
 f=tmp_path/'live_synthetic_local_only';write_fixture(f)
 assert evaluate(f)['status']=='BLOCKED'
 assert evaluate(f,reviewer_code=CODE,review_date='2100-01-01')['status']=='BLOCKED'

def test_duplicate_or_extra_row_denied(tmp_path):
 f=tmp_path/'live_synthetic_local_only';write_fixture(f)
 p=f/'HUMAN_SCORECARD.csv'
 with p.open('a',encoding='utf-8') as stream:stream.write(f'{CASES[0]},SOURCE,duplicate,PASS,\n')
 assert evaluate(f,reviewer_code=CODE,review_date=DATE)['status']=='BLOCKED'

def test_wrong_case_status_denied(tmp_path):
 f=tmp_path/'live_synthetic_local_only';write_fixture(f)
 p=f/'SUMMARY.json';s=json.loads(p.read_text(encoding='utf-8'))
 s['results'][0]['status']='REJECTED_OR_PROVIDER_FAILED';p.write_text(json.dumps(s))
 assert evaluate(f,reviewer_code=CODE,review_date=DATE)['status']=='BLOCKED'

def test_word_hashes_present_on_offline_export():
 assert go(['--offline-fake','--export-review-artifacts'])==0
 f=Path(__file__).resolve().parents[1]/'qa/live_acceptance/offline_fake'
 summary=json.loads((f/'SUMMARY.json').read_text(encoding='utf-8'))
 for r in summary['results']:
  assert len(r['word_sha256'])==64 and len(r['comparison_sha256'])==64
  assert len(r['paragraph_numbers'])==r['paragraphs']
 assert (f/'PARAGRAPH_SCORECARD.csv').is_file()


def test_missing_paragraph_review_denied(tmp_path):
 f=tmp_path/'live_synthetic_local_only';write_fixture(f)
 (f/'PARAGRAPH_SCORECARD.csv').unlink()
 assert evaluate(f,reviewer_code=CODE,review_date=DATE)['status']=='BLOCKED'
