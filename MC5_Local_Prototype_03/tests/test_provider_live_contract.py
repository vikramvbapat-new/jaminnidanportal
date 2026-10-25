"""Provider-agnostic scenarios with synthetic-only fake adapter (zero network calls)."""
import copy
import json
from app.controlled_ai import (controlled_draft, make_rewrite_request,
                               DraftRejected, OpenAIRewriter)
from app.engine import validate
from scripts.live_ai_synthetic_smoke import synthetic_cases, inspect_candidate, main
import pytest


class VerifiedFactEchoProvider:
    def rewrite(self, req):
        return {'paragraphs':[{'number':x['number'],'text':x['baseline_text']}
                              for x in req['paragraphs']]}


def test_four_scenarios_mock_provider_have_expected_paragraphs():
    provider=VerifiedFactEchoProvider()
    for name,data in synthetic_cases():
        draft=controlled_draft(data,provider,user_consented=True)
        canonical=validate(data)
        assert not inspect_candidate(canonical,draft), name
        assert draft['review_only'] is True
        assert draft['export_label']=='AI भाषिक परीक्षण — केवळ पुनरावलोकनासाठी'


def test_rewrite_payload_no_names_contacts_or_land_valuation():
    for _,data in synthetic_cases():
        data=copy.deepcopy(data)
        data['route_description']+=' अजय गणपत पाटील test@example.com 9876543210'
        out=json.dumps(make_rewrite_request(validate(data)),ensure_ascii=False)
        for private in ['अजय गणपत पाटील','विजय रामचंद्र शिंदे',
                        'test@example.com','9876543210',
                        '१२.५०','९.२०','काल्पनिक वस्ती']:
            assert private not in out


def test_test_runner_never_calls_provider_without_both_optins(monkeypatch):
    monkeypatch.delenv('MC5_LIVE_SYNTHETIC_TEST_APPROVED',raising=False)
    monkeypatch.setenv('MC5_AI_PROVIDER','openai')
    monkeypatch.setenv('MC5_AI_MODEL','any-model')
    monkeypatch.setenv('MC5_AI_ALLOW_EXTERNAL','true')
    monkeypatch.setenv('OPENAI_API_KEY','not-a-real-secret')
    monkeypatch.setattr(OpenAIRewriter,'rewrite',lambda self,req: (_ for _ in ()).throw(AssertionError('network path reached')))
    assert main([])==2
    assert main(['--live-synthetic-only'])==2
    monkeypatch.setenv('MC5_LIVE_SYNTHETIC_TEST_APPROVED','YES')
    monkeypatch.delenv('OPENAI_API_KEY')
    assert main(['--live-synthetic-only'])==3


def test_malicious_extra_prayer_rejected_through_provider():
    class Adversarial:
        def rewrite(self,req):
            ans=VerifiedFactEchoProvider().rewrite(req)
            ans['prayers']=['नवीन मागणी']
            return ans
    with pytest.raises(DraftRejected):
        controlled_draft(synthetic_cases()[0][1],Adversarial(),True)


def test_fake_hallucinated_ten_year_fact_is_rejected():
    class Adversarial:
        def rewrite(self,req):
            ans=VerifiedFactEchoProvider().rewrite(req)
            ans['paragraphs'][0]['text']+=' या रस्त्यावर १० वर्षे वहिवाट होती.'
            return ans
    with pytest.raises(DraftRejected,match='संख्यात्मक'):
        controlled_draft(synthetic_cases()[0][1],Adversarial(),True)
