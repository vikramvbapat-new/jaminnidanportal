"""Focused contradiction regressions for synthetic-only paragraph drafts."""
from __future__ import annotations
import pytest
from app.controlled_ai import controlled_draft, DraftRejected
from app.semantic_guard import semantic_contradiction_errors
from test_engine import fixture

class OneParagraphMaliciousProvider:
    def __init__(self, n:int, added:str):self.n,self.added=n,added
    def rewrite(self, req):
        out=[]
        for p in req['paragraphs']:
            text=p['baseline_text']+((' '+self.added) if p['number']==self.n else '')
            out.append({'number':p['number'],'text':text})
        return {'paragraphs':out}

@pytest.mark.parametrize('paragraph,added,change,expected',[
 (2,'सदर रस्ता अस्तित्वात नव्हता.',{},'पूर्वअस्तित्व'),
 (3,'सदर रस्ता गाव रस्त्याशी जोडलेला आहे.',{'village_road_confirmed':False},'गाव रस्त्याशी'),
 (7,'सध्या रस्ता पूर्णपणे बंद आहे.',{'status':3},'चालू अडथळ्याचा'),
 (10,'कोणतेही पुरावे उपलब्ध नाहीत.',{},'पुरावे नाकारले'),
 (11,'कोणतेही प्रयत्न केले नाहीत.',{},'प्रयत्न झाले'),
])
def test_ai_plain_language_contradictions_rejected(paragraph,added,change,expected):
    d=fixture(status=change.get('status',1));d.update(change)
    if paragraph==3:
        d['route_description']='स्वतःच्या गटापासून शेजारील गटापर्यंतचा पुष्टी केलेला मार्ग'
    with pytest.raises(DraftRejected,match=expected):
        controlled_draft(d,OneParagraphMaliciousProvider(paragraph,added),True)

@pytest.mark.parametrize('n,text,facts,case',[
 (2,'अडथळ्यापूर्वीपासून या रस्त्यावरून वहिवाट होत होती.',{'preexisting_use':'वहिवाट'},{}),
 (3,'सदर रस्त्याची रुंदी १० फूट आहे.',{}, {'village_road_confirmed':False}),
 (7,'पूर्वी ये-जा करण्यास अडचण आली होती.',{}, {'status':3}),
 (10,'पुरावे म्हणून जुने फोटो उपलब्ध आहेत.',{'evidence':['जुने फोटो']},{}),
 (11,'अडथळा काढण्यासाठी वादी यांनी वैयक्तिक विनंती केली होती.',{}, {'attempts_made':True}),
])
def test_guard_no_false_positive_on_plain_approved_sense(n,text,facts,case):
    assert semantic_contradiction_errors(n,text,facts=facts,case=case)==[]
