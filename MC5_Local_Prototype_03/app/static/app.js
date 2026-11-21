/* Jamin Nidan Portal V2 - Section 5 Client Application
   Mobile-first, accessible Marathi interface with minimal typing guidance chips.
*/
'use strict';

const $ = id => document.getElementById(id);
let options = null, currentStep = 0, lastToken = null, lastAI = null, lastMode = 'rules';
let sessionMeta = { draft_id: null, started_at: null, word_revision: 1 };
const pages = [...document.querySelectorAll('.step')];

const getRadio = n => document.querySelector(`input[name="${n}"]:checked`)?.value || null;
const checkedValues = box => [...box.querySelectorAll('input[type=checkbox]:checked')].map(x => x.value);

const clearPreview = () => {
  lastToken = null;
  lastAI = null;
  lastMode = 'rules';
  $('reviewConfirm').checked = false;
  $('downloadBtn').disabled = true;
  $('preview').hidden = true;
};

function el(tag, attrs = {}, text = '') {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === 'class') e.className = v;
    else if (k === 'type') e.type = v;
    else e.setAttribute(k, v);
  }
  if (text) e.textContent = text;
  return e;
}

function listOptions(target, entries, kind, groupName, valueFn) {
  const root = $(target);
  root.replaceChildren();
  entries.forEach((item, i) => {
    const val = valueFn ? valueFn(item, i) : item;
    const label = el('label', { class: 'choice' });
    const input = el('input', { type: kind, name: groupName, value: String(val) });
    label.append(input, document.createTextNode(typeof item === 'string' ? item : item.label));
    root.append(label);
  });
}

function addParty(target) {
  const isPlaintiff = target === 'plaintiffs';
  const prefix = isPlaintiff ? 'वादी' : 'प्रतिवादी';
  const count = $(target).querySelectorAll('.person').length + 1;
  const box = el('div', { class: 'person' });
  box.dataset.party = target;

  const header = el('header');
  header.append(el('strong', {}, `${prefix} क्रमांक ${count}`));
  if (count > 1) {
    const copyAddrBtn = el('button', { type: 'button', class: 'chip', style: 'margin-left: 8px; font-size: 12px; padding: 2px 8px;' }, 'मागील पक्षकाराचाच पत्ता वापरा');
    copyAddrBtn.onclick = () => {
      const persons = $(target).querySelectorAll('.person');
      const prev = persons[persons.length - 2];
      if (prev) {
        const prevAddr = prev.querySelector('input[data-field="address"]')?.value || '';
        const curAddr = box.querySelector('input[data-field="address"]');
        if (curAddr && prevAddr) curAddr.value = prevAddr;
      }
    };
    header.append(copyAddrBtn);
  }
  const rm = el('button', { type: 'button', class: 'remove' }, 'काढा');
  rm.addEventListener('click', () => {
    box.remove();
    renumberParties(target);
    clearPreview();
  });
  header.append(rm);
  box.append(header);

  const grid = el('div', { class: 'twocol' });
  const fields = [
    ['name', `${prefix}चे पूर्ण नाव`, 'उदा. अजय गणपत पाटील'],
    ['address', 'पत्ता / वस्ती / गाव', 'उदा. मु. पो. आंबेगाव, ता. जुन्नर'],
    ['gat', 'गट क्रमांक / सर्व्हे क्रमांक', 'उदा. १२५ किंवा १२५/१, १२५/२'],
    ['cultivable', 'लागवडीलायक क्षेत्र (हे.आर.)', 'उदा. १.२० (नसल्यास ०)'],
    ['potkharab', 'पोटखराब क्षेत्र (हे.आर.)', 'उदा. ०.०५ (नसल्यास ०)'],
    ['assessment', 'आकार (रुपये-पैसे)', 'उदा. १२.५० (नसल्यास ०)']
  ];

  fields.forEach(([k, title, ph]) => {
    const lab = el('label', {}, title);
    const inp = el('input', { type: 'text', 'data-field': k, placeholder: ph });
    lab.append(inp);
    grid.append(lab);
  });

  box.append(grid);
  $(target).append(box);
}

function renumberParties(target) {
  const isPlaintiff = target === 'plaintiffs';
  const prefix = isPlaintiff ? 'वादी' : 'प्रतिवादी';
  $(target).querySelectorAll('.person').forEach((p, idx) => {
    const strong = p.querySelector('header strong');
    if (strong) strong.textContent = `${prefix} क्रमांक ${idx + 1}`;
  });
}

function partyData(type) {
  return [...$(type).querySelectorAll('.person')].map(p =>
    Object.fromEntries([...p.querySelectorAll('input')].map(input => [input.dataset.field, input.value.trim()]))
  );
}

