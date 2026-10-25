"""Verify actual SDK call shape without any external network access."""
from __future__ import annotations
import sys
import types
import pytest
from app.controlled_ai import OpenAIRewriter, AIUnavailable


def test_structured_output_no_tools_store_false_and_sanitized_input(monkeypatch):
 seen={}
 class Responses:
  def create(self,**kwargs):
   seen.update(kwargs)
   assert kwargs['store'] is False
   assert 'tools' not in kwargs
   assert kwargs['text']['format']['type']=='json_schema'
   return types.SimpleNamespace(output_text='{"paragraphs":[{"number":2,"text":"पूर्वीपासून सदर रस्त्यावरून वादी यांची ये-जा होत होती."}]}')
 class OpenAI:
  def __init__(self,**kwargs):
   assert kwargs['max_retries']==0
   assert kwargs['timeout']<60
   self.responses=Responses()
 monkeypatch.setitem(sys.modules,'openai',types.SimpleNamespace(OpenAI=OpenAI))
 monkeypatch.setenv('MC5_AI_ALLOW_EXTERNAL','true')
 monkeypatch.setenv('MC5_AI_MODEL','test-model')
 monkeypatch.setenv('OPENAI_API_KEY','not-real')
 answer=OpenAIRewriter().rewrite({'paragraphs':[{'number':2,'baseline_text':'example','verified_facts':{}}]})
 assert answer['paragraphs'][0]['number']==2
 assert 'न्यायालय' in seen['instructions'] or 'legal' in seen['instructions']


def test_fail_closed_on_invalid_sdk_response(monkeypatch):
 class Responses:
  def create(self,**kwargs):
   return types.SimpleNamespace(output_text='{invalid json')
 class OpenAI:
  def __init__(self,**kwargs):self.responses=Responses()
 monkeypatch.setitem(sys.modules,'openai',types.SimpleNamespace(OpenAI=OpenAI))
 monkeypatch.setenv('MC5_AI_ALLOW_EXTERNAL','true')
 monkeypatch.setenv('MC5_AI_MODEL','test-model')
 monkeypatch.setenv('OPENAI_API_KEY','not-real')
 with pytest.raises(AIUnavailable,match='वैध मसुदा'):
  OpenAIRewriter().rewrite({'paragraphs':[]})
