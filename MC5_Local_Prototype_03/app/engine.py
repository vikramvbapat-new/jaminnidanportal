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

def _num_positive(x, label, errors, required=True):
 if x in ('', None):
  if required: errors.append(label+' अनिवार्य आहे.')
  return None
 try:
  value=float(x)
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
 if d['status']==3 and (reasons or d.get('urgent_hearing') is True):errors.append('अडथळा पूर्ण दूर झालेल्या प्रकरणात तातडीची जुनी निवड काढा.')
 allowed=set()
 if d['status'] in (1,2):
  allowed.update([5,6]);crop=d.get('crop_status')
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
 start=', '.join('गट क्र. '+_text(x['gat']) for x in plain)
 gp='गाव रस्त्यापर्यंत' if d['village_road_confirmed'] else 'पुष्टी केलेल्या मार्गाने'
 gat_conf='अंदाजे गट क्रमांक' if d['obstruction_gat_confidence']=='approximate' else 'गट क्रमांक'
 p={}
 p[1]=f'वादी यांची शेतजमीन मौजे {v}, ता. {t}, जि. {district} येथे {start} मध्ये आहे. प्रतिवादी यांच्या शेतजमिनींचा तपशील वरील तक्त्यात नमूद आहे. याच रस्त्यावरील अडथळा हा प्रस्तुत दाव्याचा विषय आहे.'
 p[2]=f'वादी यांच्या शेतजमिनीपर्यंत जाण्यासाठी सदर रस्ता अडथळा निर्माण होण्यापूर्वीपासून वापरात होता. {d["preexisting_use"]}'
 p[3]=f'वादी यांच्या {start} मधील शेतजमिनीपासून सदर वादग्रस्त रस्ता {d["route_description"]} असा जातो. सदर वादग्रस्त रस्त्याची अंदाजे सरासरी रुंदी {d["width_ft"]} फूट आहे.'
 if d.get('length_ft'):p[3]+=f' रस्त्याची अंदाजे लांबी {d["length_ft"]} फूट आहे.'
 if d['village_road_confirmed']:p[3]+=' अशा प्रकारे वादी यांच्या शेतजमिनीपासून गाव रस्त्यापर्यंत हा वहिवाटीचा रस्ता आहे.'
 # Paragraph 4 is omitted here to avoid repeating P02 without distinct verified farming-use facts.
 p[5]=f'दिनांक {date.fromisoformat(d["obstruction_date"]).strftime("%d-%m-%Y")} रोजी मौजे {v} येथील {gat_conf} {d["obstruction_gat"]} मधील वादी यांच्या वापरातील रस्त्यावर प्रतिवादी यांनी अडथळा निर्माण केला.'
 p[6]=f'अडथळ्याचे स्वरूप असे आहे: {d["obstruction_description"]} सद्यस्थिती: {STATUS_TEXT[d["status"]]}'
 if _text(d.get('access_effect')):
  prefix='अडथळ्यामुळे' if d['status'] in (1,2) else 'अडथळ्यामुळे पूर्वी'
  p[7]=f'{prefix} रस्त्याच्या वापरावर पुढील परिणाम झाला: {d["access_effect"]}'
 if _text(d.get('specific_harm')):p[8]=f'वादी यांना पुढील प्रत्यक्ष अडचण झाली: {d["specific_harm"]}'
 if d['status'] in (1,2) and d.get('urgency_reasons') and d.get('urgent_hearing') is True:
  reasons=[S7_REASON_LABELS[r] for r in d['urgency_reasons']]
  p[9]='सदर रस्त्याच्या वापराची तातडीची कारणे पुढीलप्रमाणे आहेत: '+' '.join(reasons)
  if d.get('reason3_details'):p[9]+=' '+' '.join(d['reason3_details'])
  if d.get('reason4_damage'):p[9]+=' '+d['reason4_damage']
  p[9]+=' त्यामुळे प्रस्तुत प्रकरणाची तातडीने सुनावणी घेऊन अंतिम निर्णय देण्यात यावा, अशी वादी यांची विनंती आहे.'
 if d.get('evidence'):p[10]='सदर रस्त्याच्या पूर्वअस्तित्वासंबंधी वादी यांच्याकडे पुढील पुरावे उपलब्ध आहेत: '+', '.join(d['evidence'])+'.'
 if d.get('attempts_made'):
  p[11]='वादी यांनी अडथळ्याच्या प्रश्नावर पुढील प्रयत्न केले: '+', '.join(d['attempt_types'])+'. प्रतिवादींचा प्रतिसाद: '+d['defendant_response']+'.'
 p[12]=f'दिनांक {date.fromisoformat(d["obstruction_date"]).strftime("%d-%m-%Y")} रोजी वादी यांच्या वापरातील रस्त्यावर अडथळा निर्माण झाल्यामुळे' + (' आणि अडथळा दूर करण्याच्या वादी यांच्या प्रयत्नांनंतरही प्रश्न न सुटल्यामुळे' if d.get('attempts_made') else '') + ' प्रस्तुत दाव्यास कारण उत्पन्न झाले.'
 p[13]=f'वादग्रस्त रस्ता व अडथळ्याचे ठिकाण मौजे {v}, तालुका {t}, जिल्हा {district} येथे असल्याने प्रस्तुत दावा चालविण्याचे अधिकारक्षेत्र मा. मामलेदार न्यायालय, {t} यांना आहे.'
 # Deliberately omit the statutory 'filed within time' assertion pending legal verification.
 return [{'number':i,'subject':CONTRACT['paragraphs'][i-1]['subject'],'text':p[i],
          'source_field_ids':paragraph_sources(i)} for i in sorted(p)]