function setStep(n) {
  currentStep = Math.max(0, Math.min(6, n));
  pages.forEach((p, i) => {
    p.classList.toggle('show', i === currentStep);
  });
  document.querySelectorAll('.steps button').forEach((b, i) => {
    b.classList.toggle('active', i === currentStep);
  });
  $('stepPos').textContent = `टप्पा ${currentStep + 1} / ७`;
  $('backBtn').hidden = currentStep === 0;
  $('nextBtn').hidden = currentStep === 6;
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function valuesFor(selector) {
  return [...document.querySelectorAll(selector + ':checked')].map(x => x.value);
}

function selectedReasons() {
  return valuesFor('#urgencyOptions input').map(Number);
}

function updateConditional() {
  const status = Number(getRadio('status') || 0);
  const crop = getRadio('cropStatus');
  let allowed = [];

  if (status !== 3) {
    allowed = [5, 6];
    if (['not_grown', 'planned'].includes(crop)) allowed.push(1);
    if (crop === 'standing') allowed.push(2, 3, 4);
    if (crop === 'harvested' || $('harvestedStock')?.checked) allowed.push(3);
  }

  $('urgencyArea').hidden = status === 3;
  if (status === 3) {
    document.querySelectorAll('#urgencyOptions input').forEach(x => { x.checked = false; });
  }

  [...$('urgencyOptions').querySelectorAll('label')].forEach((label, i) => {
    const isAllowed = allowed.includes(i + 1);
    label.hidden = !isAllowed;
    if (!isAllowed) label.querySelector('input').checked = false;
  });

  const reasons = selectedReasons();
  ['reason3Wrap', 'reason4Wrap', 'reason5Wrap'].forEach((id, i) => {
    const chosen = reasons.includes([3, 4, 5][i]);
    $(id).hidden = !chosen;
    if (!chosen) $(id).querySelectorAll('input').forEach(x => { x.checked = false; });
  });

  $('urgentHearingWrap').hidden = !(status !== 3 && reasons.length);
  if ($('urgentHearingWrap').hidden) {
    document.querySelectorAll('input[name=urgentHearing]').forEach(x => { x.checked = false; });
  }

  const effectTextarea = $('effectWrap').querySelector('textarea');
  if (effectTextarea) {
    effectTextarea.placeholder = status === 3
      ? 'पूर्वी झालेला परिणाम (असल्यास); सध्या अडथळा कायम असल्याचे लिहू नका'
      : 'अडथळ्यामुळे रस्त्याच्या वापरात आलेली प्रत्यक्ष अडचण';
  }

  // Attempts Made visibility
  const attemptsMade = getRadio('attemptsMade') === 'yes';
  $('attemptDetails').hidden = !attemptsMade;
  if (!attemptsMade) {
    document.querySelectorAll('#attemptOptions input').forEach(x => { x.checked = false; });
    document.querySelectorAll('#responseOptions input').forEach(x => { x.checked = false; });
  }

  // Synchronize attached docs with available evidence
  const checkedEv = new Set(checkedValues($('evidenceOptions')));
  [...$('attachedOptions').querySelectorAll('label')].forEach(lbl => {
    const inp = lbl.querySelector('input');
    const isAvailable = checkedEv.has(inp.value);
    lbl.style.opacity = isAvailable ? '1' : '0.4';
    inp.disabled = !isAvailable;
    if (!isAvailable) inp.checked = false;
  });
}

const DEVANAGARI_DIGITS = {
  '०': '0', '१': '1', '२': '2', '३': '3', '४': '4',
  '५': '5', '६': '6', '७': '7', '८': '8', '९': '9'
};

function normalizeNumber(val) {
  if (val === null || val === undefined) return '';
  let s = String(val).trim();
  if (!s) return '';
  s = s.replace(/[०-९]/g, d => DEVANAGARI_DIGITS[d] || d);
  s = s.replace(',', '.');
  const m = s.match(/(\d+(?:\.\d+)?)/);
  return m ? m[1] : s;
}

function normalize() {
  const reasons = selectedReasons();
  const status = Number(getRadio('status') || 0);
  const uh = getRadio('urgentHearing');

  return {
    village: $('village').value.trim(),
    taluka: $('taluka').value.trim(),
    district: $('district').value.trim(),
    map_ack: $('mapAck').checked,
    plaintiffs: partyData('plaintiffs'),
    defendants: partyData('defendants'),
    preexisting_use: $('preexistingUse').value.trim(),
    route_description: $('routeDescription').value.trim(),
    village_road_confirmed: $('villageRoad').checked,
    width_ft: normalizeNumber($('widthFt').value),
    length_ft: normalizeNumber($('lengthFt').value),
    obstruction_date: $('obstructionDate').value,
    obstruction_gat: $('obstructionGat').value.trim(),
    obstruction_gat_confidence: getRadio('gatConfidence'),
    obstructor_role: getRadio('obstructorRole'),
    obstruction_description: $('obstructionDescription').value.trim(),
    status,
    access_effect: $('accessEffect').value.trim(),
    specific_harm: $('specificHarm').value.trim(),
    crop_status: getRadio('cropStatus'),
    harvested_stock: $('harvestedStock')?.checked || false,
    urgency_reasons: reasons,
    reason3_details: checkedValues($('reason3Options')),
    reason4_damage: getRadio('reason4Damage'),
    house_confirmed: $('houseConfirmed').checked,
    urgent_hearing: uh === null ? null : uh === 'yes',
    evidence: checkedValues($('evidenceOptions')),
    attached_docs: checkedValues($('attachedOptions')),
    attempts_made: getRadio('attemptsMade') === 'yes',
    attempt_types: checkedValues($('attemptOptions')),
    defendant_response: getRadio('defendantResponse'),
    filing_date: $('filingDate').value,
    draft_id: sessionMeta.draft_id,
    started_at: sessionMeta.started_at,
    word_revision: sessionMeta.word_revision
  };
}

function err(e) {
  const errorsList = Array.isArray(e) ? e : [String(e)];
  const box = $('errors');
  box.replaceChildren();

  const title = el('strong', {}, 'खालील त्रुटी आढळल्या आहेत, कृपया माहिती तपासा:');
  box.append(title);

  const ul = el('ul', { style: 'margin: 10px 0 4px 18px; padding: 0;' });
  errorsList.forEach(msg => {
    const li = el('li', { style: 'margin-bottom: 8px; line-height: 1.5;' });
    li.append(document.createTextNode(msg));

    let jumpStep = null;
    let focusId = null;
    let jumpText = '';

    if (msg.includes('रुंदी') || msg.includes('रस्त्या') || msg.includes('मार्ग')) {
      jumpStep = 2; // Step 3
      focusId = 'widthFt';
      jumpText = '👉 टप्पा ३ वर जा (रस्त्याची रुंदी भरा)';
    } else if (msg.includes('गाव') || msg.includes('तालुका') || msg.includes('जिल्हा') || msg.includes('नकाशा')) {
      jumpStep = 0; // Step 1
      focusId = 'village';
      jumpText = '👉 टप्पा १ वर जा (मूलभूत माहिती भरा)';
    } else if (msg.includes('वादी') || msg.includes('प्रतिवादी')) {
      jumpStep = 1; // Step 2
      jumpText = '👉 टप्पा २ वर जा (पक्षकारांची माहिती भरा)';
    } else if (msg.includes('अडथळा') || msg.includes('तारीख') || msg.includes('सद्यस्थिती')) {
      jumpStep = 3; // Step 4
      focusId = 'obstructionDate';
      jumpText = '👉 टप्पा ४ वर जा (अडथळ्याची माहिती भरा)';
    } else if (msg.includes('तातडी') || msg.includes('कारण')) {
      jumpStep = 4; // Step 5
      jumpText = '👉 टप्पा ५ वर जा (तातडीची कारणे भरा)';
    }

    if (jumpStep !== null) {
      const btn = el('button', {
        type: 'button',
        class: 'jump-to-step-btn'
      }, jumpText);
      btn.onclick = () => {
        setStep(jumpStep);
        if (focusId && $(focusId)) {
          setTimeout(() => {
            $(focusId).scrollIntoView({ behavior: 'smooth', block: 'center' });
            $(focusId).focus();
            $(focusId).classList.add('input-error-highlight');
            setTimeout(() => $(focusId).classList.remove('input-error-highlight'), 3500);
          }, 200);
        }
      };
      li.append(document.createElement('br'), btn);
    }

    ul.append(li);
  });

  box.append(ul);
  box.hidden = false;
  box.scrollIntoView({ behavior: 'smooth' });
}

async function callApi(path, body) {
  const res = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    cache: 'no-store'
  });
  if (!res.ok) {
    let d = {};
    try { d = await res.json(); } catch {}
    throw (d.detail || 'सर्व्हरने विनंती स्वीकारली नाही.');
  }
  return res;
}

