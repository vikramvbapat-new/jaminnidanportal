# जमीन निदान पोर्टल V2 — कलम ५
## Live AI Execution & Human Acceptance Handoff · २४ ऑक्टोबर २०२६

**उद्देश:** Prototype 03 च्या आधी मंजूर प्रश्नावली, १३ परिच्छेद व मागण्यांमध्ये कोणताही बदल न करता, प्रत्यक्ष AI सेवा जोडलेल्या वातावरणात चार *काल्पनिक* प्रकरणांचा दर्जा तपासण्यासाठी निश्चित प्रक्रिया. **हे Production-ready प्रमाणपत्र नाही.**

### A. आधी स्थानिक ऑफलाइन पडताळणी करा

प्रकल्पाच्या `MC5_Local_Prototype_03/` फोल्डरमध्ये:

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q tests
python scripts/check_live_ai_readiness.py
```

सध्याच्या दिलेल्या वातावरणात ६१/६१ स्थानिक चाचण्या उत्तीर्ण झाल्या; API पूर्वतपासणी `NOT_READY`; **बाह्य AI कॉल ०**.

### B. चार काल्पनिक प्रकरणांवर प्रत्यक्ष API चाचणी

ही पायरी अधिकृत विकासकाने, संस्थेच्या सुरक्षित वातावरणात व खर्च/गोपनीयतेच्या परवानगीनंतरच चालवावी. `OPENAI_API_KEY` ही गुप्त माहिती चॅट, Git, लॉग किंवा ZIP मध्ये ठेवू नये.

```bash
python -m pip install -r requirements-ai.txt
export MC5_AI_PROVIDER=openai
export MC5_AI_ALLOW_EXTERNAL=true
export MC5_AI_MODEL='<approved-model-id>'
# OPENAI_API_KEY secret manager मधून environment मध्ये द्या.
export MC5_LIVE_SYNTHETIC_TEST_APPROVED=YES
export MC5_LIVE_REVIEW_EXPORT_APPROVED=YES
python scripts/check_live_ai_readiness.py
python scripts/live_ai_acceptance_review.py --live-synthetic-only --export-review-artifacts
```

Windows वर `export` ऐवजी PowerShell मधील `$env:VARIABLE = 'value'` वापरता येते.

**काहीही अतिरिक्त प्रत्यक्ष ग्राहक माहिती देऊ नका.** या script मध्ये चार अंगभूत काल्पनिक प्रकरणे आहेत; user-supplied path स्वीकारला जात नाही. थेट API कॉल करण्यासाठी दोन स्पष्ट परवानग्या आणि provider configuration आवश्यक आहे. प्रत्येक external कॉलचा खर्च संस्थेकडे असू शकतो.

### C. तुलना व मानवी परीक्षण

`qa/live_acceptance/live_synthetic_local_only/` मध्ये तयार होईल:

- चार Review-only Word अर्ज;
- चार 'मूळ नियमाधारित' विरुद्ध 'AI प्रस्तावित' तुलनात्मक Word दस्तऐवज;
- `HUMAN_SCORECARD.csv`: ४ प्रकरणे × ९ निकष = ३६ नोंदी;
- `PARAGRAPH_SCORECARD.csv`: सर्व चार अर्जांतील *प्रत्येक परिच्छेदासाठी* स्वतंत्र मानवी निर्णय;
- `SUMMARY.json`: प्रत्यक्ष बदललेल्या परिच्छेदांची संख्या, संरचनात्मक स्थिती आणि Word फाइल्सचे SHA-256.

**प्रत्येक ओळीत** `human_result` ला `PASS`, `FAIL`, `CORRECTION_REQUIRED`, किंवा `NOT_REVIEWED` असेच मूल्य द्यावे. `FAIL`/`CORRECTION_REQUIRED` असेल तर `reviewer_notes` मध्ये कारण लिहावे. वास्तविक पडताळणी केल्याशिवाय कोणतीही ओळ PASS करू नये.

### D. प्रत्यक्ष Live AI स्वीकृती-तपासणी

```bash
python -m scripts.verify_human_acceptance \
  --reviewer-code '<internal-reviewer-code>' \
  --review-date 'YYYY-MM-DD'
```

इच्छित फोल्डरसाठी `--folder qa/live_acceptance/live_synthetic_local_only` वापरू शकता.

तपासणी खालील बाबी पूर्ण नसल्यास *BLOCKED* देते:

1. Run खरोखर LIVE_PROVIDER_SYNTHETIC_ONLY म्हणून नोंदलेली आहे; Fake Provider ची run नाही;
2. चारही संरचनात्मक चाचणी प्रकरणे उत्तीर्ण;
3. Word व तुलनात्मक Word अशा ८ फाइल्सचा मूळ SHA-256 जुळतो;
4. ३६/३६ सर्वसाधारण निकष `PASS`;
5. **प्रत्येक लागू परिच्छेद** `PASS`;
6. चारपैकी किमान एका प्रकरणात AI ने प्रत्यक्ष मजकूर बदलला आहे;
7. reviewer code व ISO तारीख स्पष्ट दिली आहे.

एखादा निकष अपयशी ठरल्यास Word ताबडतोब न्यायालयासाठी जारी न करता समस्या सोडवावी आणि आवश्यक असल्यास नव्याने AI मसुदा तयार करून पुनरावलोकन करावे.

`SYNTHETIC_LINGUISTIC_REVIEW_COMPLETED_NOT_PRODUCTION_APPROVED` **फक्त चार काल्पनिक प्रकरणांचे स्थानिक भाषिक QA** पूर्ण झाल्याचे सांगते. ती कायदेशीर वैधता, स्वाक्षरी प्रमाणीकरण किंवा उत्पादन-मंजुरी नाही. `reviewer-code` ही स्थानिक स्वयंघोषित नोंद आहे, सुरक्षित डिजिटल स्वाक्षरी नाही.

### E. उत्पादनासाठी बाकी

प्रत्यक्ष अर्जांवरील वापरापूर्वी मंजूर प्रश्नावलीची UAT, वापरकर्त्याने पडताळलेली सातबारा OCR, OTP/खाती, सुरक्षित storage व ३० दिवसांनंतर प्रत्यक्ष deletion, तातडी/मुदत/पुरावे, Word layout, मागणी क्रमांक २ ची कायदेशीर पडताळणी, डेटा-गोपनीयता व सुरक्षा चाचणी, आणि प्रत्यक्ष AI न्यायालयीन मराठीची अंतिम मानवी स्वीकृती आवश्यक राहतात.

**स्रोत नियंत्रण:** Master Application च्या निश्चित १३ परिच्छेदांमध्ये किंवा मंजूर मागण्यांच्या मजकुरात या Handoff ने बदल केलेले नाहीत.
