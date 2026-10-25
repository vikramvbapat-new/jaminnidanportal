# Prototype 02 — QA report (24 Oct 2026)

- Source baseline: approved §5 Master Contract + S7 approved rule package from Prototype 01; original source unchanged.
- New feature: optional structured language rewrite provider behind two opt-ins. **No real AI service invoked.**
- Test command: `python -m pytest -q tests`
- Result: **29 passed** (includes Prototype 01 regression tests).
- Negative tests: unauthorized AI, no explicit consent, new ४०-year period, added gat/financial loss, evidence in P2, falsely attached evidence in P10, added prayers/para, request data/model tampering, 15-min expiry, missing paragraph review, mode status 3, late review only.
- Reference Fake Provider API flow passed and DOCX saved as `qa/MC5_AI_MOCK_QA_REVIEW_ONLY.docx`.
- DOCX QA: rendered into 2 PNG pages via `/home/oai/skills/docx/render_docx.py` and visually inspected (page-1, page-2). No clipping; five-column land table present; request numbering proper. Some drafting still mechanical, not final court language.
- UI: `node --check app/static/app.js` passed. Static 390px-width mobile layout inspected; no horizontal overflow. Actual browser API/UI flow was unavailable from restricted browser environment (loopback navigation blocked by administrator), so do **not** claim browser end-to-end validation.
- Live OpenAI API: **not tested** (no model credentials). The adapter requests JSON schema output and disables response storage where supported, but production privacy and service settings must be verified independently.
- Data source caution: OCR not operational; no actual party-identity/land-survey validation; do not use real client data for these tests.