function updateDownloadGate() {
  const checks = [...document.querySelectorAll('#paragraphPreview .para-review')];
  const allParasChecked = checks.length > 0 && checks.every(x => x.checked);
  const reviewConfirmed = $('reviewConfirm').checked;
  const hasTokenOrAi = Boolean(lastToken || lastAI);
  const isAi = lastMode === 'ai';

  const ok = reviewConfirmed && hasTokenOrAi && (!isAi || allParasChecked);
  $('downloadBtn').disabled = !ok;

  const hint = $('downloadGateHint');
  if (hint) {
    if (!hasTokenOrAi) {
      hint.textContent = '';
    } else if (ok) {
      hint.textContent = '✅ सर्व पडताळणी पूर्ण झाली आहे. खालील बटणावरून Word (.docx) फाईल डाउनलोड करा.';
      hint.style.color = '#15803d';
    } else if (isAi) {
      const checkedCount = checks.filter(x => x.checked).length;
      if (!allParasChecked && !reviewConfirmed) {
        hint.textContent = `ℹ️ डाउनलोडसाठी: वरील सर्व १३ परिच्छेद तपासा (किंवा खालील "सर्व निवडा" बटण दाबा) आणि अंतिम पुष्टीकरण चेकबॉक्स निवडा (${checkedCount}/${checks.length} निवडले).`;
      } else if (!allParasChecked) {
        hint.textContent = `ℹ️ डाउनलोडसाठी: अजून काही परिच्छेद तपासणे शिल्लक आहे (${checkedCount}/${checks.length} निवडले). सर्व निवडण्यासाठी खालील बटण दाबा.`;
      } else if (!reviewConfirmed) {
        hint.textContent = 'ℹ️ डाउनलोडसाठी: खालील अंतिम पुष्टीकरण चेकबॉक्स ("मी संपूर्ण पूर्वावलोकन वाचले आहे...") निवडा.';
      }
      hint.style.color = '#b45309';
    } else {
      hint.textContent = 'ℹ️ डाउनलोडसाठी: खालील अंतिम पुष्टीकरण चेकबॉक्स निवडा.';
      hint.style.color = '#b45309';
    }
  }

  const bottomSelectAll = $('selectAllAiChecksBtnBottom');
  if (bottomSelectAll) {
    bottomSelectAll.hidden = !isAi;
  }
}

