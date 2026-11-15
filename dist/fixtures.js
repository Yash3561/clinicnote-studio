export const fixtures=[
 {id:'visit-avery',patient:{name:'Avery Morgan',initials:'AM',age:42,recordId:'DEMO-1042'},time:'09:00',visitType:'Primary care · preventive follow-up',reason:'Fatigue and sleep concerns',date:'Nov 15, 2026',template:'soap',sourceVersion:1,transcript:`Patient: I have felt more tired than usual for the past week.
Patient: My sleep has been interrupted this week.
Patient: My sister was previously diagnosed with a thyroid condition. I have not been diagnosed with it.
Clinician: Assessment: Fatigue is reported; its cause is not established in this encounter.
Clinician: Plan: We agreed that I will review the available history and discuss the next steps with the patient.`,accent:'sage'},
 {id:'visit-jordan',patient:{name:'Jordan Lee',initials:'JL',age:57,recordId:'DEMO-2057'},time:'09:30',visitType:'Cardiology · follow-up',reason:'Review of reported symptoms',date:'Nov 15, 2026',template:'soap',sourceVersion:1,transcript:`Patient: I am here to discuss the symptoms I described at my last visit.
Patient: I have not brought my home measurement log today.
Clinician: History: The home measurement log is not available for review in this encounter.
Clinician: Assessment: The explanation for the reported symptoms remains uncertain; no new diagnosis was stated today.
Clinician: Plan: We agreed to review the missing log at a subsequent discussion.`,accent:'sand'},
 {id:'visit-riley',patient:{name:'Riley Bennett',initials:'RB',age:36,recordId:'DEMO-3036'},time:'10:00',visitType:'Primary care · medication history',reason:'Clarify medication history',date:'Nov 15, 2026',template:'soap',sourceVersion:1,transcript:`Patient: I want to check that my medication history was recorded correctly.
Patient: The amount I mentioned was [unclear].
Unknown: We should update the history.
Clinician: Assessment: The medication history needs clarification; the amount is not confirmed.
Clinician: Plan: I will verify the history with the patient before documenting the amount.`,accent:'lilac'}
];
export function freshFixtures(){return structuredClone(fixtures).map(e=>({...e,draft:null,previousDraft:null,audit:[],exportCount:0}));}
