#!/usr/bin/env python3
"""Generate the three synthetic Section 5 sample Word documents with clean list formatting."""
from __future__ import annotations
import io
import sys
from pathlib import Path
from docx import Document

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.engine import create_docx, canonical_hash, validate

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'qa' / 'prototype03'
OUT.mkdir(parents=True, exist_ok=True)

s1_data = {
    'map_ack': True, 'village': 'आंबेगाव', 'taluka': 'जुन्नर', 'district': 'पुणे',
    'plaintiffs': [{'name': 'अजय गणपत पाटील', 'address': 'आंबेगाव, ता. जुन्नर', 'gat': '१२५', 'cultivable': '१.२०', 'potkharab': '०.०५', 'assessment': '१२.५०'}],
    'defendants': [{'name': 'विजय रामचंद्र शिंदे', 'address': 'आंबेगाव, ता. जुन्नर', 'gat': '१२४', 'cultivable': '०.८०', 'potkharab': '०.००', 'assessment': '९.२०'}],
    'preexisting_use': 'पूर्वीपासून नियमित वहिवाट चालत आलेली होती.',
    'preexisting_use_duration': '१० वर्षांपेक्षा जास्त',
    'route_description': 'गट क्रमांक १२४ च्या पश्चिमेकडील बांधावरून जाणारा रस्ता',
    'route_orientation': 'गट क्र. १२४ च्या बांधालगत',
    'village_road_confirmed': True, 'width_ft': '१२', 'length_ft': '२००',
    'crops': ['ऊस', 'सोयाबीन'], 'crop_status': 'standing',
    'transport_modes': ['बैलगाडी', 'ट्रॅक्टर'],
    'obstruction_date': '2026-09-15', 'obstruction_gat': '१२४', 'obstruction_gat_confidence': 'exact',
    'obstruction_location_desc': 'गट क्र. १२४ मधील रस्त्याच्या भागावर',
    'obstructor_role': 'स्वतः खातेदार',
    'obstruction_description': 'मोठे दगड व मातीचा भराव टाकून रस्ता पूर्ण बंद केला',
    'status': 1,
    'access_effect': 'ट्रॅक्टर व शेती अवजारे शेतात नेता येत नाहीत',
    'farm_work_affected': 'शेतीची नियमित मशागत व वाहतूक',
    'specific_harm': 'ऊस पिकाला वेळेवर पाणी व खते देणे अशक्य झाले आहे',
    'urgency_reasons': [2], 'reason3_details': [], 'reason4_damage': None,
    'house_confirmed': False, 'urgent_hearing': True,
    'evidence': ['रस्ता दर्शविणारा नकाशा', 'महसूल/न्यायालयीन आदेश', 'जुने फोटो'],
    'attached_docs': ['रस्ता दर्शविणारा नकाशा', 'जुने फोटो'],
    'attempts_made': True, 'attempt_types': ['प्रतिवादींना वैयक्तिक विनंती', 'गावातील प्रतिष्ठित व्यक्ती/मध्यस्थांमार्फत'],
    'defendant_response': 'नकार', 'filing_date': '2026-10-24'
}