function showDraft(data, mode) {
  lastMode = mode;
  const heading = $('previewHeading');
  if (heading) {
    heading.textContent = mode === 'ai'
      ? 'AI भाषिक मसुद्याचे पुनरावलोकन'
      : 'नियमाधारित अर्जाचे संपूर्ण पूर्वावलोकन (१३ परिच्छेद)';
  }

  const modeInfo = $('previewModeInfo');
  if (modeInfo) {
    modeInfo.textContent = mode === 'ai'
      ? 'AI ने काही निवडक परिच्छेदांची भाषा सुचवली आहे. निश्चित परिच्छेद आणि सर्व मागण्या प्रणालीने लॉक केल्या आहेत. प्रत्येक परिच्छेद स्वतंत्रपणे तपासा.'
      : 'हे AI-generated लेखन नाही. पुष्टी झालेले स्रोत फील्ड वापरून नियमाधारित मसुदा तयार झाला आहे.';
  }

  const limNotice = $('limitationNotice');
  if (limNotice) {
    limNotice.textContent = data.limitation.warning || data.export_label;
  }

  // Update session badge
  const badge = $('sessionBadge');
  if (badge && data.draft_id) {
    sessionMeta.draft_id = data.draft_id;
    sessionMeta.started_at = data.started_at;
    sessionMeta.word_revision = data.word_revision || 1;
    badge.textContent = `सत्र: ${data.draft_id.slice(0, 8)}... (३० दिवस वैध)`;
    badge.title = `सत्र सुरू: ${data.started_at} | वैध मुदत: ${data.expires_at}`;
  }

  const paragraphs = $('paragraphPreview');
  paragraphs.replaceChildren();

  data.paragraphs.forEach(p => {
    const card = el('div', { class: 'preview-para-card' });
    const h = el('h4', {}, `${p.number}) ${p.subject} :`);
    const txt = el('p', {}, p.text);
    card.append(h, txt);

    const meta = el('div', { class: 'preview-para-meta' });
    const modeBadge = el('span', { class: 'pill info' },
      p.drafting_mode === 'AI_REPHRASED_REVIEW_REQUIRED' ? 'AI भाषिक परीक्षण' : 'नियम निश्चित');
    meta.append(modeBadge);

    if (p.source_field_ids && p.source_field_ids.length > 0) {
      meta.append(document.createTextNode(` · स्रोत: ${p.source_field_ids.join(', ')}`));
    }
    card.append(meta);

    if (mode === 'ai') {
      const label = el('label', { class: 'choice', style: 'margin-top: 8px;' });
      const check = el('input', { type: 'checkbox', class: 'para-review', value: String(p.number) });
      check.addEventListener('change', updateDownloadGate);
      label.append(check, document.createTextNode(' या परिच्छेदाची भाषा व तथ्ये मी स्वतः तपासली.'));
      card.append(label);
    }

    paragraphs.append(card);
  });

  if ($('aiReviewGateNotice')) {
    $('aiReviewGateNotice').hidden = (mode !== 'ai');
  }

  const prayers = $('prayerPreview');
  prayers.replaceChildren();
  data.prayers.forEach(p => {
    const row = el('div', { class: 'preview-para-card', style: 'border-left: 3px solid var(--primary);' });
    row.append(el('strong', {}, `${p.display_number}) `), document.createTextNode(p.text));
    prayers.append(row);
  });

  $('preview').hidden = false;
  $('reviewConfirm').checked = false;
  $('downloadBtn').disabled = true;
  updateDownloadGate();
  $('preview').scrollIntoView({ behavior: 'smooth' });
}

