#!/usr/bin/env python3
"""Four deterministic synthetic QA Word docs; ZERO network calls.

Evidence for the local integration boundary, never real AI quality or filing approval.
"""
from __future__ import annotations
import csv
import hashlib
import io
import json
import sys
from pathlib import Path
from docx import Document

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'tests'))
from test_engine import fixture
from app.engine import validate, create_docx, canonical_hash
from app.controlled_ai import controlled_draft
from scripts.live_ai_synthetic_smoke import synthetic_cases,inspect_candidate


class LocalEcho:
 def rewrite(self,request):
  return {'paragraphs':[{'number':p['number'],'text':p['baseline_text']} for p in request['paragraphs']]}


def main()->int:
 out=ROOT/'qa'/'prototype03'
 out.mkdir(exist_ok=True,parents=True)
 rows=[]
 for label,data in synthetic_cases():
  governed=validate(data)
  draft=controlled_draft(data,LocalEcho(),True)
  errors=inspect_candidate(governed,draft)
  # Only local synthetic generation. Avoid treating this as human-reviewed final Word issuance.
  blob=create_docx(data,canonical_hash(data),True,draft_override=draft)
  doc=Document(io.BytesIO(blob))
  text='\n'.join(p.text for p in doc.paragraphs)
  assert len(doc.tables)==1 and len(doc.tables[0].columns)==5
  assert 'याच रस्त्यावरील अडथळा हा प्रस्तुत दाव्याचा विषय आहे.' in text
  assert 'श्री ' not in text
  assert 'AI भाषिक परीक्षण' in text
  assert len(draft['paragraphs'])>0
  if data['status']==3:
   assert 'अडथळा दूर करण्याचे आदेश देण्यात यावेत.' not in text
  if data['filing_date']=='2027-08-01':
   assert 'विहित मुदतीत' not in text
   assert 'पुनरावलोकन' in text
  path=out/f'{label}_FAKE_PROVIDER_REVIEW_ONLY.docx'
  path.write_bytes(blob)
  rows.append({'scenario':label,'qa_docx':path.name,
    'paragraphs':len(draft['paragraphs']),'prayers':len(draft['prayers']),
    'limitation_mode':draft['limitation']['mode'],
    'word_qa_status':'STRUCTURAL_CHECK_PASS' if not errors else 'FAIL',
    'real_ai_test':'NOT_PERFORMED','linguistic_approval':'NOT_GIVEN',
    'legal_approval':'NOT_GIVEN','sha256':hashlib.sha256(blob).hexdigest()})
 with (out/'FOUR_SCENARIO_QA_MATRIX.csv').open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
 (out/'HUMAN_REVIEW_CHECKLIST.md').write_text('''# चार काल्पनिक Word नमुन्यांची मानवी पडताळणी — प्रलंबित

हे दस्तऐवज फक्त FAKE provider द्वारे तयार झाले आहेत. प्रत्यक्ष AI भाषा आणि न्यायालयीन वापर यांना **मंजुरी नाही**.

प्रत्येक नमुन्यात खालील बाबी तपासायच्या:

- [ ] वादी–प्रतिवादी, गाव/गट आणि प्रकरणाच्या पुष्टी झालेल्या तथ्यांचे अचूक वर्णन
- [ ] १३ परिच्छेदांचे मूळ विषय आणि लागू परिच्छेदांचे स्थिर क्रमांक
- [ ] परिच्छेद २ मध्ये पुरावा नाही; परिच्छेद १० मध्ये फक्त उपलब्ध पुरावे
- [ ] परिच्छेद ७ (रस्त्याच्या वापरावरील परिणाम) विरुद्ध ८ (स्वतंत्र अडचणी)
- [ ] परिच्छेद ९ आणि तातडीची मागणी फक्त स्वतंत्र होय पुष्टी असल्यास
- [ ] भौतिक अडथळा दूर असल्यास चालू अडथळ्याचा दावा किंवा दूर करण्याची मागणी नाही
- [ ] उपलब्ध पुरावा आणि अर्जास प्रत्यक्ष जोडलेली कागदपत्रे यांची गल्लत नाही
- [ ] मुदत संपल्यास अंतिम ग्राह्य अर्ज म्हणून नव्हे तर केवळ पुनरावलोकनाचा मसुदा
- [ ] कोणत्याही वाक्यात नवे हक्क, आर्थिक नुकसान, पुरावे, नकाशा, तारीख किंवा खटल्याचे निष्कर्ष कल्पनेने घातलेले नाहीत
- [ ] मराठी भाषा वाचनीय, प्रवाही आणि पुनरावृत्तीविरहित

**QA अहवालातील PASS हा या मानवी मंजुरींचा पर्याय नाही.**
''',encoding='utf-8')
 print(f'{len(rows)} synthetic Word proofs generated; no API call. {out}')
 return 0


if __name__=='__main__':raise SystemExit(main())
