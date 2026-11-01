"""Section 5 local prototype: deterministic, user-sourced content only.
NOT AI, not legal advice, not court-ready. Approved rule IDs stay fixed.
"""
from __future__ import annotations
import datetime, hashlib, io, json, uuid
from datetime import date
from pathlib import Path
from typing import Any
from docx import Document
from docx.shared import Cm, Pt
from .reference_rules import select_prayers, limitation_mode, export_label, InvalidForm, S7_REASON_LABELS

BASE = Path(__file__).resolve().parent.parent
S7 = json.loads((BASE/'source_baseline/S7_FINAL_APPROVED_RULES.json').read_text(encoding='utf-8'))
CONTRACT = json.loads((BASE/'source_baseline/MASTER_IMPLEMENTATION_CONTRACT.json').read_text(encoding='utf-8'))
EVIDENCE = [
 'रस्ता दर्शविणारा नकाशा','महसूल/न्यायालयीन आदेश','रस्त्याचा उल्लेख असलेले नोंदणीकृत दस्त',
 'शासकीय योजनेतील रस्त्याचा दस्तऐवज','जुने फोटो','साक्षीदार','इतर',
]
ATTEMPTS = [
 'प्रतिवादींना वैयक्तिक विनंती','गावातील प्रतिष्ठित व्यक्ती/मध्यस्थांमार्फत',
 'ग्रामपंचायत/तंटामुक्ती/महसूल अधिकारी','पोलिस तक्रार'
]
RESPONSES = ['नकार','आश्वासन देऊन पालन नाही','तात्पुरता अडथळा दूर करून पुन्हा अडथळा','प्रतिसाद नाही']
STATUS_TEXT = {
 1:'अडथळा पूर्वीप्रमाणेच कायम आहे.',
 2:'अडथळा काही प्रमाणात दूर झाला आहे; परंतु रस्त्याच्या वापरात अजूनही अडचण आहे.',
 3:'भौतिक अडथळा दूर झाला आहे; परंतु भविष्यात पुन्हा अडथळा निर्माण होऊ नये म्हणून मनाई आदेशाची मागणी करावयाची आहे.'
}
CROP = {'standing':'उभी पिके','not_grown':'अडथळ्यामुळे पीक घेता आलेले नाही',
        'planned':'सध्या पीक नाही; पीक घेण्याचे नियोजन आहे',
        'harvested':'काढलेला शेतमाल शेतात आहे', 'other':'इतर परिस्थिती'}

# Approved 7 aliases from V30 Register (A4 Gate)
APPROVED_ALIASES = {
    'MC5_URGENCY_3_SUBOPTIONS': 'reason3_details',
    'MC5_HARVESTED_STOCK': 'harvested_stock',
    'MC5_FARM_HOUSE_CONFIRMED': 'house_confirmed',
    'MC5_URGENCY_4_DAMAGE_STATUS': 'reason4_damage',
    'MC5_URGENT_HEARING_OPTIN': 'urgent_hearing',
    'MC5_FINAL_CONSENT': 'review_confirmed',
    'MC5_APP_SERIAL': 'app_number',
}

# Register V30 canonical field mapping to engine internal fields
REGISTER_CANONICAL_MAP = {
    'MC5_VILLAGE': 'village',
    'MC5_TALUKA': 'taluka',
    'MC5_DISTRICT': 'district',
    'MC5_MAP_ACK': 'map_ack',
    'MC5_PLAINTIFFS': 'plaintiffs',
    'MC5_DEFENDANTS': 'defendants',
    'MC5_LAND_RECORDS': 'land_records',
    'MC5_ROUTE_GATS': 'route_gats',
    'MC5_ROAD_WIDTH_FT': 'width_ft',
    'MC5_ROAD_LENGTH_FT': 'length_ft',
    'MC5_PREEXISTING_USE': 'preexisting_use',
    'MC5_ROUTE_DESCRIPTION': 'route_description',
    'MC5_VILLAGE_ROAD_CONFIRMED': 'village_road_confirmed',
    'MC5_OBSTRUCTION_DATE': 'obstruction_date',
    'MC5_OBSTRUCTION_GAT': 'obstruction_gat',
    'MC5_OBSTRUCTION_GAT_CONFIDENCE': 'obstruction_gat_confidence',
    'MC5_OBSTRUCTOR_ROLE': 'obstructor_role',
    'MC5_OBSTRUCTION_TYPES': 'obstruction_description',
    'MC5_CURRENT_STATUS': 'status',
    'MC5_ACCESS_EFFECT': 'access_effect',
    'MC5_SPECIFIC_HARM': 'specific_harm',
    'MC5_CROP_STATUS': 'crop_status',
    'MC5_HARVESTED_PRODUCE': 'harvested_stock',
    'MC5_DAMAGE_ACTUAL': 'specific_harm',
    'MC5_EVIDENCE_TYPES': 'evidence',
    'MC5_UPLOADED_DOCS': 'attached_docs',
    'MC5_ATTEMPTS_MADE': 'attempts_made',
    'MC5_ATTEMPT_TYPES': 'attempt_types',
    'MC5_DEFENDANT_RESPONSE': 'defendant_response',
    'MC5_URGENCY_REASONS': 'urgency_reasons',
    'MC5_REASON3_DETAILS': 'reason3_details',
    'MC5_REASON4_DAMAGE': 'reason4_damage',
    'MC5_REASON5_HOUSE': 'house_confirmed',
    'MC5_URGENT_HEARING': 'urgent_hearing',
    'MC5_FILING_DATE': 'filing_date',
    'MC5_REVIEW_CONSENT': 'review_confirmed',
    'MC5_DRAFT_ID': 'draft_id',
    'MC5_STARTED_AT': 'started_at',
    'MC5_APP_NUMBER': 'app_number',
    'MC5_WORD_REVISION': 'word_revision',
}