s2_data = {
    'map_ack': True, 'village': 'वडगाव', 'taluka': 'हवेली', 'district': 'पुणे',
    'plaintiffs': [{'name': 'दत्तात्रय सोपानराव कदम', 'address': 'वडगाव, ता. हवेली', 'gat': '८८', 'cultivable': '२.१०', 'potkharab': '०.१०', 'assessment': '१८.००'}],
    'defendants': [{'name': 'मारुती बापूराव जगताप', 'address': 'वडगाव, ता. हवेली', 'gat': '८७', 'cultivable': '१.५०', 'potkharab': '०.००', 'assessment': '१४.५०'}],
    'preexisting_use': 'अनेक वर्षांपासून नियमित वहिवाट चालत आलेली होती.',
    'preexisting_use_duration': 'निश्चित कालावधी सांगता येत नाही',
    'route_description': 'गट क्रमांक ८७ च्या दक्षिण हद्दीवरून जाणारा मार्ग',
    'route_orientation': 'गट क्र. ८७ च्या बांधालगत',
    'village_road_confirmed': False, 'width_ft': '१०', 'length_ft': '',
    'crops': ['कांदा', 'भाजीपाला'], 'crop_status': 'harvested', 'harvested_stock': True,
    'transport_modes': ['ट्रॅक्टर', 'पायी'],
    'obstruction_date': '2026-08-20', 'obstruction_gat': '८७', 'obstruction_gat_confidence': 'exact',
    'obstruction_location_desc': 'गट क्र. ८७ मधील रस्त्याच्या भागावर',
    'obstructor_role': 'स्वतः खातेदार',
    'obstruction_description': 'काटेरी तारांचे कुंपण व झाडे टाकून वहिवाटीचा अर्धा रस्ता अडवला',
    'status': 2,
    'access_effect': 'रुंद वाहने व ट्रॅक्टर जाऊ शकत नाहीत, केवळ पायी जाता येते',
    'farm_work_affected': 'शेतीची नियमित मशागत व वाहतूक',
    'specific_harm': 'कांदा शेतीमाल बाजारात पाठवणे थांबले आहे',
    'urgency_reasons': [3], 'reason3_details': ['काढलेला शेतमाल शेतातून बाहेर नेता येत नाही.'], 'reason4_damage': None,
    'house_confirmed': False, 'urgent_hearing': True,
    'evidence': ['रस्ता दर्शविणारा नकाशा', 'जुने फोटो'],
    'attached_docs': ['रस्ता दर्शविणारा नकाशा'],
    'attempts_made': True, 'attempt_types': ['प्रतिवादींना वैयक्तिक विनंती'],
    'defendant_response': 'आश्वासन देऊन पालन नाही', 'filing_date': '2026-10-24'
}

s3_data = {
    'map_ack': True, 'village': 'शिंदेवाडी', 'taluka': 'शिरूर', 'district': 'पुणे',
    'plaintiffs': [{'name': 'बाळकृष्ण तुकाराम भोसले', 'address': 'शिंदेवाडी, ता. शिरूर', 'gat': '२१२', 'cultivable': '१.००', 'potkharab': '०.००', 'assessment': '१०.००'}],
    'defendants': [{'name': 'ज्ञानेश्वर विठ्ठल गायकवाड', 'address': 'शिंदेवाडी, ता. शिरूर', 'gat': '२११', 'cultivable': '१.२०', 'potkharab': '०.०५', 'assessment': '११.५०'}],
    'preexisting_use': '१० वर्षांपेक्षा जास्त कालावधीपासून नियमित वहिवाट चालत आलेली होती.',
    'preexisting_use_duration': '१० वर्षांपेक्षा जास्त',
    'route_description': 'गट क्रमांक २११ च्या बांधावरून जाणारा रस्ता',
    'route_orientation': 'गट क्र. २११ च्या बांधालगत',
    'village_road_confirmed': True, 'width_ft': '१२', 'length_ft': '१००',
    'crops': ['बाजरी', 'हरभरा'], 'crop_status': 'standing',
    'transport_modes': ['बैलगाडी', 'पायी'],
    'obstruction_date': '2026-03-01', 'obstruction_gat': '२११', 'obstruction_gat_confidence': 'exact',
    'obstruction_location_desc': 'गट क्र. २११ मधील रस्त्याच्या भागावर',
    'obstructor_role': 'स्वतः खातेदार',
    'obstruction_description': 'मातीचा बांध घालून रस्ता अडवला होता, जो ग्रामपंचायतीच्या सांगण्यावरून काढला',
    'status': 3,
    'access_effect': 'पूर्वी ट्रॅक्टर व बैलगाडी अडवली होती',
    'farm_work_affected': 'शेतीची नियमित मशागत व वाहतूक',
    'urgency_reasons': [], 'urgent_hearing': False,
    'evidence': ['रस्ता दर्शविणारा नकाशा'],
    'attached_docs': [],
    'attempts_made': False,
    'filing_date': '2026-10-25'
}

samples = [
    ('SAMPLE_01_STATUS1_FULL_OBSTRUCTION_20261101.docx', s1_data),
    ('SAMPLE_02_STATUS2_PARTIAL_URGENT_20261101.docx', s2_data),
    ('SAMPLE_03_STATUS3_REMOVED_INJUNCTION_REVIEW_ONLY_20261101.docx', s3_data),
]

for filename, data in samples:
    v = validate(data)
    h = canonical_hash(data)
    blob = create_docx(data, h, True)
    p = OUT / filename
    p.write_bytes(blob)
    print(f"Generated {filename} ({len(blob)} bytes)")
