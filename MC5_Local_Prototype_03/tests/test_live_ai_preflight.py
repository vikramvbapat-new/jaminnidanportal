from scripts.check_live_ai_readiness import check

def test_readiness_checks_do_not_require_calls_or_reveal_secrets(monkeypatch):
    for name in ['MC5_AI_PROVIDER','MC5_AI_ALLOW_EXTERNAL','MC5_LIVE_SYNTHETIC_TEST_APPROVED','MC5_AI_MODEL','OPENAI_API_KEY']:
        monkeypatch.delenv(name,raising=False)
    got=check()
    assert got['MC5_AI_MODEL'] is False
    assert got['OPENAI_API_KEY'] is False
    assert got['MC5_LIVE_SYNTHETIC_TEST_APPROVED'] is False
    assert all(type(x) is bool for x in got.values())
