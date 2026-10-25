import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'01_IMPLEMENTATION'))
from rules_reference import select_prayers,limitation_mode,InvalidForm,export_label,S7_REASON_LABELS
class ApprovedDecisions(unittest.TestCase):
 def test_three_labels_frozen(self):
  self.assertIn('पेरणी किंवा लागवडीचा हंगाम',S7_REASON_LABELS[1]);self.assertIn('मशागत',S7_REASON_LABELS[2]);self.assertIn('पीक काढणी',S7_REASON_LABELS[3])
 def test_status_1_default_three(self): self.assertEqual(len(select_prayers(1,[],None)),3)
 def test_status_2_default_three(self): self.assertEqual(len(select_prayers(2,[],None)),3)
 def test_urgent_requires_answer(self):
  with self.assertRaisesRegex(InvalidForm,'ASK_SEPARATE'):select_prayers(1,[2],None)
 def test_explicit_yes_inserts_pr4(self): self.assertEqual([x['master_prayer_id'] for x in select_prayers(2,[2],True)],['PR-1','PR-2','PR-3','PR-4'])
 def test_no_does_not_insert(self): self.assertEqual(len(select_prayers(1,[1],False)),3)
 def test_no_reasons_cannot_add(self):
  with self.assertRaisesRegex(InvalidForm,'WITHOUT_REASON'):select_prayers(1,[],True)
 def test_status3_only_pr3(self): self.assertEqual([x['master_prayer_id'] for x in select_prayers(3,[],None)],['PR-3'])
 def test_status3_no_stale_urgency(self):
  with self.assertRaisesRegex(InvalidForm,'S7_HIDDEN'):select_prayers(3,[1],True)
 def test_prayer_display_numbering(self): self.assertEqual([x['display_number'] for x in select_prayers(3,[],False)],[1])
 def test_invalid_reason(self):
  with self.assertRaises(InvalidForm):select_prayers(1,[7],False)
 def test_missing_date_review_only(self): self.assertEqual(limitation_mode(None,'2026-10-24')['mode'],'REVIEW_ONLY')
 def test_six_month_late_review_only(self): self.assertEqual(limitation_mode('2026-01-01','2026-10-24')['flag'],'SIX_MONTH_BOUNDARY_OR_LATE')
 def test_cutoff_review_only(self): self.assertEqual(limitation_mode('2026-04-24','2026-10-24')['mode'],'REVIEW_ONLY')
 def test_preliminary_not_filing_ready(self):
  d=limitation_mode('2026-09-15','2026-10-24'); self.assertEqual(d['mode'],'NORMAL_REVIEW');self.assertFalse(d['within_limit_statement_allowed'])
 def test_review_label(self):self.assertIn('केवळ कायदेशीर पुनरावलोकनासाठी',export_label(limitation_mode(None,None)))
if __name__=='__main__':unittest.main(verbosity=2)
