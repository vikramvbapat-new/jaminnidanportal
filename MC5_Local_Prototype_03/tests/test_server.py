from fastapi.testclient import TestClient
from app.server import app
from test_engine import fixture

client=TestClient(app)

def test_page_and_options():
 r=client.get('/');assert r.status_code==200
 assert 'जमीन निदान पोर्टल' in r.text
 opts=client.get('/api/options').json()
 assert len(opts['reasons'])==6
 assert len(opts['status'])==3

def test_preview_docx_e2e():
 d=fixture(status=2,urgency=True)
 res=client.post('/api/preview',json={'data':d});assert res.status_code==200,res.text
 draft=res.json();assert len(draft['prayers'])==4
 t=draft['preview_token']
 doc=client.post('/api/docx',json={'data':d,'preview_token':t,'review_confirmed':True})
 assert doc.status_code==200 and doc.content.startswith(b'PK')
 d['route_description']='बदल'
 stale=client.post('/api/docx',json={'data':d,'preview_token':t,'review_confirmed':True})
 assert stale.status_code==422
