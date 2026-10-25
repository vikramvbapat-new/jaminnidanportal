"""Local-only FastAPI prototype 02. AI disabled by default. No persistence/OCR/OTP."""
from pathlib import Path
from io import BytesIO
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
from pydantic import BaseModel
from .engine import (make_draft, create_docx, canonical_hash, ValidationError, S7,
                     EVIDENCE, ATTEMPTS, RESPONSES, CROP, STATUS_TEXT, validate)
from .controlled_ai import (configured_provider, provider_is_configured, controlled_draft,
  validated_candidate, issue_review_token, require_review_token, AIUnavailable, DraftRejected)

app=FastAPI(title='MC5 Local Prototype 03 — NON PRODUCTION',docs_url=None,redoc_url=None)
STATIC=Path(__file__).parent/'static'

class Input(BaseModel):
 data:dict
class DocxInput(BaseModel):
 data:dict
 preview_token:str
 review_confirmed:bool=False
class AIInput(BaseModel):
 data:dict
 explicit_external_ai_consent:bool=False
class AIDocxInput(BaseModel):
 data:dict
 candidate:dict
 review_token:str
 review_confirmed:bool=False
 reviewed_paragraph_numbers:list[int]=[]

@app.get('/')
def index():return FileResponse(STATIC/'index.html',headers={'Cache-Control':'no-store'})
@app.get('/app.js')
def js():return FileResponse(STATIC/'app.js',media_type='application/javascript',headers={'Cache-Control':'no-store'})
@app.get('/styles.css')
def css():return FileResponse(STATIC/'styles.css',media_type='text/css',headers={'Cache-Control':'no-store'})
SUGGESTIONS = {
 'preexisting_use': [
  'गेल्या अनेक वर्षांपासून शेतात बैलगाडी, ट्रॅक्टर व पायी येण्या-जाण्यासाठी वहिवाट आहे.',
  'शेतमाल वाहतूक, खते व अवजारे नेण्या-आणण्यासाठी पूर्वीपासून वापर केला जातो.',
  'शेतातील विहीर, घर व मशागतीसाठी हाच पूर्वापार वहिवाटीचा रस्ता आहे.'
 ],
 'route_description': [
  'गट क्रमांकाच्या बांधावरून जाणारा वहिवाटीचा मार्ग.',
  'पूर्वेकडील हद्दीवरून थेट शेताकडे जाणारा वहिवाटीचा रस्ता.',
  'सामाईक बांधावरून गाव रस्त्याकडे जाणारा वहिवाटीचा मार्ग.'
 ],
 'obstruction_description': [
  'माती व मुरूमाचा भराव टाकून रस्ता पूर्ण बंद केला.',
  'दगडांचा ढीग रचून ट्रॅक्टर व बैलगाडीची वाहतूक अडवली.',
  'काटेरी तारांचे कुंपण व झाडांच्या फांद्या टाकून वहिवाट बंद केली.',
  'रस्त्यावर खोल चर (खड्डा) खणून वहिवाट अडवली.'
 ],
 'access_effect': [
  'शेतात ट्रॅक्टर, अवजारे व बैलगाडी नेणे पूर्णपणे बंद झाले आहे.',
  'काढलेला शेतमाल बाजारात नेणे अशक्य झाले आहे.',
  'शेतीची आंतरमशागत, खते व पाणी देणे खोळंबले आहे.'
 ],
 'specific_harm': [
  'पीक काढणी वेळेत न झाल्याने शेतमालाचे प्रत्यक्ष नुकसान होण्याची भीती आहे.',
  'पाणी देणे व औषध फवारणी वेळेत करता आली नाही.',
  'शेतात जाण्याचा दुसरा कोणताही पर्यायी मार्ग उपलब्ध नाही.'
 ]
}

@app.get('/api/options')
def options():return {'reasons':S7['reasons'],'evidence':EVIDENCE,'attempts':ATTEMPTS,
                      'responses':RESPONSES,'crop':CROP,'status':STATUS_TEXT,
                      'suggestions':SUGGESTIONS}
@app.post('/api/preview')
def preview(input:Input):
 try:
  draft=make_draft(input.data)
  draft['preview_token']=canonical_hash(input.data)
  return JSONResponse(draft,headers={'Cache-Control':'no-store'})
 except ValidationError as exc:raise HTTPException(status_code=422,detail=exc.errors) from exc
@app.post('/api/docx')
def docx(input:DocxInput):
 try:blob=create_docx(input.data,input.preview_token,input.review_confirmed)
 except ValidationError as exc:raise HTTPException(status_code=422,detail=exc.errors) from exc
 return _word(blob,'MC5_RULE_BASED_REVIEW_ONLY.docx')

def _word(blob:bytes,filename:str):
 return StreamingResponse(BytesIO(blob),media_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  headers={'Content-Disposition':f'attachment; filename="{filename}"','Cache-Control':'no-store'})

@app.post('/api/ai-preview')
def ai_preview(input:AIInput):
 # This check comes before any network call; explicit opt-in for this very request.
 if input.explicit_external_ai_consent is not True:
  raise HTTPException(status_code=422,detail=['बाह्य AI सेवेकडे मर्यादित तथ्ये पाठवण्याची स्वतंत्र संमती आवश्यक आहे.'])
 try:
  draft=controlled_draft(input.data,configured_provider(),True)
  draft['review_token']=issue_review_token(input.data,draft)
  return JSONResponse(draft,headers={'Cache-Control':'no-store'})
 except ValidationError as exc:raise HTTPException(status_code=422,detail=exc.errors) from exc
 except DraftRejected as exc:raise HTTPException(status_code=422,detail=exc.errors) from exc
 except AIUnavailable as exc:raise HTTPException(status_code=503,detail=[str(exc)]) from exc

@app.post('/api/ai-docx')
def ai_docx(input:AIDocxInput):
 if input.review_confirmed is not True:
  raise HTTPException(status_code=422,detail=['प्रत्येक परिच्छेद तपासल्याची स्पष्ट पुष्टी आवश्यक आहे.'])
 try:
  d=validate(input.data)
  # Independently re-check all AI text and recompute fixed prayers; never trust client-submitted metadata.
  if not isinstance(input.candidate,dict) or set(input.candidate)!={'paragraphs'}:
   raise DraftRejected(['AI उमेदवार मसुद्याचे स्वरूप अमान्य.'])
  approved=validated_candidate(d,input.candidate)
  expected=[p['number'] for p in approved['paragraphs']]
  if sorted(input.reviewed_paragraph_numbers)!=sorted(expected) or len(set(input.reviewed_paragraph_numbers))!=len(expected):
   raise DraftRejected(['AI मसुद्यातील प्रत्येक परिच्छेदाची स्वतंत्र पडताळणी व पुष्टी आवश्यक आहे.'])
  require_review_token(input.data,approved,input.review_token)
  blob=create_docx(input.data,canonical_hash(input.data),True,draft_override=approved)
 except (ValidationError,DraftRejected) as exc:
  raise HTTPException(status_code=422,detail=exc.errors) from exc
 return _word(blob,'MC5_AI_REVIEW_ONLY.docx')

@app.get('/api/status')
def status():
 return {'name':'MC5 local prototype 03','production':False,
         'ai_available':provider_is_configured(),
         'ai_live_tested':False,'external_ai_consent_required':True,
         'ai_send_names_and_addresses':False,
         'ocr':False,'otp':False,'persistent_storage':False}
