export const SECTION_LABELS={subjective:'History & patient report',objective:'Examination & observations',assessment:'Clinician assessment',plan:'Clinician plan'};
export const uid=()=>crypto.randomUUID();
export function parseTranscript(text){
 return text.split('\n').map(s=>s.trim()).filter(Boolean).map((line,i)=>{const match=line.match(/^(Patient|Doctor|Clinician|Nurse|Unknown)\s*:\s*(.*)$/i);const role=match?match[1].toLowerCase():'unknown';return {id:`s${i+1}`,order:i+1,role:role==='doctor'?'clinician':role,text:match?match[2]:line,raw:line}});
}
export function generateDraft(encounter){
 const spans=parseTranscript(encounter.transcript),sections=Object.keys(SECTION_LABELS).map(key=>({key,label:SECTION_LABELS[key],items:[]})),issues=[];
 for(const span of spans){let key='subjective',text=span.text;const uncertain=/\[(unclear|inaudible|speaker uncertain)\]/i.test(text);
 if(uncertain){issues.push({id:`issue-${span.id}`,spanId:span.id,kind:'clarification',blocking:true,title:'Source needs clarification',detail:'An unclear passage was left out of the draft. Correct the source or remove the passage before drafting it.'});continue;}
 if(span.role==='unknown'){issues.push({id:`issue-${span.id}`,spanId:span.id,kind:'speaker',blocking:true,title:'Confirm who said this',detail:'This passage was left out because the speaker role is unknown. Label it in the transcript before generating again.'});continue;}
 if(span.role==='clinician'||span.role==='nurse'){
 const label=text.match(/^(Assessment|Plan|Exam|Observation|History)\s*:\s*(.*)$/i);
 if(label){const map={assessment:'assessment',plan:'plan',exam:'objective',observation:'objective',history:'subjective'};key=map[label[1].toLowerCase()];text=label[2];
 if((key==='assessment'||key==='plan')&&span.role!=='clinician'){issues.push({id:`issue-${span.id}`,spanId:span.id,kind:'speaker',blocking:true,title:'Clinician attribution needed',detail:'This draft only places explicitly labeled clinician statements in Assessment and Plan. Confirm attribution in the source.'});continue;}}
 else if(text.endsWith('?'))continue;
 }
 if(!text.trim())continue;
 sections.find(s=>s.key===key).items.push({id:`item-${span.id}`,text:text.trim(),role:span.role,sourceIds:[span.id],origin:'source',uncertain:/\b(possible|possibly|uncertain|not confirmed|may|might|not established)\b/i.test(text)});
 }
 for(const section of sections)if(!section.items.length)issues.push({id:`missing-${section.key}`,kind:'missing',blocking:false,title:`${section.label} not documented`,detail:'This section is intentionally empty. Add the clinician’s actual statement to the source if it should be documented.'});
 return {id:uid(),version:(encounter.draft?.version||0)+1,sourceVersion:encounter.sourceVersion,sourceHash:hash(encounter.transcript),template:encounter.template||'soap',sections,issues,spans,createdAt:new Date().toISOString(),revision:1,approval:null};
}
export function hash(text){let h=2166136261;for(let i=0;i<text.length;i++){h^=text.charCodeAt(i);h=Math.imul(h,16777619)}return (h>>>0).toString(16)} // Change marker only, not a security digest.
export function isCurrent(e){return !!e.draft&&e.draft.sourceVersion===e.sourceVersion&&(e.draft.hashAlgorithm==='sha256'||e.draft.sourceHash===hash(e.transcript))&&e.draft.template===e.template;}
export function canApprove(e){return isCurrent(e)&&!e.draft.issues.some(i=>i.blocking)&&e.draft.sections.some(s=>s.items.some(i=>i.text.trim()));}
export function approvedCurrent(e){return canApprove(e)&&!!e.draft.approval&&e.draft.approval.revision===e.draft.revision&&e.draft.approval.sourceVersion===e.sourceVersion;}
export function updateSource(e,text){if(text===e.transcript)return false;e.transcript=text;e.sourceVersion++;e.updatedAt=new Date().toISOString();return true;}
export function updateItem(e,itemId,text){const item=e.draft?.sections.flatMap(s=>s.items).find(i=>i.id===itemId);if(!item||item.text===text)return false;item.text=text;item.origin='manual';e.draft.revision++;e.draft.approval=null;return true;}
export function approve(e,reviewer){if(!canApprove(e))throw new Error('Current draft with resolved source issues required.');if(!reviewer?.trim())throw new Error('Enter a reviewer name.');e.draft.approval={reviewer:reviewer.trim(),at:new Date().toISOString(),revision:e.draft.revision,sourceVersion:e.sourceVersion};}
export function exportPayload(e){if(!approvedCurrent(e))throw new Error('Approve the current draft before export.');return {schema:'clinicnote-demo-export/1',syntheticDemo:true,encounterId:e.id,patient:e.patient,sourceVersion:e.sourceVersion,draftVersion:e.draft.version,revision:e.draft.revision,template:e.template,approval:e.draft.approval,sections:e.draft.sections.map(s=>({name:s.label,items:s.items.map(i=>({text:i.text,attribution:i.role,sourceIds:i.sourceIds,origin:i.origin}))})),sourceSpans:e.draft.spans.map(s=>({id:s.id,role:s.role,text:s.text,line:s.order,sourceVersion:e.draft.sourceVersion})),integrationStatus:'download_only_not_sent_to_ehr'};}
export function noteText(e){const p=exportPayload(e);return [`${p.patient.name} · ${e.visitType}`,`Synthetic demo · ${e.date}`,`Reviewed by ${p.approval.reviewer}`,...p.sections.flatMap(s=>['',s.name.toUpperCase(),...(s.items.length?s.items.map(i=>`${i.attribution==='patient'?'Patient reports: ':i.attribution==='clinician'?'Clinician stated: ':''}${i.text}`):['Not documented in source.'])])].join('\n');}
export function status(e){if(approvedCurrent(e))return 'Approved';if(e.draft&&!isCurrent(e))return 'Needs refresh';if(e.draft?.issues.some(i=>i.blocking))return 'Needs clarification';if(e.draft)return 'Ready to review';return e.transcript?'Ready to draft':'New encounter';}