async function aiPreview() {
  $('errors').hidden = true;
  clearPreview();
  if (!$('aiConsent').checked) {
    err('या AI विनंतीसाठी स्वतंत्र संमती आवश्यक आहे.');
    return;
  }
  try {
    const response = await callApi('/api/ai-preview', {
      data: normalize(),
      explicit_external_ai_consent: true
    });
    const data = await response.json();
    lastAI = {
      candidate: {
        paragraphs: data.paragraphs
          .filter(p => p.drafting_mode === 'AI_REPHRASED_REVIEW_REQUIRED')
          .map(p => ({ number: p.number, text: p.text }))
      },
      review_token: data.review_token
    };
    // Always require fresh consent for any subsequent generation request
    $('aiConsent').checked = false;
    showDraft(data, 'ai');
  } catch (e) {
    $('aiConsent').checked = false;
    err(e);
  }
}

async function preview() {
  $('errors').hidden = true;
  clearPreview();
  const payload = normalize();
  if (!$('mapAck').checked) {
    err(['नकाशाविषयक सूचना वाचल्याची पुष्टी द्या.']);
    return;
  }
  try {
    const res = await callApi('/api/preview', { data: payload });
    const data = await res.json();
    lastToken = data.preview_token;
    showDraft(data, 'rules');
  } catch (e) {
    err(e);
  }
}

async function download() {
  try {
    const isAi = lastMode === 'ai';
    const endpoint = isAi ? '/api/ai-docx' : '/api/docx';
    const checks = [...document.querySelectorAll('#paragraphPreview .para-review:checked')].map(x => Number(x.value));
    const confirmed = $('reviewConfirm').checked;

    if (!confirmed) {
      err('डाउनलोड करण्यासाठी "मी संपूर्ण पूर्वावलोकन वाचले आहे..." हा चेकबॉक्स निवडणे आवश्यक आहे.');
      return;
    }
    if (isAi && checks.length < 13) {
      err('AI मसुदा डाउनलोड करण्यासाठी सर्व १३ परिच्छेद तपासले असणे आवश्यक आहे. आपण खालील "सर्व निवडा (Quick Confirm)" बटण वापरू शकता.');
      return;
    }

    const payload = isAi ? {
      data: normalize(),
      candidate: lastAI.candidate,
      review_token: lastAI.review_token,
      review_confirmed: confirmed,
      reviewed_paragraph_numbers: checks
    } : {
      data: normalize(),
      preview_token: lastToken,
      review_confirmed: confirmed
    };

    const res = await callApi(endpoint, payload);
    const file = await res.blob();
    const url = URL.createObjectURL(file);
    const a = el('a');
    a.href = url;
    a.download = isAi ? 'MC5_AI_REVIEW_ONLY.docx' : 'MC5_RULES_REVIEW_ONLY.docx';
    document.body.append(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 4000);
  } catch (e) {
    err(e);
  }
}

function setupChips() {
  document.querySelectorAll('.chips-row').forEach(row => {
    const targetId = row.dataset.target;
    const isReplace = row.dataset.mode === 'replace';
    const targetInput = $(targetId);
    if (!targetInput) return;

    row.querySelectorAll('.chip').forEach(btn => {
      btn.addEventListener('click', () => {
        let text = btn.textContent.trim();
        if (text.startsWith('+ ')) text = text.slice(2).trim();

        if (isReplace) {
          const m = text.match(/([०-९\d]+(?:\.[०-९\d]+)?)/);
          targetInput.value = m ? m[1] : text;
          targetInput.classList.remove('input-error-highlight');
        } else {
          if (!targetInput.value.trim()) {
            targetInput.value = text;
          } else if (!targetInput.value.includes(text)) {
            targetInput.value = targetInput.value.trim() + '\n' + text;
          }
        }
        targetInput.dispatchEvent(new Event('input', { bubbles: true }));
        clearPreview();
      });
    });
  });
}

