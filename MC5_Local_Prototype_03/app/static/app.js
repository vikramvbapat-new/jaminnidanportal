/* MC5 development UI; AI strictly opt-in and off by default. No localStorage, analytics, account, OCR or uploads. */
'use strict';
const $ = id => document.getElementById(id);
let options = null, currentStep = 0, lastToken = null, lastAI=null, lastMode="rules";
const pages = [...document.querySelectorAll('.step')];
const getRadio = n => document.querySelector(`input[name="${n}"]:checked`)?.value || null;
const checkedValues = box => [...box.querySelectorAll('input[type=checkbox]:checked')].map(x => x.value);
const clearPreview = () => {lastToken=null;lastAI=null;lastMode='rules';$('reviewConfirm').checked=false;$('downloadBtn').disabled=true;$('preview').hidden=true;};
function el(tag, attrs={}, text='') {
 const e=document.createElement(tag);
 for(const [k,v] of Object.entries(attrs)) {if(k==='class')e.className=v;else if(k==='type')e.type=v;else e.setAttribute(k,v)}
 if(text)e.textContent=text;return e;
}
function listOptions(target, entries, kind, groupName, valueFn) {
 const root=$(target);root.replaceChildren();
 entries.forEach((item,i)=>{
  const val=valueFn?valueFn(item,i):item;const label=el('label',{class:'choice'});
  const input=el('input',{type:kind,name:groupName,value:String(val)});
  label.append(input,document.createTextNode(typeof item==='string'?item:item.label));root.append(label);
 });
}
function addParty(target) {
 const count=$(target).querySelectorAll('.person').length+1;
 const box=el('div',{class:'person'});box.dataset.party=target;
 const header=el('header');header.append(el('strong',{},(target==='plaintiffs'?'वादी':'प्रतिवादी')+' — '+count));
 const rm=el('button',{type:'button',class:'remove'},'काढा');rm.addEventListener('click',()=>{box.remove();clearPreview()});header.append(rm);box.append(header);
 const grid=el('div',{class:'twocol'});
 [['name','पूर्ण नाव'],['address','पत्ता'],['gat','गट क्रमांक'],['cultivable','लागवडीलायक क्षेत्र (हे.आर.)'],['potkharab','पोटखराब (हे.आर.; नसल्यास ०)'],['assessment','आकार (रुपये-पैसे; नसल्यास ०)']].forEach(([k,title])=>{
  const lab=el('label',{},title),inp=el('input',{type:'text','data-field':k});lab.append(inp);grid.append(lab)
 });
 box.append(grid);$(target).append(box);
}
function partyData(type){return [...$(type).querySelectorAll('.person')].map(p=>Object.fromEntries([...p.querySelectorAll('input')].map(input=>[input.dataset.field,input.value.trim()])))}
function setStep(n){currentStep=Math.max(0,Math.min(6,n));pages.forEach((p,i)=>{p.classList.toggle('show',i===currentStep)});document.querySelectorAll('.steps button').forEach((b,i)=>b.classList.toggle('active',i===currentStep));$('stepPos').textContent=`टप्पा ${currentStep+1} / ७`;$('backBtn').hidden=currentStep===0;$('nextBtn').hidden=currentStep===6;window.scrollTo({top:0,behavior:'smooth'})}
function valuesFor(selector){return [...document.querySelectorAll(selector+':checked')].map(x=>x.value)}
function selectedReasons(){return valuesFor('#urgencyOptions input').map(Number)}
function updateConditional(){
 const status=Number(getRadio('status')||0);const crop=getRadio('cropStatus');let allowed=[];
 if(status!==3){allowed=[5,6];if(['not_grown','planned'].includes(crop))allowed.push(1);if(crop==='standing')allowed.push(2,3,4);if(crop==='harvested'||$('harvestedStock')?.checked)allowed.push(3)}
 $('urgencyArea').hidden=status===3;
 if(status===3){document.querySelectorAll('#urgencyOptions input').forEach(x=>x.checked=false);}
 [...$('urgencyOptions').querySelectorAll('label')].forEach((label,i)=>{
  label.hidden=!allowed.includes(i+1);if(!allowed.includes(i+1))label.querySelector('input').checked=false;
 });
 const reasons=selectedReasons();
 ['reason3Wrap','reason4Wrap','reason5Wrap'].forEach((id,i)=>{
  const chosen=reasons.includes([3,4,5][i]);$(id).hidden=!chosen;
  if(!chosen)$(id).querySelectorAll('input').forEach(x=>x.checked=false);
 });
 $('urgentHearingWrap').hidden=!(status!==3&&reasons.length);
 if($('urgentHearingWrap').hidden)document.querySelectorAll('input[name=urgentHearing]').forEach(x=>x.checked=false);
 $('effectWrap').querySelector('textarea').placeholder=status===3?'पूर्वी झालेला परिणाम (असल्यास); सध्या अडथळा कायम असल्याचे लिहू नका':'अडथळ्यामुळे रस्त्याच्या वापरात आलेली प्रत्यक्ष अडचण';
}
function normalize(){
 const reasons=selectedReasons();const status=Number(getRadio('status')||0);
 const uh=getRadio('urgentHearing');
 return {village:$('village').value.trim(),taluka:$('taluka').value.trim(),district:$('district').value.trim(),
  map_ack:$('mapAck').checked,plaintiffs:partyData('plaintiffs'),defendants:partyData('defendants'),
  preexisting_use:$('preexistingUse').value.trim(),route_description:$('routeDescription').value.trim(),
  village_road_confirmed:$('villageRoad').checked,width_ft:$('widthFt').value.trim(),length_ft:$('lengthFt').value.trim(),
  obstruction_date:$('obstructionDate').value,obstruction_gat:$('obstructionGat').value.trim(),
  obstruction_gat_confidence:getRadio('gatConfidence'),obstructor_role:getRadio('obstructorRole'),
  obstruction_description:$('obstructionDescription').value.trim(),status,
  access_effect:$('accessEffect').value.trim(),specific_harm:$('specificHarm').value.trim(),
  crop_status:getRadio('cropStatus'),harvested_stock:$('harvestedStock')?.checked||false,
  urgency_reasons:reasons,reason3_details:checkedValues($('reason3Options')),
  reason4_damage:getRadio('reason4Damage'),house_confirmed:$('houseConfirmed').checked,
  urgent_hearing:uh===null?null:uh==='yes',
  evidence:checkedValues($('evidenceOptions')),attached_docs:checkedValues($('attachedOptions')),
  attempts_made:getRadio('attemptsMade')==='yes',attempt_types:checkedValues($('attemptOptions')),
  defendant_response:getRadio('defendantResponse'),filing_date:$('filingDate').value};
}
function err(e){const message=Array.isArray(e)?e.map(x=>'• '+x).join('\n'):String(e);$('errors').textContent=message;$('errors').hidden=false;}
async function callApi(path,body){
 const res=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body),cache:'no-store'});
 if(!res.ok){let d={};try{d=await res.json()}catch{}throw (d.detail||'सर्व्हरने विनंती स्वीकारली नाही.')}return res;
}
function updateDownloadGate(){
 const checks=[...document.querySelectorAll('#paragraphPreview .para-review')];
 $('downloadBtn').disabled=!($('reviewConfirm').checked&&(lastToken||lastAI) && (lastMode!=='ai'||(checks.length>0&&checks.every(x=>x.checked))));
}
function showDraft(data, mode){
 lastMode=mode;
 $('previewHeading').textContent=mode==='ai'?'AI भाषिक मसुद्याचे पुनरावलोकन':'नियमाधारित अर्जाचे पूर्वावलोकन';
 $('previewModeInfo').textContent=mode==='ai'?'AI ने काही परिच्छेदांची भाषा सुचवली आहे. निश्चित परिच्छेद आणि सर्व मागण्या प्रणालीने लॉक केल्या आहेत. प्रत्येक विधान स्वतंत्रपणे तपासा.':'हे AI-generated लेखन नाही. स्रोत फील्ड वापरून नियमाधारित चाचणी मसुदा तयार झाला आहे.';
 $('limitationNotice').textContent=data.limitation.warning||data.export_label;
 const paragraphs=$('paragraphPreview');paragraphs.replaceChildren();
 data.paragraphs.forEach(p=>{const h=el('strong',{},`${p.number}) ${p.subject} :`),txt=el('p',{},p.text);paragraphs.append(h,txt);
  if(mode==='ai'){const foot=el('p',{class:'help'},`लेखन: ${p.drafting_mode==='AI_REPHRASED_REVIEW_REQUIRED'?'AI भाषिक परीक्षण':'मूळ नियम निश्चित'} · स्रोत: ${(p.source_field_ids||[]).join(', ')}`);paragraphs.append(foot);
   const label=el('label',{class:'choice'},' हा परिच्छेद तपासला.');const check=el('input',{type:'checkbox',class:'para-review',value:String(p.number)});check.addEventListener('change',updateDownloadGate);label.prepend(check);paragraphs.append(label);}
 });
 const prayers=$('prayerPreview');prayers.replaceChildren();data.prayers.forEach(p=>prayers.append(el('p',{},`${p.display_number}) ${p.text}`)));
 $('preview').hidden=false;$('reviewConfirm').checked=false;$('downloadBtn').disabled=true;$('preview').scrollIntoView({behavior:'smooth'});
}
async function aiPreview(){
 $('errors').hidden=true;clearPreview();
 if(!$('aiConsent').checked){err('या AI विनंतीसाठी स्वतंत्र संमती आवश्यक आहे.');return;}
 try{
  const response=await callApi('/api/ai-preview',{data:normalize(),explicit_external_ai_consent:true});
  const data=await response.json();
  lastAI={candidate:{paragraphs:data.paragraphs.filter(p=>p.drafting_mode==='AI_REPHRASED_REVIEW_REQUIRED').map(p=>({number:p.number,text:p.text}))},review_token:data.review_token};
  showDraft(data,'ai');
 }catch(e){err(e)}
}
async function preview(){
 $('errors').hidden=true;clearPreview();let payload=normalize();
 if(!$('mapAck').checked){err(['नकाशाविषयक सूचना वाचल्याची पुष्टी द्या.']);return;}
 try{
  let res=await callApi('/api/preview',{data:payload}),data=await res.json();lastToken=data.preview_token;showDraft(data,'rules');
 }catch(e){err(e)}
}
async function download(){
 try{
  const res=await callApi(lastMode==='ai'?'/api/ai-docx':'/api/docx',lastMode==='ai'?{data:normalize(),candidate:lastAI.candidate,review_token:lastAI.review_token,review_confirmed:$('reviewConfirm').checked,reviewed_paragraph_numbers:[...document.querySelectorAll('#paragraphPreview .para-review:checked')].map(x=>Number(x.value))}:{data:normalize(),preview_token:lastToken,review_confirmed:$('reviewConfirm').checked});
  const file=await res.blob(),url=URL.createObjectURL(file),a=el('a');a.href=url;a.download=lastMode==='ai'?'MC5_AI_REVIEW_ONLY.docx':'MC5_RULES_REVIEW_ONLY.docx';document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),3000);
 }catch(e){err(e)}
}
async function init(){
 options=await (await fetch('/api/options',{cache:'no-store'})).json();
 listOptions('statusOptions',Object.entries(options.status).map(([k,v])=>({label:v,k})), 'radio','status',i=>i.k);
 listOptions('cropOptions',Object.entries(options.crop).map(([k,v])=>({label:v,k})), 'radio','cropStatus',i=>i.k);
 listOptions('urgencyOptions',options.reasons,'checkbox','urgencyReasons',i=>Number(i.id.split('-')[1]));
 listOptions('reason3Options',options.reasons[2].suboptions,'checkbox','reason3Details');
 listOptions('reason4Options',options.reasons[3].suboptions,'radio','reason4Damage');
 listOptions('evidenceOptions',options.evidence,'checkbox','evidence');
 listOptions('attachedOptions',options.evidence,'checkbox','attachedDocs');
 listOptions('attemptOptions',options.attempts,'checkbox','attemptTypes');
 listOptions('responseOptions',options.responses,'radio','defendantResponse');
 addParty('plaintiffs');addParty('defendants');
 $('cropOptions').querySelector('input').checked=true;
 $('mainForm').addEventListener('input',(e)=>{if(e.target.id==='reviewConfirm')return;clearPreview();updateConditional();});
 $('mainForm').addEventListener('change',(e)=>{if(e.target.id==='reviewConfirm')return;clearPreview();updateConditional();});
 $('addPlaintiff').onclick=()=>{addParty('plaintiffs');clearPreview()};$('addDefendant').onclick=()=>{addParty('defendants');clearPreview()};
 $('backBtn').onclick=()=>setStep(currentStep-1);$('nextBtn').onclick=()=>setStep(currentStep+1);
 document.querySelectorAll('.steps button').forEach(b=>b.onclick=()=>setStep(Number(b.dataset.step)));
 $('previewBtn').onclick=preview;$('aiPreviewBtn').onclick=aiPreview;$('downloadBtn').onclick=download;
 $('reviewConfirm').onchange=updateDownloadGate;
 $('filingDate').value=new Date().toLocaleDateString('en-CA');
 try{
  const availability=await (await fetch('/api/status',{cache:'no-store'})).json();
  $('aiStatus').textContent=availability.ai_available?'AI सेवा सर्व्हरवर उपलब्ध आहे; प्रत्येक विनंतीसाठी स्पष्ट संमती आवश्यक.':'AI सेवा उपलब्ध नाही. डिफॉल्ट सुरक्षित स्थानिक नियमाधारित मोड वापरा.';
  $('aiPreviewBtn').disabled=!availability.ai_available;
 }catch(e){$('aiStatus').textContent='AI स्थिती सध्या उपलब्ध नाही.';}
 updateConditional();setStep(0);
}
init().catch(e=>err('नमुना सुरु करताना त्रुटी: '+e));
