#!/usr/bin/env python3
"""Purely local preflight: checks configuration without printing secrets/calling API."""
from __future__ import annotations
import importlib.util, json, os

REQUIRED={
    'MC5_AI_PROVIDER':'openai',
    'MC5_AI_ALLOW_EXTERNAL':'true',
    'MC5_LIVE_SYNTHETIC_TEST_APPROVED':'YES',
}

def check():
    statuses={name:(os.getenv(name)==value) for name,value in REQUIRED.items()}
    statuses['MC5_AI_MODEL']=bool(os.getenv('MC5_AI_MODEL','').strip())
    statuses['OPENAI_API_KEY']=bool(os.getenv('OPENAI_API_KEY','').strip())
    statuses['openai_package']=importlib.util.find_spec('openai') is not None
    return statuses

def main():
    statuses=check()
    print(json.dumps({'readiness':'READY_TO_ATTEMPT_SYNTHETIC_LIVE_TEST' if all(statuses.values()) else 'NOT_READY',
        'satisfied':sorted([k for k,v in statuses.items() if v]),
        'missing_or_unapproved':sorted([k for k,v in statuses.items() if not v]),
        'external_calls_made':0,
        'notice':'Preflight never sends requests, checks no API validity, and is not a live AI test.'},
        ensure_ascii=False,indent=2))
    return 0 if all(statuses.values()) else 3
if __name__=='__main__':raise SystemExit(main())
