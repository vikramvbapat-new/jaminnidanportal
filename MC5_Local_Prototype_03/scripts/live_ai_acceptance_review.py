#!/usr/bin/env python3
"""MC5 §5: four FIXED fictional cases, pairwise comparison & manual acceptance.

No data-file input. No case-uploads. Offline is default mode. Live requires
operator + invocation opt-ins. No key/model/config or user case is saved.
"""
from __future__ import annotations
import argparse, csv, hashlib, json, os, sys
from datetime import date
from io import BytesIO
from pathlib import Path
from typing import Any
from docx import Document
from docx.shared import Pt, Cm

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.live_ai_synthetic_smoke import synthetic_cases, inspect_candidate
from app.engine import validate, make_draft, canonical_hash, create_docx
from app.controlled_ai import controlled_draft, configured_provider, provider_is_configured, AIUnavailable, DraftRejected

class FakeProvider:
 def rewrite(self, req):
  return {'paragraphs':[{'number':x['number'],'text':x['baseline_text']} for x in req['paragraphs']]}

RUBRIC=[
 ('SOURCE','Every statement supported by fictional verified input, no invented route/right/date/witness/loss'),
 ('P02_P10','Road pre-existence facts in P02; evidence only in P10; attached vs available distinct'),
 ('P03','Route direction, pre-obstruction width in feet and optional length, no fabricated village-road connection'),
 ('P07_P08','Direct road use impairment distinct from separately verified concrete hardship'),
 ('P09','Urgency only with verified reasons and independent yes for hearing'),
 ('P12_P13','Cause date, jurisdiction, no unsupported limitation assertion'),
 ('STATUS_PRAYERS','Status 3 has no physical removal prayer; prayers follow governed approved rules'),
 ('MARATHI','Affirmative, natural Marathi pleadings; no template padding/redundancy'),
 ('DOCX','Table and parties correct; annexures attached only, layout clear'),
]

def private_dir(path:Path)->None:
 path.mkdir(parents=True,exist_ok=True)
 try: path.chmod(0o700)
 except OSError:pass

def private_write(path:Path,contents:bytes)->None:
 flags=os.O_WRONLY|os.O_CREAT|os.O_TRUNC
 fd=os.open(path,flags,0o600)
 with os.fdopen(fd,'wb') as f:f.write(contents)
 try:path.chmod(0o600)
 except OSError:pass

def make_comparison(label:str,d:dict, draft:dict, baseline:dict)->bytes:
 """Review-only comparison of *synthetic* case paragraphs, never a legal filing."""
 doc=Document();sec=doc.sections[0];sec.top_margin=Cm(1.7);sec.bottom_margin=Cm(1.7)
 st=doc.styles['Normal'];st.font.name='Noto Sans Devanagari';st.font.size=Pt(9)
 doc.add_heading('कलम ५ — AI परिच्छेद तुलनात्मक परीक्षण',0)
 doc.add_paragraph(f'{label} | केवळ कृत्रिम चाचणी. न्यायालयीन अर्ज किंवा कायदेशीर अभिप्राय नाही.')
 doc.add_paragraph('मूळ = नियमाधारित मजकूर. AI = मॉडेलने प्रस्तावित केलेला मजकूर (स्वयंचलित पडताळणी उत्तीर्ण झालेला असला तरी तथ्यशुद्धता सिद्ध झालेली नाही).')
 doc.add_paragraph(f'अडथळ्याची स्थिती: {d["status"]} | मुदत मोड: {draft["limitation"]["mode"]}')
 base={x['number']:x for x in baseline['paragraphs']}
 for p in draft['paragraphs']:
  n=p['number'];b=base[n]
  doc.add_heading(f'{n}) {p["subject"]}',level=2)
  doc.add_paragraph('तथ्य स्रोत: '+', '.join(p.get('source_field_ids',[])))
  t=doc.add_table(rows=1,cols=2);t.style='Table Grid'
  t.rows[0].cells[0].text='मूळ नियमाधारित मजकूर'
  t.rows[0].cells[1].text='AI प्रस्तावित मजकूर'
  cells=t.add_row().cells;cells[0].text=b['text'];cells[1].text=p['text']
  doc.add_paragraph('मानवी निर्णय: □ स्वीकार्य  □ सुधारणा आवश्यक  □ नकार  |  टीप: __________')
 doc.add_heading('अंतिम मागण्या — AI बदल करू शकत नाही',2)
 for q in draft['prayers']:doc.add_paragraph(f'{q["display_number"]}) {q["text"]}')
 doc.add_paragraph('कायदेशीर ग्राह्यता, तथ्ये, मराठी, मुदत आणि जोडपत्रांची मानवी पडताळणी: बाकी.')
 f=BytesIO();doc.save(f);return f.getvalue()

