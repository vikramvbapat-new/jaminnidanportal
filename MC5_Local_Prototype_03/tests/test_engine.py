from __future__ import annotations
from datetime import date
import io, copy
import pytest
from docx import Document
from app.engine import make_draft,create_docx,canonical_hash,ValidationError,S7,EVIDENCE


def fixture(status=1,urgency=False,filing_date='2026-10-24'):
 d={
 'map_ack':True,'village':'आंबेगाव','taluka':'जुन्नर','district':'पुणे',
 'plaintiffs':[{'name':'अजय गणपत पाटील','address':'काल्पनिक वस्ती, जुन्नर','gat':'१२५','cultivable':'१.२०','potkharab':'०.०५','assessment':'१२.५०'}],
 'defendants':[{'name':'विजय रामचंद्र शिंदे','address':'काल्पनिक वस्ती, जुन्नर','gat':'१२४','cultivable':'०.८०','potkharab':'०.००','assessment':'९.२०'}],
 'preexisting_use':'पूर्वीपासून ये-जा होत होती.',
 'route_description':'गट क्रमांक १२४ च्या शेजारून गाव रस्त्याच्या दिशेने',
 'village_road_confirmed':True,'width_ft':'१२','length_ft':'१५०',
 'obstruction_date':'2026-09-15','obstruction_gat':'१२४','obstruction_gat_confidence':'exact',
 'obstructor_role':'स्वतः खातेदार',
 'obstruction_description':'दगड ठेवण्यात आले.','status':status,
 'access_effect':'ट्रॅक्टर येऊ शकत नाही.' if status!=3 else 'पूर्वी ट्रॅक्टरला अडचण आली होती.',
 'specific_harm':'','crop_status':'standing','harvested_stock':False,
 'urgency_reasons':[2] if urgency else [], 'reason3_details':[], 'reason4_damage':None,
 'house_confirmed':False,'urgent_hearing':True if urgency else None,
 'evidence':[EVIDENCE[4],EVIDENCE[5]],'attached_docs':[EVIDENCE[4]],
 'attempts_made':True,'attempt_types':['प्रतिवादींना वैयक्तिक विनंती'],
 'defendant_response':'नकार','filing_date':filing_date
 }
 return d

def test_all_statuses_prayers():
 for status,expect in [(1,3),(2,3),(3,1)]:
  d=fixture(status=status);out=make_draft(d)
  assert len(out['prayers'])==expect
  assert [x['display_number'] for x in out['prayers']]==list(range(1,expect+1))
  assert [x['number'] for x in out['paragraphs'] if x['number'] in (1,12,13)]==[1,12,13]

def test_urgency_requires_separate_yes_no():
 d=fixture(urgency=True);assert len(make_draft(d)['prayers'])==4
 d['urgent_hearing']=False;assert len(make_draft(d)['prayers'])==3
 d['urgent_hearing']=None
 with pytest.raises(ValidationError):make_draft(d)

def test_status3_rejects_stale_urgency():
 d=fixture(3);d['urgency_reasons']=[2];d['urgent_hearing']=True
 with pytest.raises(ValidationError):make_draft(d)

def test_expired_late_review_only_and_no_within_time_assertion():
 d=fixture(filing_date='2027-08-01');out=make_draft(d)
 assert out['limitation']['mode']=='REVIEW_ONLY'
 assert all('विहित मुदतीत' not in x['text'] for x in out['paragraphs'])

def test_prayers_not_in_ai_paragraphs():
 d=fixture();o=make_draft(d)
 assert all('तातडीने सुनावणी' not in p['text'] for p in o['paragraphs'])
 assert not any(p['number']==4 for p in o['paragraphs']) # avoid P02 duplicate

def test_real_docx_and_review_token_stale_rejection():
 d=fixture(urgency=True)
 with pytest.raises(ValidationError):create_docx(d,canonical_hash(d),False)
 blob=create_docx(d,canonical_hash(d),True)
 doc=Document(io.BytesIO(blob));text='\n'.join(p.text for p in doc.paragraphs)
 assert len(doc.tables[0].columns)==5
 assert 'दाव्यास कारण' in text and 'तातडीने सुनावणी' in text
 assert 'श्री ' not in text
 d['width_ft']='१३'
 with pytest.raises(ValidationError):create_docx(d,canonical_hash(fixture(urgency=True)),True)

def test_no_invented_attached_documents():
 d=fixture();d['attached_docs']=[]
 blob=create_docx(d,canonical_hash(d),True)
 assert 'कोणतेही जोडल्याची पुष्टी दिलेली नाही' in '\n'.join(p.text for p in Document(io.BytesIO(blob)).paragraphs)

def test_reason3_needs_suboption():
 d=fixture();d['urgency_reasons']=[3];d['urgent_hearing']=False
 with pytest.raises(ValidationError):make_draft(d)
 d['reason3_details']=[S7['reasons'][2]['suboptions'][1]]
 assert not any(x['number']==9 for x in make_draft(d)['paragraphs']) # explicit urgent hearing NO
 d['urgent_hearing']=True
 assert any(x['number']==9 for x in make_draft(d)['paragraphs'])

def test_crop_conditions_and_house_confirmation():
 d=fixture();d['crop_status']='planned';d['urgency_reasons']=[2];d['urgent_hearing']=False
 with pytest.raises(ValidationError):make_draft(d)
 d=fixture();d['urgency_reasons']=[5];d['urgent_hearing']=False
 with pytest.raises(ValidationError):make_draft(d)
 d['house_confirmed']=True;assert make_draft(d)

def test_no_unverified_gat_and_width():
 d=fixture();d['width_ft']='';d['obstruction_gat']=''
 with pytest.raises(ValidationError):make_draft(d)

def test_evidence_is_not_attachment():
 d=fixture();d['attached_docs']=[EVIDENCE[0]]
 with pytest.raises(ValidationError):make_draft(d)
