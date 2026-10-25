"""Every test uses a fake provider; no external AI call or real personal data."""
from __future__ import annotations
import copy, io, json
import pytest
from fastapi.testclient import TestClient
from docx import Document
from app.engine import validate
from app.controlled_ai import (make_rewrite_request, controlled_draft, validated_candidate,
 DraftRejected, issue_review_token, require_review_token, LOCKED_PARAGRAPHS)
from app import server
from test_engine import fixture

class EchoRewriter:
 def __init__(self): self.saw=None
 def rewrite(self,request):
  self.saw=request
  return {'paragraphs':[{'number':p['number'],'text':p['baseline_text']} for p in request['paragraphs']]}

class AlterRewriter(EchoRewriter):
 def __init__(self,number,replacement):self.number=number;self.replacement=replacement
 def rewrite(self,request):
  x=super().rewrite(request)
  for p in x['paragraphs']:
   if p['number']==self.number:p['text']=self.replacement(p['text'])
  return x

def raw_candidate(d):
 req=make_rewrite_request(validate(d))
 return {'paragraphs':[{'number':p['number'],'text':p['baseline_text']} for p in req['paragraphs']]}

def test_minimized_request_does_not_send_party_names_addresses_phone():
 d=fixture();d['route_description']+=' अजय गणपत पाटील 9876543210 test@example.com'
 provider=EchoRewriter()
 request=make_rewrite_request(validate(d))
 data=json.dumps(request,ensure_ascii=False)
 assert 'अजय गणपत पाटील' not in data
 assert 'विजय रामचंद्र शिंदे' not in data
 assert 'काल्पनिक वस्ती' not in data
 assert '9876543210' not in data and 'test@example.com' not in data
 assert 'गट क्रमांक' in data
 assert 'जिल्हा' not in data  # not required for editable paragraphs

def test_external_consent_is_compulsory_even_with_injected_provider():
 with pytest.raises(DraftRejected,match='संमती'):
  controlled_draft(fixture(),EchoRewriter(),False)

def test_echo_provider_success_and_locked_fields():
 d=fixture(urgency=True);provider=EchoRewriter();result=controlled_draft(d,provider,True)
 assert [p['number'] for p in result['paragraphs'] if p['number'] in LOCKED_PARAGRAPHS]==[1,5,6,12,13]
 assert len(result['prayers'])==4
 assert all(p['source_field_ids'] for p in result['paragraphs'])
 assert 'प्रकरणाशी संबंध' not in provider.saw['paragraphs'][0]['baseline_text']

def test_refuse_added_40_year_fact():
 x=AlterRewriter(2,lambda text:text+' या रस्त्याचा ४० वर्षांपासून वापर आहे.')
 with pytest.raises(DraftRejected,match='संख्यात्मक'):
  controlled_draft(fixture(),x,True)

def test_refuse_evidence_in_paragraph_two():
 x=AlterRewriter(2,lambda text:text+' जुन्या फोटोमधून हा रस्ता दिसून येतो.')
 with pytest.raises(DraftRejected,match='पुरावे'):
  controlled_draft(fixture(),x,True)

def test_refuse_false_attached_docs_claim():
 x=AlterRewriter(10,lambda text:text+' अर्जासोबत जोडलेले पुरावे सादर केलेले आहेत.')
 with pytest.raises(DraftRejected,match='उपलब्ध पुरावा'):
  controlled_draft(fixture(),x,True)

def test_refuse_ai_made_prayers_and_extra_paragraph():
 d=validate(fixture());p=raw_candidate(d)
 p['prayers']=[{'text':'नवीन मनमानी मागणी'}]
 with pytest.raises(DraftRejected):validated_candidate(d,p)
 p=raw_candidate(d);p['paragraphs'].append({'number':14,'text':'पूर्णपणे अमान्य नमुना परिच्छेद.'})
 with pytest.raises(DraftRejected):validated_candidate(d,p)

def test_refuse_new_unverified_money_and_gat_number():
 d=fixture();d['specific_harm']='मशागत वेळेत होऊ शकत नाही.'
 x=AlterRewriter(8,lambda text:text+' आर्थिक नुकसान ९००० रुपये झाले.')
 with pytest.raises(DraftRejected):controlled_draft(d,x,True)
 x=AlterRewriter(3,lambda text:text+' अतिरिक्त गट क्रमांक ९९९ मधून मार्ग जातो.')
 with pytest.raises(DraftRejected,match='संख्यात्मक'):
  controlled_draft(fixture(),x,True)

