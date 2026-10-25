"""Offline gated QA: never contacts AI provider."""
import json
import os
from pathlib import Path
from docx import Document
from scripts.live_ai_acceptance_review import go


def test_no_external_path_parser_or_real_case_file(monkeypatch,tmp_path):
 monkeypatch.delenv('MC5_LIVE_SYNTHETIC_TEST_APPROVED',raising=False)
 assert go(['--live-synthetic-only'])==2

def test_export_blocked_without_second_approval(monkeypatch):
 monkeypatch.setenv('MC5_LIVE_SYNTHETIC_TEST_APPROVED','YES')
 monkeypatch.delenv('MC5_LIVE_REVIEW_EXPORT_APPROVED',raising=False)
 assert go(['--live-synthetic-only','--export-review-artifacts'])==2

def test_real_provider_required_no_calls(monkeypatch):
 monkeypatch.setenv('MC5_LIVE_SYNTHETIC_TEST_APPROVED','YES')
 monkeypatch.delenv('OPENAI_API_KEY',raising=False)
 assert go(['--live-synthetic-only'])==3

def test_offline_fake_export_creates_four_pairwise_review_docs():
 assert go(['--offline-fake','--export-review-artifacts'])==0
 root=Path(__file__).resolve().parents[1]/'qa/live_acceptance/offline_fake'
 paths=list(root.glob('*_PARAGRAPH_COMPARISON.docx'))
 assert len(paths)==4
 assert len(list(root.glob('*_REVIEW_ONLY.docx')))==4
 for p in paths:
  doc=Document(p)
  assert len(doc.tables)>0
  assert 'तुलनात्मक परीक्षण' in '\n'.join(x.text for x in doc.paragraphs)
 data=json.loads((root/'SUMMARY.json').read_text(encoding='utf-8'))
 assert len(data['results'])==4
 assert all(x['status']=='STRUCTURAL_OK_HUMAN_REVIEW_PENDING' for x in data['results'])
 assert all(x['rewritten_changed_paragraphs']==0 for x in data['results'])
