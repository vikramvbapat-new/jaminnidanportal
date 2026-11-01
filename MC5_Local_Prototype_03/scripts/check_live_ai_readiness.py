#!/usr/bin/env python3
"""Purely local preflight: checks configuration without printing secrets/calling API."""
from __future__ import annotations
import importlib.util, json, os

def check():
    statuses={}
    provider=os.getenv('MC5_AI_PROVIDER','')
    statuses['MC5_AI_PROVIDER']=provider in ('openai','gemini')
    statuses['MC5_AI_ALLOW_EXTERNAL']=os.getenv('MC5_AI_ALLOW_EXTERNAL','').lower()=='true'
    statuses['MC5_AI_MODEL']=bool(os.getenv('MC5_AI_MODEL','').strip())
    # Provider-specific checks
    statuses['OPENAI_API_KEY'] = bool(os.getenv('OPENAI_API_KEY','').strip()) if provider=='openai' else False
    statuses['openai_package'] = (importlib.util.find_spec('openai') is not None) if provider=='openai' else False
    statuses['GEMINI_API_KEY'] = bool(os.getenv('GEMINI_API_KEY','').strip()) if provider=='gemini' else False
    statuses['google_genai_package'] = (importlib.util.find_spec('google.genai') is not None) if provider=='gemini' else False
    # MC5_LIVE_SYNTHETIC_TEST_APPROVED is only needed for live synthetic smoke tests,
    # not for normal AI preview in the web UI.
    statuses['MC5_LIVE_SYNTHETIC_TEST_APPROVED']=os.getenv('MC5_LIVE_SYNTHETIC_TEST_APPROVED')=='YES'
    return statuses

def main():
    statuses=check()
    # For basic AI usage via web UI, the synthetic test flag is optional.
    core_ok=all(v for k,v in statuses.items() if k!='MC5_LIVE_SYNTHETIC_TEST_APPROVED')
    print(json.dumps({'readiness':'READY_TO_ATTEMPT_SYNTHETIC_LIVE_TEST' if all(statuses.values()) else ('AI_UI_READY' if core_ok else 'NOT_READY'),
        'provider':os.getenv('MC5_AI_PROVIDER','(not set)'),
        'satisfied':sorted([k for k,v in statuses.items() if v]),
        'missing_or_unapproved':sorted([k for k,v in statuses.items() if not v]),
        'external_calls_made':0,
        'notice':'Preflight never sends requests, checks no API validity, and is not a live AI test.'},
        ensure_ascii=False,indent=2))
    return 0 if core_ok else 3
if __name__=='__main__':raise SystemExit(main())