PROVENANCE={1:['village','taluka','district','plaintiffs','defendants'],2:['preexisting_use'],
 3:['plaintiffs','route_description','width_ft','length_ft','village_road_confirmed'],
 4:['preexisting_use'],5:['obstruction_date','obstruction_gat','obstruction_gat_confidence'],
 6:['obstruction_description','status'],7:['access_effect'],8:['specific_harm'],
 9:['urgency_reasons','reason3_details','reason4_damage','urgent_hearing'],10:['evidence'],
 11:['attempts_made','attempt_types','defendant_response'],12:['obstruction_date'],
 13:['village','taluka','district','obstruction_date','filing_date']}
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
 p=doc.add_paragraph();p.alignment=1;p.add_run('AI भाषिक परीक्षण मसुदा — न्यायालयात दाखल करण्यासाठी अंतिम नाही' if draft_override is not None else 'चाचणी मसुदा — न्यायालयात दाखल करण्यासाठी अंतिम नाही').bold=True
 if d['limitation']['mode']=='REVIEW_ONLY':
  p=doc.add_paragraph('केवळ कायदेशीर पुनरावलोकनासाठी — सहा महिन्यांच्या मुदतीची स्वतंत्र पडताळणी आवश्यक.');p.style='Subtitle'
 doc.add_paragraph(f'मा. मामलेदार न्यायालय, {d["taluka"]}')
 doc.add_paragraph('दावा क्रमांक : ____ / '+str(date.fromisoformat(d['filing_date']).year))
 for i,person in enumerate(d['plaintiffs'],1):doc.add_paragraph(f'वादी {i}) {person["name"]}, {person["address"]}')
 doc.add_paragraph('विरुद्ध')
 for i,person in enumerate(d['defendants'],1):doc.add_paragraph(f'प्रतिवादी {i}) {person["name"]}, {person["address"]}')
 table=doc.add_table(rows=1,cols=5);table.style='Table Grid'
 for c,s in zip(table.rows[0].cells,CONTRACT['land_table']['five_columns']):c.text=s
 for group,people in [('वादी',d['plaintiffs']),('प्रतिवादी',d['defendants'])]:
  for person in people:
   cells=table.add_row().cells
   for c,s in zip(cells,[group,d['village'],str(person['gat']),
      f'लागवडीलायक: {person["cultivable"]}\nपोटखराब: {person["potkharab"]}',str(person['assessment'])]):c.text=s
 doc.add_heading('मामलेदार न्यायालय अधिनियम, १९०६ चे कलम ५ अन्वये रस्त्यावरील अडथळा दूर करण्याबाबत दावा',level=2)
 for p in b['paragraphs']:
  doc.add_paragraph(f'{p["number"]}) {p["subject"]} :',style='Heading 3')
  doc.add_paragraph(p['text'])
 doc.add_paragraph('तरी विनंती की,')
 for prayer in d['prayers']:
  doc.add_paragraph(f'{prayer["display_number"]}) {prayer["text"]}')
 if d.get('attached_docs'):
  doc.add_paragraph('अर्जासोबत जोडण्यासाठी वापरकर्त्याने निवडलेली कागदपत्रे (प्रत्यक्ष जोडल्याची तपासणी आवश्यक):')
  for i,x in enumerate(d['attached_docs'],1):doc.add_paragraph(f'{i}) {x}')
 else:doc.add_paragraph('जोडपत्रे : कोणतेही जोडल्याची पुष्टी दिलेली नाही.')
 doc.add_paragraph('सत्यापन : मी/आम्ही, वर नमूद वादी, प्रतिज्ञापूर्वक लिहून देतो/देते की, वरील दाव्यातील परिच्छेद क्र. १ ते १३ मधील मजकूर माझ्या/आमच्या स्वतःच्या माहितीप्रमाणे व उपलब्ध कागदपत्रांनुसार खरा व बरोबर आहे.')
 doc.add_paragraph(f'ठिकाण : {d["village"]}')
 doc.add_paragraph(f'अर्जाची मसुदा तारीख: {d["filing_date"]}')
 doc.add_paragraph('वादी/वादींची स्वाक्षरी : __________________')
 doc.add_paragraph('तथ्ये, मुदत, हक्क, पुरावे आणि कायदेशीर ग्राह्यता स्वतंत्रपणे पडताळणे आवश्यक आहे.')
 bio=io.BytesIO();doc.save(bio);return bio.getvalue()