def go(argv:list[str]|None=None)->int:
 ap=argparse.ArgumentParser(description='MC5 synthetic-only AI acceptance runner. No external case files supported.')
 mode=ap.add_mutually_exclusive_group(required=True)
 mode.add_argument('--offline-fake',action='store_true',help='Zero network, regression of comparison/export')
 mode.add_argument('--live-synthetic-only',action='store_true',help='Potential paid API calls; requires explicit authorizations')
 ap.add_argument('--export-review-artifacts',action='store_true',help='Local DOCX and comparisons; with live requires second opt-in')
 ns=ap.parse_args(argv)
 is_live=ns.live_synthetic_only
 if is_live:
  if os.getenv('MC5_LIVE_SYNTHETIC_TEST_APPROVED')!='YES':
   print('BLOCKED: requires MC5_LIVE_SYNTHETIC_TEST_APPROVED=YES; zero API calls.');return 2
  if ns.export_review_artifacts and os.getenv('MC5_LIVE_REVIEW_EXPORT_APPROVED')!='YES':
   print('BLOCKED: review export requires MC5_LIVE_REVIEW_EXPORT_APPROVED=YES; zero API calls.');return 2
  if not provider_is_configured():
   print('NOT RUN: provider/model/key/operator opt-in missing; zero API calls.');return 3
  provider=configured_provider()
 else:provider=FakeProvider()
 dest=ROOT/'qa'/'live_acceptance'/('live_synthetic_local_only' if is_live else 'offline_fake')
 private_dir(dest)
 results=[];scores=[];paragraph_scores=[]
 for label,raw in synthetic_cases():
  d=validate(raw)
  try:
   draft=controlled_draft(raw,provider,user_consented=True)
   baseline=make_draft(raw)
   problems=inspect_candidate(d,draft)
   if problems:raise DraftRejected(['internal QA check failed'])
   text_changed=sum(base['text']!=p['text'] for base,p in zip(baseline['paragraphs'],draft['paragraphs']))
   state='STRUCTURAL_OK_HUMAN_REVIEW_PENDING'
   artifact_hashes={}
   if ns.export_review_artifacts:
    b=create_docx(raw,canonical_hash(raw),True,draft_override=draft)
    private_write(dest/(label+'_REVIEW_ONLY.docx'),b)
    artifact_hashes['word_sha256']=hashlib.sha256(b).hexdigest()
    comparison=make_comparison(label,d,draft,baseline)
    private_write(dest/(label+'_PARAGRAPH_COMPARISON.docx'),comparison)
    artifact_hashes['comparison_sha256']=hashlib.sha256(comparison).hexdigest()
   for key,description in RUBRIC:
    scores.append({'case':label,'criterion':key,'check':description,'human_result':'NOT_REVIEWED', 'reviewer_notes':''})
   for para in draft['paragraphs']:
    paragraph_scores.append({'case':label,'paragraph_number':para['number'],
      'subject':para['subject'], 'source_field_ids':';'.join(para.get('source_field_ids',[])),
      'human_result':'NOT_REVIEWED','reviewer_notes':''})
   results.append({'case':label,'status':state,'paragraphs':len(draft['paragraphs']),
      'paragraph_numbers':[p['number'] for p in draft['paragraphs']],
      'rewritten_changed_paragraphs':text_changed,'review_only':True,
      'word_exported':bool(ns.export_review_artifacts), 'linguistic_approval':False,'legal_approval':False,
      **artifact_hashes})
  except (AIUnavailable,DraftRejected,ValueError,KeyError,TypeError):
   results.append({'case':label,'status':'REJECTED_OR_PROVIDER_FAILED',
      'paragraphs':None,'rewritten_changed_paragraphs':None,
      'review_only':True,'word_exported':False,'linguistic_approval':False,'legal_approval':False})
  print(f'{label}: {results[-1]["status"]}')
 summary={'run_mode':'LIVE_PROVIDER_SYNTHETIC_ONLY' if is_live else 'OFFLINE_FAKE_ZERO_NETWORK',
    'notice':'Synthetic QA only. Even PASS is NOT legal, factual, or linguistic approval.',
    'review_artifacts_exported':bool(ns.export_review_artifacts),
    'models_or_keys_saved':False,'results':results}
 private_write(dest/'SUMMARY.json',json.dumps(summary,ensure_ascii=False,indent=2).encode())
 if ns.export_review_artifacts:
  from io import StringIO
  buf=StringIO();w=csv.DictWriter(buf,fieldnames=['case','criterion','check','human_result','reviewer_notes']);w.writeheader();w.writerows(scores)
  private_write(dest/'HUMAN_SCORECARD.csv',buf.getvalue().encode('utf-8-sig'))
  para_buf=StringIO()
  para_fields=['case','paragraph_number','subject','source_field_ids','human_result','reviewer_notes']
  w=csv.DictWriter(para_buf,fieldnames=para_fields);w.writeheader();w.writerows(paragraph_scores)
  private_write(dest/'PARAGRAPH_SCORECARD.csv',para_buf.getvalue().encode('utf-8-sig'))
 print(f'Local result folder: {dest.name}. Real cases are NOT accepted or loaded.')
 return 0 if all(r['status']=='STRUCTURAL_OK_HUMAN_REVIEW_PENDING' for r in results) else 1

if __name__=='__main__':raise SystemExit(go())