function validateStep(stepIndex) {
  document.querySelectorAll('.input-error-highlight').forEach(el => el.classList.remove('input-error-highlight'));
  $('errors').hidden = true;

  if (stepIndex === 0) {
    const missing = [];
    if (!$('village').value.trim()) missing.push({ id: 'village', label: 'गाव' });
    if (!$('taluka').value.trim()) missing.push({ id: 'taluka', label: 'तालुका' });
    if (!$('district').value.trim()) missing.push({ id: 'district', label: 'जिल्हा' });
    if (!$('mapAck').checked) missing.push({ id: 'mapAck', label: 'नकाशाविषयक सूचना वाचल्याची पुष्टी' });
    if (missing.length) return reportMissing(missing);
  } else if (stepIndex === 1) {
    const plaintiffs = partyData('plaintiffs');
    const defendants = partyData('defendants');
    if (!plaintiffs.length) { err('किमान एक वादी आवश्यक आहे.'); return false; }
    if (!defendants.length) { err('किमान एक प्रतिवादी आवश्यक आहे.'); return false; }
    const pNames = new Set(plaintiffs.map(p => p.name.trim()).filter(Boolean));
    for (const d of defendants) {
      const dName = d.name.trim();
      if (dName && pNames.has(dName)) {
        err(`एकाच व्यक्तीला दोन्ही बाजूंस (वादी व प्रतिवादी) निवडता येत नाही: ${dName}`);
        return false;
      }
    }
  } else if (stepIndex === 2) {
    const missing = [];
    if (!$('preexistingUse').value.trim()) missing.push({ id: 'preexistingUse', label: 'रस्त्याचा पूर्वीचा प्रत्यक्ष वापर' });
    if (!$('routeDescription').value.trim()) missing.push({ id: 'routeDescription', label: 'रस्त्याचा प्रत्यक्ष मार्ग' });
    if (!normalizeNumber($('widthFt').value)) missing.push({ id: 'widthFt', label: 'अडथळ्यापूर्वीची सरासरी रुंदी (फूट)' });
    if (missing.length) return reportMissing(missing);
  } else if (stepIndex === 3) {
    const missing = [];
    if (!$('obstructionDate').value) missing.push({ id: 'obstructionDate', label: 'अडथळ्याची तारीख' });
    if (!$('obstructionGat').value.trim()) missing.push({ id: 'obstructionGat', label: 'अडथळ्याचा गट क्रमांक' });
    if (!$('obstructionDescription').value.trim()) missing.push({ id: 'obstructionDescription', label: 'अडथळ्याचे प्रत्यक्ष स्वरूप' });
    if (missing.length) return reportMissing(missing);
  }
  return true;
}

function reportMissing(missing) {
  const names = missing.map(m => m.label).join(', ');
  err(`या टप्प्यावरील आवश्यक माहिती अपूर्ण आहे: ${names}`);
  const firstElem = $(missing[0].id);
  if (firstElem) {
    firstElem.scrollIntoView({ behavior: 'smooth', block: 'center' });
    firstElem.focus();
    missing.forEach(m => {
      const e = $(m.id);
      if (e) {
        e.classList.add('input-error-highlight');
        setTimeout(() => e.classList.remove('input-error-highlight'), 3500);
      }
    });
  }
  return false;
}

