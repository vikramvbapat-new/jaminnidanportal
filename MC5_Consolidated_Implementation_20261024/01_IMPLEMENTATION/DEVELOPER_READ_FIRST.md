# MC5 — एकत्रित Developer Implementation Baseline (24 October 2026)

**Status:** implementation baseline after 3 express user approvals; not production-ready.
**Module:** cases under Mamlatdars’ Courts Act, 1906, §5; §143 separate legal engine.

## Read these files first
1. `MASTER_IMPLEMENTATION_CONTRACT.json` — approved 13 immutable paragraphs, conditional prayers, land table, retention; updates the 3 user decisions in V30.
2. `S7_FINAL_APPROVED_RULES.json` — exact six S7 labels and conditional logic; labels 1–3 explicitly approved 24-10-2026; later approved 4–6 preserved.
3. `rules_reference.py` — executable reference implementation of just the three new decisions; not the full portal.
4. `../02_APPROVAL_AND_TESTS/CHANGE_REGISTER_20261024.csv` — approval evidence; no silent promotion of pending matters.
5. `../03_SOURCE_REFERENCE/MC5_V30_COMPLETE_UNMODIFIED.zip` — full unchanged 232-file development history (V17–V30).
6. `../03_SOURCE_REFERENCE/MC5_Master_Approved_Specification_20261023.docx` — approved Master baseline.

## Precedence
Approved Master Base Application, then later explicitly approved corrections and dated user decisions, then audited sources, then candidate examples. Never let QA synthetic petitions override Master. Do not replace 13 paragraph numbers with dynamic re-numbering. §5 parties = वादी/प्रतिवादी. §143 (अर्जदार/जाबदार) remains isolated.

## Scope of freeze
- **Newly frozen:** labels S7-1/2/3, PR4 independent opt-in, review-only late-case Word behavior.
- **Already frozen:** original 13 paragraph subjects/numbers, approved prayers text, 5-column land table, main facts and conditional rules, S7-4/5/6 and suboptions.
- **Not frozen/implemented:** every missing literal screen question, final Word layout, PR2 independent legal check, live AI, OCR, OTP, secure user data, physical 30-day deletion.

## Essential release conditions
1. Real data/OCR must be verified; no invented people, gats, dates, route directions, harms or rights. Every paragraph bound to user-verified fields and checked fact-by-fact.
2. PR4 **never** inferred solely from selected S7 reasons; explicit yes/no and status=1/2.
3. For suspected late cases allow **REVIEW_ONLY** DOCX with conspicuous warning, no filing-ready label; no automatic “विहित मुदतीत” assertion.
4. Any input or generated draft change invalidates the previous approval. User reviews complete actual final Word once after sample QA.
5. Developer should not ask user approval for routine aliases, screen wiring or security mechanisms. Escalate only true legal ambiguity or a materially inconsistent approved question.
6. Approved prayer #2 may remain in the Master; do not mark release gate green until independent legal implementation review.
7. Existing V28 mock/provider and Word tests are reference only. The production portal and genuine AI service are not delivered.