def resolve_field_aliases(data: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Resolves V30 register aliases and canonical MC5_ keys with conflict detection."""
    d = dict(data)
    errors = []

    def _is_conflict(v1, v2):
        if v1 is None or v2 is None:
            return False
        if v1 == v2:
            return False
        if isinstance(v1, str) and isinstance(v2, str):
            return v1.strip() != v2.strip()
        if isinstance(v1, list) and isinstance(v2, list):
            return v1 != v2
        return True

    # 1. Resolve approved aliases
    for alias, canonical in APPROVED_ALIASES.items():
        if alias in d:
            val = d[alias]
            if canonical in d and d[canonical] is not None:
                if _is_conflict(val, d[canonical]):
                    errors.append(f"Alias conflict: '{alias}' value conflicts with canonical '{canonical}'.")
            else:
                d[canonical] = val

    # 2. Resolve register MC5_ keys
    for reg_key, canonical in REGISTER_CANONICAL_MAP.items():
        if reg_key in d:
            val = d[reg_key]
            if canonical in d and d[canonical] is not None:
                if _is_conflict(val, d[canonical]):
                    errors.append(f"Register key conflict: '{reg_key}' value conflicts with canonical '{canonical}'.")
            else:
                d[canonical] = val

    return d, errors

class ValidationError(ValueError):
 def __init__(self, errors):
  self.errors = errors
  super().__init__('; '.join(errors))

def _text(x):return str(x or '').strip()
def _bool(x):return type(x) is bool

DEVANAGARI_DIGITS_TABLE = str.maketrans('०१२३४५६७८९', '0123456789')

def _num_positive(x, label, errors, required=True):
 if x in ('', None):
  if required: errors.append(label+' अनिवार्य आहे.')
  return None
 try:
  s = str(x).strip().translate(DEVANAGARI_DIGITS_TABLE).replace(',', '.')
  import re
  m = re.search(r'([-+]?\d+(?:\.\d+)?)', s)
  if m:
   value = float(m.group(1))
  else:
   value = float(s)
  if not (0 < value < 1_000_000):raise ValueError()
  return value
 except (ValueError, TypeError):
  errors.append(label+' सकारात्मक अंकात द्या.');return None

def _valid_date(x):
 try:return date.fromisoformat(x)
 except (ValueError, TypeError):return None

def validate(payload:dict[str,Any]) -> dict[str,Any]:
 """Canonicalizes only input shape; never silently changes a user's selected facts."""
 if not isinstance(payload, dict):raise ValidationError(['माहितीचा नमुना चुकीचा आहे.'])
 d, alias_errors = resolve_field_aliases(payload)
 errors = list(alias_errors)
 if d.get('map_ack') is not True:errors.append('नकाशाविषयक सूचना वाचल्याची पुष्टी आवश्यक आहे.')
 for f,label in [('village','गाव'),('taluka','तालुका'),('district','जिल्हा'),
                 ('route_description','रस्त्याचा प्रत्यक्ष मार्ग'),('preexisting_use','रस्त्याचा पूर्वीचा प्रत्यक्ष वापर'),
                 ('obstruction_description','अडथळ्याचे स्वरूप'),('obstruction_gat','अडथळ्याचा गट')]:
  if not _text(d.get(f)):errors.append(label+' अनिवार्य आहे.')
  import re
  if d.get('width_ft') is not None:
   d['width_ft'] = re.sub(r'\s*(फूट|ft|feet).*$', '', str(d['width_ft']), flags=re.I).strip()
  if d.get('length_ft'):
   d['length_ft'] = re.sub(r'\s*(फूट|ft|feet).*$', '', str(d['length_ft']), flags=re.I).strip()
  _num_positive(d.get('width_ft'),'अडथळ्यापूर्वीची अंदाजे सरासरी रुंदी (फूट)',errors)
  _num_positive(d.get('length_ft'),'अंदाजे लांबी (फूट)',errors,required=False)
 if d.get('obstruction_gat_confidence') not in ('exact','approximate'):errors.append('अडथळ्याचा गट निश्चित की अंदाजे ते निवडा.')
 if d.get('obstructor_role') not in ('स्वतः खातेदार','खातेदाराचा प्रतिनिधी'):errors.append('अडथळा करणाऱ्याची भूमिका निवडा.')
 if not _valid_date(d.get('obstruction_date')):errors.append('अडथळ्याची तारीख वैध द्या.')
 if not _valid_date(d.get('filing_date')):errors.append('अर्जाची तारीख वैध द्या.')
 try:d['status']=int(d.get('status'))
 except (TypeError,ValueError):errors.append('अडथळ्याची सद्यस्थिती निवडा.');d['status']=0
 if d['status'] not in STATUS_TEXT:errors.append('अडथळ्याचे तीन मंजूर पर्यायांपैकी एक निवडा.')
 if d['status'] in (1,2) and not _text(d.get('access_effect')):errors.append('रस्त्याच्या वापरावर झालेला परिणाम नमूद करा.')
 for key,label in [('plaintiffs','वादी'),('defendants','प्रतिवादी')]:
  arr=d.get(key)
  if not isinstance(arr,list) or not arr:errors.append('किमान एक '+label+' आवश्यक आहे.');continue
  if len(arr)>20:errors.append(label+' ची संख्या चाचणी मर्यादेबाहेर आहे.')
  for i,p in enumerate(arr):
   if not isinstance(p,dict):errors.append(label+' माहिती चुकीची आहे.');continue
   for k,n in [('name','नाव'),('address','पत्ता'),('gat','गट क्रमांक'),('cultivable','लागवडीलायक क्षेत्र'),('potkharab','पोटखराब'),('assessment','आकार')]:
    if not _text(p.get(k)):errors.append(f'{label} {i+1} — {n} आवश्यक आहे (नसल्यास ० द्या).')
   # Decimal representation sourced from records, never recompute or synthesize.
 if not isinstance(d.get('village_road_confirmed'),bool):errors.append('गाव रस्त्याशी जोड असल्याची पुष्टी होय/नाही द्या.')
 if d.get('crop_status') not in CROP:errors.append('पीकस्थिती निवडा.')
 reasons=d.get('urgency_reasons') or []
 if not isinstance(reasons,list) or any(type(x) is not int or x not in (1,2,3,4,5,6) for x in reasons):
  errors.append('तातडीचे कारण चुकीचे आहे.');reasons=[]
 if len(reasons)!=len(set(reasons)):errors.append('तातडीचे कारण पुनरावृत्तीने निवडू नका.')
 allowed=set([5,6])
 crop=d.get('crop_status')
 if crop in ('not_grown','planned'):allowed.add(1)
 if crop=='standing':allowed.update([2,3,4])
 if crop=='harvested' or d.get('harvested_stock') is True:allowed.add(3)
 if any(r not in allowed for r in reasons):errors.append('निवडलेले तातडीचे कारण पीकस्थितीशी जुळत नाही.')
 if 3 in reasons and not d.get('reason3_details'):errors.append('कारण ३ चे किमान एक उपकारण निवडा.')
 if 3 not in reasons and d.get('reason3_details'):errors.append('कारण ३ काढल्यावर त्याचे उपपर्यायही काढा.')
 if any(x not in S7['reasons'][2]['suboptions'] for x in (d.get('reason3_details') or [])):errors.append('कारण ३ चा अमान्य उपपर्याय.')
 if 4 in reasons and d.get('reason4_damage') not in S7['reasons'][3]['suboptions']:errors.append('कारण ४ साठी नुकसानीची सद्यस्थिती निवडा.')
 if 4 not in reasons and d.get('reason4_damage'):errors.append('कारण ४ काढल्यावर नुकसानीचा उपप्रश्न काढा.')
 if 5 in reasons and d.get('house_confirmed') is not True:errors.append('शेतातील घराची पुष्टी नसल्यास कारण ५ वापरता येणार नाही.')
 if 5 not in reasons and d.get('house_confirmed') is True:errors.append('घराची पुष्टी कारण ५ निवडल्यावरच वापरा.')
 if reasons and not _bool(d.get('urgent_hearing')):errors.append('तातडीची सुनावणी स्वतंत्र होय/नाही निवडणे आवश्यक आहे.')
 if not reasons and d.get('urgent_hearing') is True:errors.append('तातडीचे कारण नसताना तातडीची मागणी जोडता येणार नाही.')
 for f,validset in [('evidence',EVIDENCE),('attached_docs',EVIDENCE),('attempt_types',ATTEMPTS)]:
  items=d.get(f) or []
  if not isinstance(items,list) or any(x not in validset for x in items):errors.append(f+' मधील पर्याय अमान्य आहेत.')
 if not set(d.get('attached_docs') or []).issubset(set(d.get('evidence') or [])):
  errors.append('जोडलेली कागदपत्रे उपलब्ध पुराव्यांमध्ये निवडलेली असणे आवश्यक आहे.')
 if 'साक्षीदार' in (d.get('attached_docs') or []):
  errors.append('साक्षीदार हा प्रत्यक्ष कागदपत्र-जोडपत्र म्हणून जोडता येत नाही.')
 p_names = {_text(p.get('name')) for p in (d.get('plaintiffs') or []) if _text(p.get('name'))}
 d_names = {_text(p.get('name')) for p in (d.get('defendants') or []) if _text(p.get('name'))}
 common_names = p_names.intersection(d_names)
 if common_names:
  errors.append(f'एकाच व्यक्तीला दोन्ही बाजूंस (वादी व प्रतिवादी) निवडता येत नाही: {", ".join(common_names)}')
 if d.get('attempts_made') is True:
  if not d.get('attempt_types'):errors.append('केलेले प्रयत्न निवडा.')
  if d.get('defendant_response') not in RESPONSES:errors.append('प्रतिवादींचा प्रतिसाद निवडा.')
 elif d.get('attempt_types') or d.get('defendant_response'):
  errors.append('प्रयत्न झाले नसतील तर त्यांच्याशी संबंधित उत्तरे काढा.')
 if errors:raise ValidationError(errors)
 try:d['prayers']=select_prayers(d['status'],reasons,d.get('urgent_hearing'))
 except InvalidForm as exc:raise ValidationError([str(exc)]) from exc
 d['limitation']=limitation_mode(d['obstruction_date'],d['filing_date'])
 return d

def draft_paragraphs(d):
 v=d['village'];t=d['taluka'];district=d['district'];plain=d['plaintiffs'];defs=d['defendants']
 plain_gats=', '.join(str(x['gat']) for x in plain)
 def_gats=', '.join(str(x['gat']) for x in defs)
 obs_gat=str(d.get('obstruction_gat') or def_gats)
 route_gats=str(d.get('route_gats') or obs_gat)
 gat_conf='अंदाजे गट क्रमांक' if d.get('obstruction_gat_confidence')=='approximate' else 'गट क्रमांक'
 p={}

 # P01: जमिनींचा संबंध
 p[1]=f'१) वादी व प्रतिवादी यांच्या संबंधित शेतजमिनींचा तपशील अर्जाच्या प्रारंभी दिलेल्या मिळकतीच्या वर्णनात नमूद केलेला आहे. वादी हे त्यांच्या संबंधित शेतजमिनीची वहिवाट करून शेती व्यवसाय करीत आहेत. सदर शेतजमिनीमध्ये जाण्या-येण्यासाठी तसेच शेतीविषयक कामकाजासाठी वादी हे प्रस्तुत दाव्यात नमूद केलेल्या रस्त्याचा वापर करीत होते. प्रतिवादी यांचा सदर प्रकरणाशी संबंध हा वादी यांच्या वापरातील वादग्रस्त रस्त्याच्या संदर्भात असून, संबंधित रस्ता गट क्रमांक {route_gats} मधून जातो. अशा प्रकारे वादी यांची शेतजमीन, प्रतिवादी यांच्याशी संबंधित जमीन आणि वादग्रस्त रस्ता यांचा परस्पर संबंध आहे. याच रस्त्यावरील अडथळा हा प्रस्तुत दाव्याचा विषय आहे.'

 # P02: रस्त्याचे पूर्वअस्तित्व
 if d.get('preexisting_use_duration'):
  dur=d['preexisting_use_duration']
  if dur=='अलीकडेच तयार झाला आहे' and d.get('preexisting_year'):
   dur_text=f"सुमारे {d['preexisting_year']} पासून"
  elif dur=='निश्चित कालावधी सांगता येत नाही':
   dur_text='अनेक वर्षांपासून'
  else:
   dur_text=dur
 elif d.get('preexisting_use'):
  dur_text=str(d['preexisting_use']).strip()
 else:
  dur_text='अनेक वर्षांपासून'
 gen_text=' वादी यांच्या पूर्वीच्या पिढ्यांकडूनही सदर रस्त्याचा वापर होत आलेला असून, त्यानंतर वादी यांनीही त्याच रस्त्यावरून शेतजमिनीची वहिवाट सुरू ठेवलेली आहे.' if d.get('generational_use') else ''
 p[2]=f'२) वादी यांच्या शेतजमिनीकडे जाण्या-येण्यासाठी प्रस्तुत दाव्यात नमूद केलेला रस्ता हा अडथळा निर्माण होण्यापूर्वीपासून अस्तित्वात असून, वादी यांच्या शेतजमिनीच्या वहिवाटीसाठी त्याचा वापर होत आलेला आहे. वादी हे गेल्या {dur_text} सदर रस्त्यावरून त्यांच्या शेतजमिनीकडे नियमितपणे ये-जा करीत असून, शेतीच्या आवश्यक कामकाजासाठी त्यांची या रस्त्यावरून वहिवाट चालत आलेली आहे.{gen_text} सदर रस्त्याचे अस्तित्व हे केवळ प्रस्तावित किंवा नव्याने मागणी केलेल्या मार्गाच्या स्वरूपाचे नसून, अडथळा निर्माण होण्यापूर्वी वादी यांच्या प्रत्यक्ष वापरातील रस्त्याच्या स्वरूपाचे आहे. त्यामुळे प्रस्तुत दाव्याचा संबंध नवीन रस्ता उपलब्ध करून देण्याशी नसून, अडथळा निर्माण होण्यापूर्वी अस्तित्वात असलेल्या व वादी यांच्या वापरात असलेल्या रस्त्याशी आहे.'

 # P03: रस्त्याचा मार्ग व मोजमाप
 r_desc=d.get('route_description') or f'गट क्रमांक {route_gats} च्या बांधावरून जाणारा मार्ग'
 r_orient=d.get('route_orientation') or f'गट क्र. {route_gats} च्या बांधालगत'
 width=d.get('width_ft')
 length=d.get('length_ft')
 if length not in ('',None):
  dim_text=f'सदर रस्त्याची रुंदी अंदाजे {width} फूट असून, त्याची लांबी {length} फूट आहे.'
 else:
  dim_text=f'सदर रस्त्याची रुंदी अंदाजे {width} फूट आहे.'
 vr_conn=' अशा प्रकारे वादी यांच्या शेतजमिनीपासून गाव रस्त्यापर्यंत हा वहिवाटीचा रस्ता आहे.' if d.get('village_road_confirmed') else ''
 p[3]=f'३) वादी यांच्या शेतजमिनीकडे जाण्यासाठी वापरात असलेला वादग्रस्त रस्ता मौजे {v} येथील गट क्रमांक {route_gats} मधून जात असून, सदर रस्त्याचा मार्ग {r_desc} असा आहे. वादी यांच्या शेतजमिनीच्या संदर्भात सदर रस्त्याचे स्थान व दिशा {r_orient} अशी आहे. {dim_text} वादी यांच्या शेतजमिनीकडे जाण्यासाठी वापरात असलेल्या रस्त्याचा मार्ग हा वरीलप्रमाणे निश्चितपणे वर्णन केलेला असून, प्रस्तुत दाव्यातील अडथळा याच मार्गावरील आहे.{vr_conn}'

 # P04: शेती व रस्त्याचा पूर्वीचा वापर (MANDATORY per Language Bank & Owner Directive)
 crops=d.get('crops') or 'भात व भाजीपाला'
 if isinstance(crops, (list, tuple)):
  crops=', '.join(str(c) for c in crops)
 transit=d.get('transport_modes') or 'पायी, दुचाकी व ट्रॅक्टर'
 if isinstance(transit, (list, tuple)):
  transit=', '.join(str(t) for t in transit)
 p[4]=f'४) वादी हे त्यांच्या संबंधित शेतजमिनीमध्ये {crops} या पिकांची लागवड करून शेती व्यवसाय करीत आहेत. सदर शेतजमिनीची मशागत करणे, पेरणी, लागवड, पिकांची निगा राखणे तसेच शेतीशी संबंधित इतर आवश्यक कामकाज पार पाडण्यासाठी वादी यांना त्यांच्या शेतजमिनीमध्ये वेळोवेळी जाणे-येणे आवश्यक असते. वादी हे अडथळा निर्माण होण्यापूर्वी सदर रस्त्यावरून {transit} यांच्या साहाय्याने शेतजमिनीकडे नियमितपणे ये-जा करीत होते. शेतीसाठी आवश्यक बियाणे, खते, औषधे, कृषी अवजारे व इतर साहित्य शेतजमिनीमध्ये नेण्यासाठी तसेच शेतात उत्पादित झालेला शेतीमाल बाहेर आणण्यासाठी सदर रस्त्याचा वापर केला जात होता. सदर रस्त्यावरून होणारी ये-जा ही केवळ प्रसंगोपात स्वरूपाची नसून वादी यांच्या शेतीच्या नियमित कामकाजाशी संबंधित होती. अशा प्रकारे वादग्रस्त रस्ता हा अडथळा निर्माण होण्यापूर्वी वादी यांच्या शेतजमिनीच्या प्रत्यक्ष वहिवाटीसाठी वापरात असलेला रस्ता होता.'

 # P05: अडथळ्याची तारीख व ठिकाण
 obs_date_fmt=date.fromisoformat(d['obstruction_date']).strftime('%d/%m/%Y')
 obs_loc=d.get('obstruction_location_desc') or f'गट क्र. {d["obstruction_gat"]} मधील रस्त्याच्या भागावर'
 p[5]=f'५) वादी यांच्या शेतजमिनीकडे जाण्यासाठी पूर्वीपासून अस्तित्वात असलेल्या व त्यांच्या प्रत्यक्ष वहिवाटीत असलेल्या रस्त्यावर प्रतिवादी यांनी दिनांक {obs_date_fmt} रोजी अडथळा निर्माण केला. सदर अडथळा मौजे {v}, तालुका {t}, जिल्हा {district} येथील {gat_conf} {d["obstruction_gat"]} मधून जाणाऱ्या रस्त्याच्या भागात निर्माण करण्यात आलेला आहे. अडथळ्याचे स्थान {obs_loc} असे असून, सदर ठिकाण हे वादी यांच्या शेतजमिनीकडे जाणाऱ्या व पूर्वीपासून वापरात असलेल्या रस्त्याच्या मार्गावरच येते. प्रतिवादी यांनी अडथळा निर्माण करण्यापूर्वी वादी हे याच मार्गावरून त्यांच्या शेतजमिनीकडे जाण्या-येण्याची वहिवाट करीत होते. त्यामुळे प्रतिवादी यांनी अडथळा निर्माण केलेला भाग हा नव्याने रस्ता मागितलेला भाग नसून, वादी यांच्या पूर्वीच्या प्रत्यक्ष वापरातील रस्त्याचाच भाग आहे. अशा प्रकारे दिनांक {obs_date_fmt} रोजी प्रतिवादी यांनी सदर ठिकाणी निर्माण केलेला अडथळा ही प्रस्तुत दावा दाखल करण्यास कारणीभूत ठरलेली घटना आहे.'

 # P06: अडथळ्याचे स्वरूप व सद्यस्थिती
 obs_desc=d.get('obstruction_description') or 'दगड व मातीचा भराव टाकून वहिवाट अडवली'
 access_diff=d.get('access_effect') or 'वाहतूक व ये-जा सुरळीतपणे न करता येण्याची'
 if d['status']==1:
  stat_block='प्रतिवादी यांनी निर्माण केलेला सदर अडथळा अद्याप पूर्वीप्रमाणेच कायम आहे. त्यामुळे वादी यांना अडथळा निर्माण होण्यापूर्वी ज्या प्रकारे रस्त्याचा वापर करता येत होता, त्या प्रकारे त्याची वहिवाट करता येत नाही. सदर अडथळा दूर करून पूर्वीच्या रस्त्यावरील वहिवाट पूर्ववत होण्यासाठी वादी यांना न्यायालयाकडे दाद मागणे आवश्यक झाले आहे.'
 elif d['status']==2:
  stat_block='प्रतिवादी यांनी निर्माण केलेला अडथळा काही प्रमाणात दूर झालेला असला, तरी उर्वरित अडथळ्यामुळे वादी यांच्या रस्त्याच्या वापरातील अडचण पूर्णतः दूर झालेली नाही. परिणामी, वादी यांना सदर रस्त्याचा अडथळा निर्माण होण्यापूर्वीप्रमाणे वापर करता येत नाही. उर्वरित अडथळ्याच्या संदर्भात वादी यांना न्यायालयाकडे दाद मागणे आवश्यक झाले आहे.'
 else:
  stat_block='प्रतिवादी यांनी निर्माण केलेला भौतिक अडथळा सध्या पूर्णतः दूर झालेला आहे. तथापि, पूर्वी निर्माण झालेल्या अडथळ्याच्या घटनेच्या अनुषंगाने वादी हे सदर रस्त्यावर भविष्यात पुन्हा अडथळा निर्माण होऊ नये यासाठी मनाई आदेशाची मागणी करीत आहेत. सदर मागणीचा निर्णय पूर्वीच्या घटनेची वस्तुस्थिती आणि उपलब्ध कायदेशीर आधार विचारात घेऊन करण्यात यावा, अशी वादी यांची विनंती आहे.'
 p[6]=f'६) प्रतिवादी यांनी वादी यांच्या पूर्वीपासूनच्या प्रत्यक्ष वापरातील वादग्रस्त रस्त्यावर {obs_desc} अशा प्रकारे अडथळा निर्माण केलेला आहे. सदर अडथळा हा परिच्छेद क्रमांक ५ मध्ये नमूद केलेल्या ठिकाणी निर्माण करण्यात आलेला असून, त्यामुळे वादी यांच्या पूर्वीपासून चालत आलेल्या रस्त्याच्या वहिवाटीत व्यत्यय निर्माण झाला. प्रतिवादी यांच्या सदर कृतीमुळे वादी यांना पूर्वीप्रमाणे सदर मार्गावरून ये-जा करण्यास {access_diff} अशी अडचण निर्माण झाली. {stat_block} अशा प्रकारे प्रतिवादी यांनी निर्माण केलेल्या अडथळ्याचे स्वरूप, त्याचा वादी यांच्या वहिवाटीवर झालेला परिणाम आणि त्याची सद्यस्थिती ही प्रस्तुत दाव्यात विचारार्थ असलेली बाब आहे.'

 # P07: रस्त्याच्या वापरावरील परिणाम
 disrupt='कायम असलेली बाधा' if d['status'] in (1,2) else 'झालेली बाधा'
 p[7]=f'७) प्रतिवादी यांनी वादग्रस्त रस्त्यावर निर्माण केलेल्या अडथळ्यामुळे वादी यांच्या शेतजमिनीकडे जाण्या-येण्याच्या पूर्वीपासून चालत आलेल्या वहिवाटीत प्रत्यक्ष बाधा निर्माण झाली आहे. सदर अडथळा निर्माण होण्यापूर्वी वादी हे त्यांच्या शेतीविषयक गरजांनुसार या रस्त्यावरून {transit} अशा प्रकारे ये-जा करीत होते. तथापि, प्रतिवादी यांच्या सदर कृतीमुळे रस्त्याच्या पूर्वीच्या वापरावर मर्यादा निर्माण होऊन {access_diff} अशी परिस्थिती निर्माण झाली. त्यामुळे वादी यांना त्यांच्या शेतजमिनीकडे जाण्यासाठी पूर्वी उपलब्ध असलेल्या रस्त्याचा वापर पूर्ववत स्वरूपात करता येत नाही. सदर बाधा ही केवळ रस्त्याच्या भौतिक स्थितीपुरती मर्यादित नसून, वादी यांच्या शेतजमिनीकडे होणाऱ्या प्रत्यक्ष ये-जा व वाहतुकीवर परिणाम करणारी आहे. अशा प्रकारे प्रतिवादी यांनी निर्माण केलेल्या अडथळ्यामुळे वादी यांच्या पूर्वीच्या रस्त्याच्या वापरात {disrupt} निर्माण झाली आहे.'

 # P08: अडचणी व नुकसान
 farm_diff=d.get('farm_work_affected') or 'शेतीची नियमित मशागत व वाहतूक'
 machinery=' शेतीची मशागत करण्यासाठी आवश्यक ट्रॅक्टर, कृषी अवजारे व इतर साधनसामग्री शेतजमिनीमध्ये नेणे, तसेच खते, बियाणे व औषधे पोहोचवणे या कामांमध्ये अडचणी निर्माण झाल्या आहेत.'
 produce=' शेतात तयार झालेला शेतीमाल बाहेर आणण्याच्या कामातही अडथळा निर्माण झाल्यामुळे शेतीमालाच्या वाहतुकीवर प्रतिकूल परिणाम झाला आहे.' if (d.get('harvested_stock') or d.get('crop_status')=='harvested') else ''
 harm=f' या परिस्थितीमुळे वादी यांना {d["specific_harm"]} सहन करावी लागली आहे.' if d.get('specific_harm') else ''
 p[8]=f'८) प्रतिवादी यांनी वादग्रस्त रस्त्यावर निर्माण केलेल्या अडथळ्यामुळे वादी यांच्या शेतजमिनीतील नियमित शेतीविषयक कामकाजात प्रत्यक्ष अडचणी निर्माण झाल्या आहेत. सदर अडथळ्यामुळे वादी यांना {farm_diff} ही कामे पूर्वीप्रमाणे सुरळीतपणे पार पाडता येत नाहीत.{machinery}{produce}{harm} अशा प्रकारे प्रतिवादी यांच्या कृतीचा परिणाम केवळ रस्त्यावरील ये-जा करण्यापुरता मर्यादित न राहता वादी यांच्या शेतीच्या नियमित कामकाजावर व त्यासंबंधित व्यवहारांवरही झाला आहे.'

 # P09: तातडीची कारणे (Omitted if no urgency confirmed)
 reasons=d.get('urgency_reasons') or []
 if reasons and d.get('urgent_hearing') is True:
  r_labels=' '.join(S7_REASON_LABELS.get(r,'') for r in reasons if r in S7_REASON_LABELS)
  if d.get('reason3_details'):r_labels+=' '+' '.join(d['reason3_details'])
  if d.get('reason4_damage'):r_labels+=' '+d['reason4_damage']
  if d['status']==3:
   impact_text='सदर भौतिक अडथळा सध्या दूर झालेला असला तरी भविष्यात पुन्हा अडथळा निर्माण झाल्यास शेतीकामांचे मोठे नुकसान होण्याची शक्यता असल्याने ही वेळेची निकड निर्माण झाली आहे.'
  else:
   impact_text='तथापि, सदर अडथळ्यामुळे शेतीकामांवर प्रत्यक्ष परिणाम झालेला आहे.'
  p[9]=f'९) प्रतिवादी यांनी वादग्रस्त रस्त्यावर निर्माण केलेल्या अडथळ्यामुळे वादी यांच्या शेतजमिनीतील आवश्यक शेतीविषयक कामकाजाच्या अनुषंगाने तातडीची परिस्थिती निर्माण झाली आहे. सद्यस्थितीत {r_labels} ही कामे करणे आवश्यक असून, त्यासाठी वादी यांना त्यांच्या पूर्वीच्या वापरातील रस्त्यावरून {transit} या प्रकारे ये-जा करणे आवश्यक आहे. {impact_text} त्यामुळे वादी यांच्या शेतीविषयक कामकाजाची वेळेची निकड आणि वादग्रस्त रस्त्याच्या वापराची आवश्यकता विचारात घेता, प्रस्तुत प्रकरणाची तातडीने सुनावणी होऊन कायद्यानुसार अंतिम निर्णय होणे आवश्यक आहे.'

 # P10: रस्त्याच्या अस्तित्वाचे पुरावे
 ev_list=', '.join(d['evidence']) if d.get('evidence') else 'गाव नकाशा व जुने पुरावे'
 wit_text=' तसेच सदर रस्त्याचे पूर्वअस्तित्व व त्यावरून चालत आलेल्या वहिवाटीबाबत माहिती असलेले साक्षीदारही वादी यांच्याकडे उपलब्ध असून, आवश्यकतेनुसार त्यांचा पुरावा न्यायालयासमोर सादर करण्यात येईल.' if ('साक्षीदार' in (d.get('evidence') or [])) else ''
 att_text=f' यांपैकी {", ".join(d["attached_docs"])} या कागदपत्रांच्या प्रती प्रस्तुत अर्जासोबत जोडण्यात आलेल्या असून, त्यांचा तपशील जोडलेल्या कागदपत्रांच्या यादीत स्वतंत्रपणे नमूद केला आहे.' if d.get('attached_docs') else ''
 p[10]=f'१०) वादी यांच्या शेतजमिनीकडे जाण्यासाठी प्रस्तुत दाव्यात नमूद केलेला वादग्रस्त रस्ता हा अडथळा निर्माण होण्यापूर्वीपासून अस्तित्वात असून, सदर रस्त्यावरून वादी यांची प्रत्यक्ष वहिवाट चालत आलेली होती. या रस्त्याचे पूर्वअस्तित्व, त्याचा मार्ग, स्थान तसेच त्यावरून पूर्वीपासून चालत आलेली वहिवाट या बाबींच्या समर्थनार्थ वादी यांच्याकडे {ev_list} असे पुरावे उपलब्ध आहेत.{wit_text} सदर उपलब्ध पुरावे हे वादग्रस्त रस्त्याच्या अस्तित्वाशी, त्याच्या प्रत्यक्ष मार्गाशी अथवा त्यावरील पूर्वीच्या वापराशी संबंधित असून, वादी यांनी नमूद केलेल्या रस्त्याच्या वहिवाटीस पुष्टी देण्याच्या दृष्टीने महत्त्वाचे आहेत.{att_text} त्यामुळे प्रस्तुत दाव्यातील वादग्रस्त रस्त्याचे पूर्वअस्तित्व, त्याचा मार्ग आणि वादी यांची पूर्वीची वहिवाट निश्चित करताना सदर उपलब्ध पुरावे व आवश्यकतेनुसार साक्षीदारांचा पुरावा विचारात घेण्यात यावा.'

 # P11: पूर्वीचे प्रयत्न व प्रतिसाद (Omitted if attempts_made is False)
 if d.get('attempts_made'):
  att_types=', '.join(d.get('attempt_types') or [])
  resp=d.get('defendant_response')
  if resp=='नकार':
   resp_desc='प्रतिवादी यांनी अडथळा दूर करण्यास नकार दिल्यामुळे वादी यांच्या प्रयत्नातून प्रश्न सुटू शकला नाही.'
  elif resp=='आश्वासन देऊन पालन नाही':
   resp_desc='प्रतिवादी यांनी अडथळा दूर करण्याचे आश्वासन दिले; तथापि, त्यानुसार अडथळा दूर करण्यात आलेला नाही.'
  elif resp=='तात्पुरता अडथळा दूर करून पुन्हा अडथळा':
   resp_desc='प्रतिवादी यांनी अडथळा काही काळासाठी दूर केला; मात्र त्यानंतर पुन्हा अडथळा निर्माण केल्यामुळे रस्त्याच्या वापरास अडचण निर्माण झाली.'
  else:
   resp_desc='वादी यांनी केलेल्या प्रयत्नांवर प्रतिवादींकडून कोणताही प्रतिसाद प्राप्त झाला नाही.'
  p[11]=f'११) प्रतिवादी यांनी वादी यांच्या पूर्वीपासूनच्या वहिवाटीच्या रस्त्यावर अडथळा निर्माण केल्यानंतर सदर अडथळा दूर होऊन वादी यांची रस्त्यावरील पूर्ववत वहिवाट सुरू व्हावी, या उद्देशाने वादी यांनी {att_types} असे प्रयत्न केले. सदर प्रयत्नांद्वारे वादी यांनी रस्त्याच्या वापरास निर्माण झालेली अडचण दूर करण्यासाठी उपलब्ध मार्गांचा अवलंब केला. {resp_desc} तथापि, वादी यांनी केलेल्या प्रयत्नांनंतरही रस्त्यावरील अडचण कायम राहिली आहे. अशा प्रकारे वादी यांनी केलेले प्रयत्न, त्यावर प्रतिवादी यांनी घेतलेली भूमिका आणि त्यानंतरची परिस्थिती विचारात घेता, वादग्रस्त रस्त्याच्या वापरासंबंधी निर्माण झालेला प्रश्न न्यायालयीन निर्णयासाठी उपस्थित झाला असून, वादी यांना प्रस्तुत दाव्याद्वारे कायद्यानुसार दाद मागणे आवश्यक झाले आहे.'

 # P12: दाव्यास कारण (Strictly heading १२) दाव्यास कारण : )
 att_p12=''
 if d.get('attempts_made'):
  att_p12=f' सदर अडथळा दूर करण्यासाठी वादी यांनी त्यानंतर {att_types} असे प्रयत्न केले; तथापि, वादी यांच्या प्रयत्नांनंतरही {resp_desc}'
 if d['status']==1:
  stat_p12='सदर अडथळा अद्याप पूर्वीप्रमाणेच कायम असून, वादी यांना रस्त्यावरील पूर्वीची वहिवाट करता येत नाही.'
 elif d['status']==2:
  stat_p12='सदर अडथळा काही प्रमाणात दूर झालेला असला तरी उर्वरित अडथळ्यामुळे वादी यांच्या रस्त्याच्या वापरातील अडचण अद्याप पूर्णतः दूर झालेली नाही.'
 else:
  stat_p12='सदर भौतिक अडथळा सध्या पूर्णतः दूर झालेला आहे. तथापि, पूर्वी घडलेल्या अडथळ्याच्या घटनेच्या अनुषंगाने भविष्यात पुन्हा अडथळा निर्माण होऊ नये यासाठी वादी हे कायद्यानुसार मनाई आदेशाची मागणी करीत आहेत.'
 p[12]=f'१२) दाव्यास कारण : प्रतिवादी यांनी दिनांक {obs_date_fmt} रोजी मौजे {v} येथील {gat_conf} {d["obstruction_gat"]} मधून जाणाऱ्या व वादी यांच्या पूर्वीपासून प्रत्यक्ष वापरात असलेल्या रस्त्यावर {obs_desc} अशा प्रकारे अडथळा निर्माण केला. सदर कृतीमुळे वादी यांच्या शेतजमिनीकडे जाण्या-येण्याच्या पूर्वीपासून चालत आलेल्या वहिवाटीत बाधा निर्माण झाली आणि त्याच दिवशी प्रस्तुत दाव्यास कारण उत्पन्न झाले.{att_p12} {stat_p12} अशा प्रकारे प्रतिवादी यांनी निर्माण केलेल्या अडथळ्याची मूळ घटना, त्यानंतरची पुष्टी झालेली परिस्थिती आणि वादी यांच्या रस्त्याच्या वापराशी संबंधित निर्माण झालेला वाद विचारात घेता, वादी यांना प्रस्तुत दावा दाखल करून मा. न्यायालयाकडे कायद्यानुसार दाद मागणे आवश्यक झाले आहे.'

 # P13: अधिकारक्षेत्र व मुदत
 lim_sentence=''
 if d.get('limitation',{}).get('mode')=='VERIFIED_AFFIRMATIVE':
  lim_sentence=' तसेच प्रतिवादी यांनी सदर रस्त्यावर अडथळा निर्माण केल्यापासून विहित मुदतीत प्रस्तुत दावा दाखल करण्यात येत आहे.'
 p[13]=f'१३) वादग्रस्त रस्ता व अडथळ्याचे ठिकाण मौजे {v}, तालुका {t}, जिल्हा {district} येथे असल्याने प्रस्तुत दावा चालविण्याचे अधिकारक्षेत्र मा. मामलेदार न्यायालय, {t} यांना आहे.{lim_sentence}'

 return [{'number':i,'subject':CONTRACT['paragraphs'][i-1]['subject'],'text':p[i],
          'source_field_ids':paragraph_sources(i)} for i in sorted(p)]

PROVENANCE={
 1:['village','taluka','district','plaintiffs','defendants'],
 2:['preexisting_use','preexisting_use_duration','preexisting_year'],
 3:['plaintiffs','route_description','width_ft','length_ft','village_road_confirmed'],
 4:['crops','crop_status','transport_modes'],
 5:['obstruction_date','obstruction_gat','obstruction_gat_confidence'],
 6:['obstruction_description','status'],
 7:['access_effect','status'],
 8:['specific_harm','farm_work_affected'],
 9:['urgency_reasons','reason3_details','reason4_damage','urgent_hearing'],
 10:['evidence','attached_docs'],
 11:['attempts_made','attempt_types','defendant_response'],
 12:['obstruction_date','obstruction_gat','obstruction_description','status'],
 13:['village','taluka','district','obstruction_date','filing_date']
}
def paragraph_sources(n):return PROVENANCE[n]

def make_draft(input_data):
 d=validate(input_data)
 now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
 if not d.get('draft_id'):
  d['draft_id'] = str(uuid.uuid4())
 if not d.get('started_at'):
  d['started_at'] = now_iso
 if not d.get('word_revision'):
  d['word_revision'] = 1
 try:
  start_dt = datetime.datetime.fromisoformat(d['started_at'])
 except Exception:
  start_dt = datetime.datetime.now(datetime.timezone.utc)
 d['expires_at'] = (start_dt + datetime.timedelta(days=30)).isoformat()
 return {'paragraphs':draft_paragraphs(d),'prayers':d['prayers'],
  'limitation':d['limitation'],'export_label':export_label(d['limitation']),
  'evidence':d.get('evidence') or [], 'attached_docs':d.get('attached_docs') or [],
  'status':d['status'],'review_only':True,
  'draft_id': d.get('draft_id'),
  'started_at': d.get('started_at'),
  'expires_at': d.get('expires_at'),
  'word_revision': d.get('word_revision', 1),
  'app_number': d.get('app_number'),
  'retention_days_remaining': 30,
  'notice':'सॉफ्टवेअरचा चाचणी मसुदा — स्वतंत्र कायदेशीर पुनरावलोकनाशिवाय न्यायालयात दाखल करू नये.'}

def canonical_hash(d:dict)->str:
 cleaned={k:v for k,v in d.items() if k not in ('review_confirmed','preview_token','prayers','limitation')}
 return hashlib.sha256(json.dumps(cleaned,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()

def create_docx(input_data:dict, preview_token:str, review_confirmed:bool, draft_override:dict|None=None)->bytes:
 if review_confirmed is not True:raise ValidationError(['अर्जाचा संपूर्ण मजकूर तपासल्याची स्पष्ट पुष्टी आवश्यक आहे.'])
 if canonical_hash(input_data)!=preview_token:raise ValidationError(['पूर्वावलोकनानंतर माहिती बदलली आहे. पुन्हा पूर्वावलोकन करा.'])
 d=validate(input_data);b=draft_override if draft_override is not None else make_draft(d)
 doc=Document();s=doc.sections[0];s.top_margin=Cm(1.8);s.bottom_margin=Cm(1.8)
 normal=doc.styles['Normal'];normal.font.name='Noto Sans Devanagari';normal.font.size=Pt(10)
 p=doc.add_paragraph();p.alignment=1;p.add_run('AI भाषिक परीक्षण मसुदा — न्यायालयात दाखल करण्यासाठी अंतिम नाही (REVIEW ONLY)' if draft_override is not None else 'चाचणी मसुदा — न्यायालयात दाखल करण्यासाठी अंतिम नाही (REVIEW ONLY)').bold=True
 if d['limitation']['mode']=='REVIEW_ONLY':
  p=doc.add_paragraph('केवळ कायदेशीर पुनरावलोकनासाठी — सहा महिन्यांच्या मुदतीची स्वतंत्र पडताळणी आवश्यक.');p.style='Subtitle'
 doc.add_paragraph(f'मा. मामलेदार न्यायालय, तालुका {d["taluka"]}, जिल्हा {d["district"]}')
 plain_names=', '.join(x['name'] for x in d['plaintiffs'])
 def_names=', '.join(x['name'] for x in d['defendants'])
 doc.add_paragraph(f'वादी : {plain_names}     विरुद्ध     प्रतिवादी : {def_names}')
 doc.add_paragraph('मामलेदार न्यायालय अधिनियम, १९०६ कलम ५ अंतर्गत रस्त्यावरील अडथळ्याबाबत दावा')
 
 # Land table section with approved heading
 doc.add_heading('जमिनीचे वर्णन',level=2)
 table=doc.add_table(rows=1,cols=5);table.style='Table Grid'
 for c,s in zip(table.rows[0].cells,CONTRACT['land_table']['five_columns']):c.text=s
 for group,people in [('वादी',d['plaintiffs']),('प्रतिवादी',d['defendants'])]:
  for person in people:
   cells=table.add_row().cells
   for c,s in zip(cells,[group,d['village'],str(person['gat']),
      f'लागवडीलायक: {person["cultivable"]}\nपोटखराब: {person["potkharab"]}',str(person['assessment'])]):c.text=s
 
 # Paragraphs: Strictly NO internal subject headings in Word document (Owner Directive 12)
 for p in b['paragraphs']:
  doc.add_paragraph(p['text'])
 
 doc.add_paragraph('तरी विनंती की,')
 for prayer in d['prayers']:
  doc.add_paragraph(f'{prayer["display_number"]}) {prayer["text"]}')
 
 # Annexures: Include confirmed document titles only; no unapproved statements if empty (Owner Directive 7)
 attached=[x for x in (d.get('attached_docs') or []) if x!='साक्षीदार']
 if attached:
  doc.add_heading('जोडपत्रे :',level=3)
  for i,x in enumerate(attached,1):doc.add_paragraph(f'{i}) {x}')
 
 doc.add_paragraph('सत्यापन : मी/आम्ही, वर नमूद वादी, प्रतिज्ञापूर्वक लिहून देतो/देते की, वरील दाव्यातील मजकूर माझ्या/आमच्या स्वतःच्या माहितीप्रमाणे व उपलब्ध कागदपत्रांनुसार खरा व बरोबर आहे.')
 doc.add_paragraph(f'ठिकाण : {d["village"]}')
 doc.add_paragraph(f'अर्जाची मसुदा तारीख: {date.fromisoformat(d["filing_date"]).strftime("%d/%m/%Y")}')
 doc.add_paragraph('वादी/वादींची स्वाक्षरी : __________________')
 doc.add_paragraph('तथ्ये, मुदत, हक्क, पुरावे आणि कायदेशीर ग्राह्यता स्वतंत्रपणे पडताळणे आवश्यक आहे.')
 bio=io.BytesIO();doc.save(bio);return bio.getvalue()

