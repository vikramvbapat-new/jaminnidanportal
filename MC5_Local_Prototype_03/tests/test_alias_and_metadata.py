from __future__ import annotations
import pytest
from app.engine import validate, make_draft, create_docx, canonical_hash, ValidationError, S7, EVIDENCE
from test_engine import fixture


def test_approved_aliases_mapping():
    """Verify all 7 approved aliases from V30 Register (A4 Gate) map to canonical keys."""
    d = fixture(urgency=True)
    # Remove direct keys
    d.pop('reason3_details', None)
    d.pop('harvested_stock', None)
    d.pop('house_confirmed', None)
    d.pop('reason4_damage', None)
    d.pop('urgent_hearing', None)

    # Use approved aliases
    d['urgency_reasons'] = [3, 4, 5]
    d['crop_status'] = 'standing'
    d['MC5_URGENCY_3_SUBOPTIONS'] = [S7['reasons'][2]['suboptions'][0]]
    d['MC5_HARVESTED_STOCK'] = False
    d['MC5_FARM_HOUSE_CONFIRMED'] = True
    d['MC5_URGENCY_4_DAMAGE_STATUS'] = S7['reasons'][3]['suboptions'][0]
    d['MC5_URGENT_HEARING_OPTIN'] = True

    governed = validate(d)
    assert governed['reason3_details'] == [S7['reasons'][2]['suboptions'][0]]
    assert governed['house_confirmed'] is True
    assert governed['reason4_damage'] == S7['reasons'][3]['suboptions'][0]
    assert governed['urgent_hearing'] is True


def test_alias_conflict_rejection():
    """Ensure conflict between alias and canonical field raises ValidationError."""
    d = fixture()
    d['MC5_HARVESTED_STOCK'] = True
    d['harvested_stock'] = False
    with pytest.raises(ValidationError) as exc:
        validate(d)
    assert any('Alias conflict' in str(err) for err in exc.value.errors)


def test_register_canonical_key_mapping():
    """Ensure MC5_ prefixed canonical register keys resolve properly."""
    d = fixture()
    d.pop('village')
    d['MC5_VILLAGE'] = 'नांदूर'
    governed = validate(d)
    assert governed['village'] == 'नांदूर'


def test_register_key_conflict_rejection():
    """Ensure conflict between MC5_ register key and canonical field raises ValidationError."""
    d = fixture()
    d['village'] = 'गाव_अ'
    d['MC5_VILLAGE'] = 'गाव_ब'
    with pytest.raises(ValidationError) as exc:
        validate(d)
    assert any('Register key conflict' in str(err) for err in exc.value.errors)


def test_metadata_and_retention():
    """Verify session draft_id, started_at, and 30-day retention calculation."""
    d = fixture()
    draft = make_draft(d)
    assert 'draft_id' in draft and len(draft['draft_id']) > 10
    assert 'started_at' in draft and 'T' in draft['started_at']
    assert 'expires_at' in draft and 'T' in draft['expires_at']
    assert draft['word_revision'] == 1
    assert draft['retention_days_remaining'] == 30


def test_verification_clause_in_docx():
    """Verify formal statutory verification clause (सत्यापन) exists in generated Word doc."""
    import io
    from docx import Document
    d = fixture()
    token = canonical_hash(d)
    blob = create_docx(d, token, review_confirmed=True)
    doc = Document(io.BytesIO(blob))
    text = '\n'.join(p.text for p in doc.paragraphs)
    assert 'सत्यापन' in text
    assert 'प्रतिज्ञापूर्वक लिहून देतो/देते' in text
    assert 'ठिकाण :' in text
    assert 'वादी/वादींची स्वाक्षरी :' in text


def test_devanagari_and_marathi_width_parsing():
    """Verify Marathi Devanagari digits and unit suffixes parse cleanly without error."""
    d = fixture()
    d['width_ft'] = '१० फूट'
    d['length_ft'] = '१५० फूट'
    governed = validate(d)
    draft = make_draft(governed)
    p3 = next(p for p in draft['paragraphs'] if p['number'] == 3)
    assert '10' in p3['text'] or '१०' in p3['text']

    # Also test ASCII with units and pure Devanagari
    d['width_ft'] = '12 ft'
    assert validate(d)

    d['width_ft'] = '१५.५'
    assert validate(d)


def test_width_missing_or_invalid_errors():
    """Verify missing width produces mandatory error, and negative produces positive number error."""
    d = fixture()
    d['width_ft'] = ''
    with pytest.raises(ValidationError) as exc:
        validate(d)
    assert any('अडथळ्यापूर्वीची अंदाजे सरासरी रुंदी (फूट) अनिवार्य आहे.' in err for err in exc.value.errors)

    d['width_ft'] = '-5'
    with pytest.raises(ValidationError) as exc:
        validate(d)
    assert any('अडथळ्यापूर्वीची अंदाजे सरासरी रुंदी (फूट) सकारात्मक अंकात द्या.' in err for err in exc.value.errors)