def test_review_token_tampering_expiry_and_input_change():
 d=fixture();draft=controlled_draft(d,EchoRewriter(),True)
 t=issue_review_token(d,draft,now=1000)
 require_review_token(d,draft,t,now=1020)
 with pytest.raises(DraftRejected):require_review_token(d,draft,t,now=1901)
 changed=copy.deepcopy(d);changed['width_ft']='१३'
 with pytest.raises(DraftRejected):require_review_token(changed,draft,t,now=1020)
 modified=copy.deepcopy(draft);modified['paragraphs'][0]['text']='खोटा बदल'
 with pytest.raises(DraftRejected):require_review_token(d,modified,t,now=1020)

def test_fastapi_no_provider_exposed_and_separate_ai_consent():
 client=TestClient(server.app)
 status=client.get('/api/status').json()
 assert status['ai_available'] is False
 assert status['persistent_storage'] is False
 assert client.post('/api/ai-preview',json={'data':fixture(),'explicit_external_ai_consent':False}).status_code==422
 assert client.post('/api/ai-preview',json={'data':fixture(),'explicit_external_ai_consent':True}).status_code==503

def test_ai_route_review_and_word_using_mock(monkeypatch):
 provider=EchoRewriter()
 monkeypatch.setattr(server,'configured_provider',lambda:provider)
 client=TestClient(server.app)
 data=fixture(urgency=True)
 response=client.post('/api/ai-preview',json={'data':data,'explicit_external_ai_consent':True})
 assert response.status_code==200,response.text
 body=response.json();assert body['review_token']
 cand={'paragraphs':[{'number':p['number'],'text':p['text']} for p in body['paragraphs'] if p['drafting_mode']=='AI_REPHRASED_REVIEW_REQUIRED']}
 payload={'data':data,'candidate':cand,'review_token':body['review_token'],'review_confirmed':True,'reviewed_paragraph_numbers':[p['number'] for p in body['paragraphs']]}
 denied=client.post('/api/ai-docx',json={**payload,'review_confirmed':False})
 assert denied.status_code==422
 without_one=copy.deepcopy(payload);without_one['reviewed_paragraph_numbers'].pop()
 assert client.post('/api/ai-docx',json=without_one).status_code==422
 okay=client.post('/api/ai-docx',json=payload)
 assert okay.status_code==200,okay.text[:500] if okay.status_code!=200 else ''
 doc=Document(io.BytesIO(okay.content))
 output='\n'.join(p.text for p in doc.paragraphs)
 assert 'AI भाषिक परीक्षण' in output and 'तातडीने सुनावणी' in output
 assert len(doc.tables[0].columns)==5
 assert 'श्री ' not in output
 bad=copy.deepcopy(payload);bad['data']['width_ft']='१९'
 assert client.post('/api/ai-docx',json=bad).status_code==422
 tamper=copy.deepcopy(payload);tamper['candidate']['paragraphs'][0]['text']+=' अपुष्ट अतिरिक्त दावा.'
 assert client.post('/api/ai-docx',json=tamper).status_code==422

def test_status_three_no_ongoing_road_opening():
 d=fixture(status=3)
 result=controlled_draft(d,EchoRewriter(),True)
 assert len(result['prayers'])==1
 assert all('अडथळा दूर करण्याचे आदेश' not in p['text'] for p in result['prayers'])

def test_late_filing_stays_review_only():
 d=fixture(filing_date='2027-08-01')
 result=controlled_draft(d,EchoRewriter(),True)
 assert result['limitation']['mode']=='REVIEW_ONLY'
 assert all('विहित मुदतीत' not in p['text'] for p in result['paragraphs'])


def test_reason_selected_but_urgent_hearing_no_has_no_p9_or_pr4():
 d=fixture(urgency=True);d['urgent_hearing']=False
 out=controlled_draft(d,EchoRewriter(),True)
 assert 9 not in [p['number'] for p in out['paragraphs']]
 assert not any(p['master_prayer_id']=='PR-4' for p in out['prayers'])

def test_cause_of_action_mentions_attempt_only_if_confirmed():
 from app.engine import draft_paragraphs
 with_attempts={p['number']:p['text'] for p in draft_paragraphs(validate(fixture()))}
 d=fixture();d['attempts_made']=False;d['attempt_types']=[];d['defendant_response']=None
 without={p['number']:p['text'] for p in draft_paragraphs(validate(d))}
 assert 'प्रयत्नांनंतरही' in with_attempts[12] and 'प्रयत्नांनंतरही' not in without[12]

def test_literal_redaction_blocks_final_ai_paragraph():
 d=fixture();d['preexisting_use']='वापरकर्ता अजय गणपत पाटील आणि फोन ९८७६५४३२१०'
 with pytest.raises(DraftRejected):controlled_draft(d,EchoRewriter(),True)
