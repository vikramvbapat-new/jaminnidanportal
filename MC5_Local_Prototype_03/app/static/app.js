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
    width_ft: $('widthFt').value.trim(),
    length_ft: $('lengthFt').value.trim(),
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
  const message = Array.isArray(e) ? e.map(x => '• ' + x).join('\n') : String(e);
  $('errors').textContent = message;
  $('errors').hidden = false;
  $('errors').scrollIntoView({ behavior: 'smooth' });
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
  const ok = $('reviewConfirm').checked && (lastToken || lastAI) &&
    (lastMode !== 'ai' || (checks.length > 0 && checks.every(x => x.checked)));
  $('downloadBtn').disabled = !ok;
}

function showDraft(data, mode) {
  lastMode = mode;
  $('previewHeading').textContent = mode === 'ai'
    ? 'AI भाषिक मसुद्याचे पुनरावलोकन'
    : 'नियमाधारित अर्जाचे संपूर्ण पूर्वावलोकन (१३ परिच्छेद)';

  $('previewModeInfo').textContent = mode === 'ai'
    ? 'AI ने काही निवडक परिच्छेदांची भाषा सुचवली आहे. निश्चित परिच्छेद आणि सर्व मागण्या प्रणालीने लॉक केल्या आहेत. प्रत्येक परिच्छेद स्वतंत्रपणे तपासा.'
    : 'हे AI-generated लेखन नाही. पुष्टी झालेले स्रोत फील्ड वापरून नियमाधारित मसुदा तयार झाला आहे.';

  $('limitationNotice').textContent = data.limitation.warning || data.export_label;

  // Update session badge
  if (data.draft_id) {
    sessionMeta.draft_id = data.draft_id;
    sessionMeta.started_at = data.started_at;
    sessionMeta.word_revision = data.word_revision || 1;
    $('sessionBadge').textContent = `सत्र: ${data.draft_id.slice(0, 8)}... (३० दिवस वैध)`;
    $('sessionBadge').title = `सत्र सुरू: ${data.started_at} | वैध मुदत: ${data.expires_at}`;
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
    showDraft(data, 'ai');
  } catch (e) {
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
    const payload = isAi ? {
      data: normalize(),
      candidate: lastAI.candidate,
      review_token: lastAI.review_token,
      review_confirmed: $('reviewConfirm').checked,
      reviewed_paragraph_numbers: [...document.querySelectorAll('#paragraphPreview .para-review:checked')].map(x => Number(x.value))
    } : {
      data: normalize(),
      preview_token: lastToken,
      review_confirmed: $('reviewConfirm').checked
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
    const targetInput = $(targetId);
    if (!targetInput) return;

    row.querySelectorAll('.chip').forEach(btn => {
      btn.addEventListener('click', () => {
        let text = btn.textContent.trim();
        if (text.startsWith('+ ')) text = text.slice(2).trim();

        if (!targetInput.value.trim()) {
          targetInput.value = text;
        } else if (!targetInput.value.includes(text)) {
          targetInput.value = targetInput.value.trim() + '\n' + text;
        }
        targetInput.dispatchEvent(new Event('input', { bubbles: true }));
        clearPreview();
      });
    });
  });
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

  $('mainForm').addEventListener('input', e => {
    if (e.target.id === 'reviewConfirm') return;
    clearPreview();
    updateConditional();
  });

  $('mainForm').addEventListener('change', e => {
    if (e.target.id === 'reviewConfirm') return;
    clearPreview();
    updateConditional();
  });

  $('addPlaintiff').onclick = () => { addParty('plaintiffs'); clearPreview(); };
  $('addDefendant').onclick = () => { addParty('defendants'); clearPreview(); };

  $('backBtn').onclick = () => setStep(currentStep - 1);
  $('nextBtn').onclick = () => setStep(currentStep + 1);

  document.querySelectorAll('.steps button').forEach(b => {
    b.onclick = () => setStep(Number(b.dataset.step));
  });

  $('previewBtn').onclick = preview;
  $('aiPreviewBtn').onclick = aiPreview;
  $('downloadBtn').onclick = download;
  $('reviewConfirm').onchange = updateDownloadGate;

  $('filingDate').value = new Date().toLocaleDateString('en-CA');

  setupChips();

  try {
    const availability = await (await fetch('/api/status', { cache: 'no-store' })).json();
    $('aiStatus').textContent = availability.ai_available
      ? 'AI सेवा सर्व्हरवर उपलब्ध आहे; प्रत्येक विनंतीसाठी स्वतंत्र स्पष्ट संमती आवश्यक.'
      : 'AI सेवा बंद आहे. सुरक्षित स्थानिक नियमाधारित मोड उपलब्ध आहे.';
    $('aiPreviewBtn').disabled = !availability.ai_available;
  } catch (e) {
    $('aiStatus').textContent = 'AI स्थिती सध्या उपलब्ध नाही.';
  }

  updateConditional();
  setStep(0);
}

init().catch(e => err('नमुना सुरू करताना त्रुटी: ' + e));
