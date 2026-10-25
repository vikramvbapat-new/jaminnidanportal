# जमीन निदान पोर्टल V2 — कलम ५ | Local Working Prototype 03

**स्थिती: Controlled AI Integration Test-Ready. हा पूर्ण AI पोर्टल नाही; न्यायालयात अर्ज दाखल करण्यासाठी वापरू नका.**

## काय बदलले

Prototype 02 मधील मंजूर Master, प्रश्नावली, AI संदर्भ-Adapter, Word निर्मिती, तातडीसाठी स्वतंत्र पुष्टी, मुद्द्यांचे स्थिर क्रमांक, सहा-महिन्यांच्या मुदतीचा review-only नियम आणि सर्व पूर्वीच्या चाचण्या सुरक्षित आहेत.

या आवृत्तीत नवीन:

- `scripts/live_ai_synthetic_smoke.py` — **फक्त कोडमध्येच असलेल्या चार काल्पनिक प्रकरणांसाठी** प्रत्यक्ष AI सेवा तपासण्याची पर्यायी स्क्रिप्ट. बाहेरून केस/फाइल घेण्याची सोय नाही.
- स्क्रिप्टला `--live-synthetic-only` आणि `MC5_LIVE_SYNTHETIC_TEST_APPROVED=YES` ही दोन स्वतंत्र, स्पष्ट अनुमती आवश्यक; त्याशिवाय **API कॉल होत नाही**.
- `tests/test_openai_adapter_contract.py` — AI SDK चे JSON Schema, `store=False`, न वापरलेले tools, सुरक्षित अपयश या अटी तपासणाऱ्या नेटवर्कविरहित चाचण्या.
- `tests/test_provider_live_contract.py` — चार चाचणी-परिस्थिती, मर्यादित डेटा पाठवणे, अनधिकृत मागणी व काल्पनिक कालावधी नाकारणे यांसाठी Fake Provider चाचण्या.
- `scripts/offline_four_scenario_qa.py` — चार परिस्थितींचे **Fake Provider QA Word** आणि परीक्षणासाठी CSV तयार करणारी नेटवर्कविरहित स्क्रिप्ट.
- `qa/prototype03/` — Word नमुने, तपासणी-तक्ता आणि मानवी परीक्षणाची यादी.

## स्थानिक, सुरक्षित प्रारंभ

Python 3.11+:

```bash
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
python -m pytest tests -q
python scripts/offline_four_scenario_qa.py
./START_LOCAL.sh
```

ब्राउझरमधील पत्ता **http://127.0.0.1:8765**. सार्वजनिक होस्टिंगसाठी नाही.

## पर्यायी प्रत्यक्ष AI चाचणी — फक्त विकासकाकडून आणि काल्पनिक माहितीवर

**या पॅकेजच्या निर्मितीवेळी OPENAI_API_KEY आणि मॉडेल सेट केलेले नव्हते; एकही प्रत्यक्ष बाह्य AI कॉल झालेला नाही.** अधिकृत विकास वातावरणातच खालील निवडी कराव्यात. API Key कोणालाही चॅटमध्ये पाठवू नका; ZIP, `.env`, Screenshot किंवा Source Control मध्ये ठेवू नका.

```bash
python -m pip install -r requirements-ai.txt
export MC5_AI_PROVIDER=openai
export MC5_AI_ALLOW_EXTERNAL=true
export MC5_AI_MODEL='<approved-model-id>'
# OPENAI_API_KEY विकासकाच्या सुरक्षित secret manager/environment मधून द्यावी.
export MC5_LIVE_SYNTHETIC_TEST_APPROVED=YES
python scripts/live_ai_synthetic_smoke.py --live-synthetic-only
```

या चाचणीत API खर्च आणि काल्पनिक जमीन/रस्त्याचे तथ्य बाह्य मॉडेलकडे जाऊ शकतात. यासाठी संस्थेची स्वतंत्र सुरक्षा/डेटा-संरक्षण पडताळणी आवश्यक. स्क्रिप्ट **फक्त चार अंगभूत काल्पनिक प्रकरणे** वापरते: अडथळा कायम, अंशतः दूर + तातडी, पूर्ण दूर + मनाई, मुदत-संबंधी पुनरावलोकन. प्रतिसादाचा संपूर्ण मजकूर डिस्कवर लिहीत नाही; केवळ सुरक्षित निकाल ठेवते. मॉडेलचा भाषिक व कायदेशीर दर्जा तज्ञाकडून तपासणे आवश्यकच आहे.

### चाचणी आणि मंजुरी यांचा फरक

- `36/36` स्वयंचलित स्थानिक चाचण्या यशस्वी (या आवृत्तीच्या निर्मितीवेळी).
- ४ काल्पनिक Word QA फाइल्स तयार; संरचनात्मक तपासणी यशस्वी.
- **Live AI provider calls: 0; live API quality validation: NOT RUN.**
- **मानवी भाषिक/कायदेशीर मंजुरी: NOT GIVEN.**
- OCR, OTP, स्वतःचे खाते, सुरक्षा-परीक्षण, ३० दिवसांनी प्रत्यक्ष डेटा हटवणे, बाह्य सेवा डेटा करार: NOT IMPLEMENTED.
- मूळ मंजूर शब्दांकन, १३ परिच्छेदांचे विषय व स्थिर क्रमांक, मुख्य मागण्यांचा आशय अपरिवर्तित. Prototype 03 मधील Sample अर्जांना अंतिम Template म्हणून समजू नका.

## मानवाकडून तपासायचे निर्णायक प्रश्न

`qa/prototype03/HUMAN_REVIEW_CHECKLIST.md` पाहा. मराठीतील प्रत्येक वाक्याचा अर्थ, दिशावर्णन, तारीख, गट क्रमांक, अपुष्ट आर्थिक नुकसान/हक्क, रस्ता अस्तित्व व उपलब्ध पुरावे यांची परस्पर पडताळणी आवश्यक. Automated Pattern Checks तथ्यशुद्धतेची पूर्ण हमी देत नाहीत.