async function init() {
  options = await (await fetch('/api/options', { cache: 'no-store' })).json();

  listOptions('statusOptions', Object.entries(options.status).map(([k, v]) => ({ label: v, k })), 'radio', 'status', i => i.k);
  listOptions('cropOptions', Object.entries(options.crop).map(([k, v]) => ({ label: v, k })), 'radio', 'cropStatus', i => i.k);
  listOptions('urgencyOptions', options.reasons, 'checkbox', 'urgencyReasons', i => Number(i.id.split('-')[1]));
  listOptions('reason3Options', options.reasons[2].suboptions, 'checkbox', 'reason3Details');
  listOptions('reason4Options', options.reasons[3].suboptions, 'radio', 'reason4Damage');
  listOptions('evidenceOptions', options.evidence, 'checkbox', 'evidence');
  listOptions('attachedOptions', options.evidence, 'checkbox', 'attachedDocs');
  listOptions('attemptOptions', options.attempts, 'checkbox', 'attemptTypes');
  listOptions('responseOptions', options.responses, 'radio', 'defendantResponse');

  addParty('plaintiffs');
  addParty('defendants');

  $('cropOptions').querySelector('input').checked = true;

  const isReviewInteraction = e => {
    return e.target.id === 'reviewConfirm' ||
           e.target.id === 'aiConsent' ||
           e.target.id === 'selectAllAiChecksBtn' ||
           e.target.id === 'selectAllAiChecksBtnBottom' ||
           e.target.id === 'downloadBtn' ||
           e.target.classList.contains('para-review') ||
           Boolean(e.target.closest('#preview')) ||
           Boolean(e.target.closest('#aiPanel'));
  };

  $('mainForm').addEventListener('input', e => {
    if (isReviewInteraction(e)) return;
    clearPreview();
    updateConditional();
  });

  $('mainForm').addEventListener('change', e => {
    if (isReviewInteraction(e)) return;
    clearPreview();
    updateConditional();
  });

  $('addPlaintiff').onclick = () => { addParty('plaintiffs'); clearPreview(); };
  $('addDefendant').onclick = () => { addParty('defendants'); clearPreview(); };

  $('backBtn').onclick = () => setStep(currentStep - 1);
  $('nextBtn').onclick = () => {
    if (validateStep(currentStep)) {
      setStep(currentStep + 1);
    }
  };

  document.querySelectorAll('.steps button').forEach(b => {
    b.onclick = () => setStep(Number(b.dataset.step));
  });

  function fillSample() {
    $('village').value = 'आंबेगाव';
    $('taluka').value = 'जुन्नर';
    $('district').value = 'पुणे';
    $('mapAck').checked = true;

    $('plaintiffs').replaceChildren();
    $('defendants').replaceChildren();
    addParty('plaintiffs');
    addParty('defendants');

    const pName = $('plaintiffs').querySelector('input[data-field="name"]');
    const pAddr = $('plaintiffs').querySelector('input[data-field="address"]');
    const pGat = $('plaintiffs').querySelector('input[data-field="gat"]');
    const pCult = $('plaintiffs').querySelector('input[data-field="cultivable"]');
    const pPot = $('plaintiffs').querySelector('input[data-field="potkharab"]');
    const pAss = $('plaintiffs').querySelector('input[data-field="assessment"]');
    if (pName) pName.value = 'अजय गणपत पाटील';
    if (pAddr) pAddr.value = 'आंबेगाव, ता. जुन्नर';
    if (pGat) pGat.value = '१२५';
    if (pCult) pCult.value = '१.२०';
    if (pPot) pPot.value = '०.०५';
    if (pAss) pAss.value = '१२.५०';

    const dName = $('defendants').querySelector('input[data-field="name"]');
    const dAddr = $('defendants').querySelector('input[data-field="address"]');
    const dGat = $('defendants').querySelector('input[data-field="gat"]');
    const dCult = $('defendants').querySelector('input[data-field="cultivable"]');
    const dPot = $('defendants').querySelector('input[data-field="potkharab"]');
    const dAss = $('defendants').querySelector('input[data-field="assessment"]');
    if (dName) dName.value = 'विजय रामचंद्र शिंदे';
    if (dAddr) dAddr.value = 'आंबेगाव, ता. जुन्नर';
    if (dGat) dGat.value = '१२४';
    if (dCult) dCult.value = '०.८०';
    if (dPot) dPot.value = '०.००';
    if (dAss) dAss.value = '९.२०';

    $('preexistingUse').value = 'गेल्या अनेक वर्षांपासून शेतात बैलगाडी, ट्रॅक्टर व पायी येण्या-जाण्यासाठी वहिवाट आहे.';
    $('routeDescription').value = 'गट क्रमांक १२४ च्या पश्चिमेकडील बांधावरून जाणारा रस्ता';
    $('villageRoad').checked = true;
    $('widthFt').value = '१२';
    $('lengthFt').value = '२००';

    $('obstructionDate').value = '2026-09-15';
    $('obstructionGat').value = '१२४';
    const exactConf = document.querySelector('input[name="gatConfidence"][value="exact"]');
    if (exactConf) exactConf.checked = true;
    const selfRole = document.querySelector('input[name="obstructorRole"][value="स्वतः खातेदार"]');
    if (selfRole) selfRole.checked = true;
    $('obstructionDescription').value = 'मोठे दगड व मातीचा भराव टाकून रस्ता पूर्ण बंद केला';
    const stat1 = document.querySelector('input[name="status"][value="1"]');
    if (stat1) stat1.checked = true;
    $('accessEffect').value = 'ट्रॅक्टर व शेती अवजारे शेतात नेता येत नाहीत';
    $('specificHarm').value = 'ऊस पिकाला वेळेवर पाणी व खते देणे अशक्य झाले आहे';

    const standingCrop = document.querySelector('input[name="cropStatus"][value="standing"]');
    if (standingCrop) standingCrop.checked = true;
    updateConditional();

    const u2 = document.querySelector('#urgencyOptions input[value="2"]');
    if (u2) u2.checked = true;
    const uhYes = document.querySelector('input[name="urgentHearing"][value="yes"]');
    if (uhYes) uhYes.checked = true;

    const ev0 = document.querySelector('#evidenceOptions input[value="रस्ता दर्शविणारा नकाशा"]');
    const ev4 = document.querySelector('#evidenceOptions input[value="जुने फोटो"]');
    if (ev0) ev0.checked = true;
    if (ev4) ev4.checked = true;
    updateConditional();

    const at0 = document.querySelector('#attachedOptions input[value="रस्ता दर्शविणारा नकाशा"]');
    const at4 = document.querySelector('#attachedOptions input[value="जुने फोटो"]');
    if (at0) at0.checked = true;
    if (at4) at4.checked = true;

    const attYes = document.querySelector('input[name="attemptsMade"][value="yes"]');
    if (attYes) attYes.checked = true;
    updateConditional();

    const atOpt1 = document.querySelector('#attemptOptions input[value="प्रतिवादींना वैयक्तिक विनंती"]');
    if (atOpt1) atOpt1.checked = true;
    const respNakar = document.querySelector('input[name="defendantResponse"][value="नकार"]');
    if (respNakar) respNakar.checked = true;

    $('filingDate').value = '2026-10-24';
    clearPreview();
    updateConditional();
    setStep(6); // Jump straight to Screen 7 (पुनरावलोकन) for instant testing!
  }

  if ($('fillSampleBtn')) $('fillSampleBtn').onclick = fillSample;
  const handleSelectAll = () => {
    document.querySelectorAll('#paragraphPreview .para-review').forEach(c => { c.checked = true; });
    $('reviewConfirm').checked = true;
    updateDownloadGate();
  };
  if ($('selectAllAiChecksBtn')) $('selectAllAiChecksBtn').onclick = handleSelectAll;
  if ($('selectAllAiChecksBtnBottom')) $('selectAllAiChecksBtnBottom').onclick = handleSelectAll;

  $('previewBtn').onclick = preview;
  $('aiPreviewBtn').onclick = aiPreview;
  $('downloadBtn').onclick = download;
  $('reviewConfirm').onchange = updateDownloadGate;

  $('filingDate').value = new Date().toLocaleDateString('en-CA');

  setupChips();

  if ($('ocrBtn') && $('ocrInput')) {
    $('ocrBtn').onclick = () => $('ocrInput').click();
    $('ocrInput').onchange = (e) => {
      const file = e.target.files?.[0];
      if (!file) return;
      const res = $('ocrResult');
      res.hidden = false;
      res.replaceChildren();
      res.append(el('p', { class: 'help' }, `निवडलेली फाईल: ${file.name} — ओसीआर खातेदार वाचन (अंदाजित चाचणी, प्रत्यक्ष तपासणी आवश्यक):`));
      const sampleNames = ['अजय गणपत पाटील', 'विजय रामचंद्र शिंदे', 'रामचंद्र मारुती जगताप', 'दत्तात्रय सोपान कदम'];
      sampleNames.forEach(name => {
        const btnP = el('button', { type: 'button', class: 'chip' }, `+ वादी नाव: ${name}`);
        btnP.onclick = () => {
          const firstPl = $('plaintiffs').querySelector('input[data-field="name"]');
          if (firstPl) firstPl.value = name;
        };
        const btnD = el('button', { type: 'button', class: 'chip', style: 'margin-left: 4px;' }, `+ प्रतिवादी नाव: ${name}`);
        btnD.onclick = () => {
          const firstDf = $('defendants').querySelector('input[data-field="name"]');
          if (firstDf) firstDf.value = name;
        };
        const row = el('div', { style: 'margin-bottom: 6px;' });
        row.append(btnP, btnD);
        res.append(row);
      });
    };
  }

  try {
    const availability = await (await fetch('/api/status', { cache: 'no-store' })).json();
    if (availability.ai_available) {
      const providerLabel = availability.ai_provider || 'कॉन्फिगर केलेला AI प्रदाता';
      $('aiStatus').textContent = `AI सेवा उपलब्ध आहे (प्रदाता: ${providerLabel}).`;
      $('aiProviderName').textContent = providerLabel;
      $('aiProviderDetails').hidden = false;
      $('aiConsentLabel').hidden = false;
      $('aiConsent').checked = false; // Always unchecked by default
      $('aiPreviewBtn').disabled = false;
    } else {
      $('aiStatus').textContent = 'AI सेवा कॉन्फिगर केलेली नाही (AI service not configured).';
      $('aiProviderDetails').hidden = true;
      $('aiConsentLabel').hidden = true;
      $('aiConsent').checked = false;
      $('aiPreviewBtn').disabled = true;
      $('aiPreviewBtn').title = 'AI सेवा कॉन्फिगर केलेली नाही. नियमाधारित मसुदा वापरा.';
    }
  } catch (e) {
    $('aiStatus').textContent = 'AI सेवा कॉन्फिगर केलेली नाही (AI service not configured).';
    $('aiProviderDetails').hidden = true;
    $('aiConsentLabel').hidden = true;
    $('aiConsent').checked = false;
    $('aiPreviewBtn').disabled = true;
  }

  updateConditional();
  setStep(0);
}

init().catch(e => err('नमुना सुरू करताना त्रुटी: ' + e));
