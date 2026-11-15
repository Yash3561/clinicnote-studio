# v2 scope update

The hosted Site remains a synthetic browser preview. A working local API, persistence, speech/model adapter, context/task APIs and revised design now exist. Read [the current model and scale plan](MODEL_AND_SCALE_PLAN.md) for current implementation and limitations. The v1 description below is historical where they differ.

# ClinicNote Studio — product and integration plan

Independent prototype, November 15, 2026. The intended first audience is a primary-care physician reviewing a preventive-care follow-up. Navierre's public about page identifies Dr. Sakina Dinani as co-founder, Chief Medical Officer, and a primary-care physician with a preventive-care focus: https://www.navierre.com/about . Her personal workflows, EHR, note preferences, customers, patient data, and current internal architecture have not been confirmed. This is a suggested workflow for feedback, not a Navierre product or endorsement.

## Product promise and first pilot question

Make an encounter easier to finish: capture input, inspect the original evidence, review a clear draft, and hand off the version the clinician approved. The first pilot should establish whether this reduces documentation/review effort while preserving useful facts and avoiding unsupported interpretations. No time savings, model accuracy, clinical effectiveness, or regulatory status is assumed.

The design deliberately keeps the physician's main work together: encounter identity, editable note, supporting source and review status. The path is worklist → capture → review → export. Evidence opens alongside the note, rather than sending the user to another application. Workflow placement inside a host is a separate design preview; it is not a connected integration.

## What is functional now

- Three synthetic encounter records, search and patient/encounter selection.
- A preventive primary-care follow-up; a specialty follow-up; and a medication-history clarification scenario.
- Creating additional fictional encounters.
- Recording and uploading audio locally when the browser supports it. Audio playback stays in the tab, is not sent to a service, and does not persist across reloads. No audio transcription runs here.
- Transcript entry/editing with explicit Patient/Clinician/Nurse/Unknown speaker labels. Uncommitted input survives UI navigation in this tab; Save commits a new source version. Explicit clinician sections use Assessment, Plan, Exam, Observation or History labels.
- A deterministic draft generator that preserves the source wording. It is a parser and renderer, not an LLM, diagnostic system, general clinical NLP model, or assessment of medical correctness.
- SOAP and visit-note presentation over the same source evidence. Missing sections remain visibly undocumented rather than filled with invented text.
- Traceable source IDs, uncertainty markers based on a small transparent word list, missing-section notices and blocking unknown/unclear-source markers.
- Reviewer text edits, marking those edits as manual, and clearing approval when edits change the draft.
- Approval tied to a particular source version, draft version, and draft revision. The confirmation is a local demo action, not authenticated electronic signature.
- Copying and downloading approved notes as text or a documented demo JSON schema, including exact source spans. No data is sent to a clinical system. The export is not a validated FHIR bundle, CDA document or EHR message.
- Read-only previous-draft snapshot, local event history, and demo reset.
- A responsive clinic-workspace placement preview, without external integration or parent-page data exchange.
- Text/approvals/history persist in browser localStorage. This is not clinical storage, shared access, a durable backend, or a tamper-resistant audit system. The published Site itself remains owner-private.

## User journeys and acceptance evidence

### 1. Finish a preventive primary-care visit

Open Avery's encounter. Read the draft and follow source 03 to see that a family member's thyroid history is retained as patient report. The clinician's explicit uncertainty stays intact. Examination is visibly not documented. Edit, review and approve the draft. Copy or download the approved version. Acceptance: correct encounter, attributed text, inspectable sources, visible missingness, and explicit review.

### 2. Resolve unclear documentation

Open Riley's encounter. The source contains [unclear] and an Unknown speaker. Both passages are omitted from the draft and approval is blocked. Correct those source lines using actual known information (synthetic in this demo), save and prepare the updated draft. Acceptance: approval is unavailable until the source issues are resolved; missing information is not guessed. An operator who incorrectly relabels a speaker can still introduce an error, so this is not a guarantee of attribution accuracy.

### 3. Correct the source after approval

Approve an encounter, then modify and save its transcript. The source version increments and the draft becomes stale. The old approval cannot export the new visit. Rebuild, inspect the previous snapshot if useful, review and approve again. Acceptance: version changes require a fresh decision; no silent carry-forward of approval.

### 4. Reviewer makes a note correction

Edit an approved statement. The content becomes reviewer-entered and approval clears immediately. The source reference is retained as context, not proof that the new manual wording is supported. Acceptance: the approval bar, header/worklist status, and export eligibility all update. Clinician-added content still needs the user's review and must not be claimed as model-extracted evidence.

### 5. Place the note inside the clinic workspace

Workspace preview shows a generic host frame, encounter identity and note tool without the standalone worklist. It validates the design concept only. Acceptance: clear encounter context and easy return; no claim that patient launch, SSO or write-back works yet.

## Functional boundaries and failure behavior

The prototype assumes one local user and a small synthetic worklist. It handles empty transcripts, missing speaker labels, explicit unclear markers, template changes, note edits, source changes, empty notes, clipboard denial, unsupported recording, denied microphone, oversized/non-audio upload, and browser-storage failure messages. Reset restores fixtures. It does not detect every negation, correction, diagnostic inference, wrong identity, poor audio segment or malicious clinical assertion. A known-good deterministic draft does not demonstrate how a future probabilistic extractor will behave.

Audio format checks are a browser MIME/size check (50 MB cap), not a secure media-decoding gateway. There is no server, STT, generative inference, diarization, timestamp alignment, semantic verifier, medical-code mapping, EHR connector, shared account system, cross-user synchronization, or production evaluation. No real patient information belongs here.

## Full system to implement next

1. **Host and identity adapter.** Use the existing workspace's supported identity/session flow. Resolve an authorized encounter context from the host; do not trust a patient ID supplied by a browser alone. Confirm whether their environment supports an embedded web view, sanctioned iframe, launch link, or backend integration. Avoid inventing a platform-specific launch mechanism.
2. **Durable encounter API.** Keep tenant, encounter, source version, processing job, draft, reviewer revision, approval and export attempt in transactional storage. Enforce permissions at read/write/export boundaries. Use expected-version updates, idempotency keys, database constraints, and audit events. A frontend warning is not a server-side permission control.
3. **Approved recording ingestion.** Upload securely to approved object storage, verify media properties and size, enforce retention and access, and enqueue work. Scope audio URLs and keep credentials out of the client and logs.
4. **Transcription adapter.** Evaluate an approved provider on language, specialty terms, numbers/units, negation, speakers, noisy/remote visits and operational behavior. Preserve raw transcript, speaker uncertainty and timestamps. Do not let cleanup erase corrections.
5. **Evidence extraction and drafting adapter.** Compare a direct-transcript baseline with structured evidence plus constrained rendering. Preserve speaker, subject, time, polarity, certainty, source spans and explicit clinician assessments/plans. Allow missing information. Do not infer diagnosis from symptoms to complete SOAP sections.
6. **Measured verification.** Validate schema/reference integrity in code; test source support, contradictions, attribution and omissions with domain-reviewed evaluation. A model verifier is fallible and can share errors with the drafter. Hold draft text until checks are complete; stream job status instead.
7. **Review and export adapter.** Authenticate the reviewer and bind the explicit review to exact source/draft/revision. Where the host supports write-back, prepare a preview and re-check authority and source freshness before sending. Persist external request/result IDs and reconcile ambiguous retries; a 202 acknowledgment is not proof of a chart write.
8. **Pilot operations.** Evaluation gates, monitoring, safe logs, provider quotas, retention/deletion, backup/restore, rollout/rollback, incident response and qualified review. The organization's assessment governs clinical/product readiness and compliance; this plan does not certify either.

## Proposed backend contracts

These are implementation contracts, not currently served endpoints.

- POST /v1/encounters/{encounter}/sources: authorize, persist upload/transcript reference/version and idempotency key; return source/job IDs.
- GET /v1/jobs/{job}: authorized processing stage, recoverable error and retry guidance; don't fabricate percentages.
- POST /v1/encounters/{encounter}/drafts: supported template plus expected source version; return a job ID.
- GET /v1/drafts/{draft}: source/draft/schema/model/prompt versions, source-linked content, issues and review eligibility.
- PATCH /v1/drafts/{draft}: expected revision and explicit reviewer edits; increment revision and invalidate prior approval in one transaction.
- POST /v1/drafts/{draft}/approvals: expected source/draft/revision, reviewer identity and required review acknowledgments. Reject stale/conflicting requests.
- POST /v1/drafts/{draft}/exports: target adapter, current approved version and operation key. Separate queued/accepted/confirmed/failed/unknown external outcomes.

The server owns state transitions. Every endpoint checks authenticated tenant/encounter permissions. Authentication context is not accepted from a user-editable body field. Cross-encounter source references, stale approvals and duplicate side effects need integration tests. A queue is generally at-least-once; use durable idempotency, bounded retries, recovery and an outbox if DB/queue publishing consistency requires it.

## Integration discovery checklist

Ask the team which encounter object and identity source already exist; who may record, edit, approve and export; where note templates live; which clinical system is the destination; which scopes/APIs and chart-write semantics are supported; who owns mappings; how conflicts are handled; and what sandbox/data permission is available. Ask clinicians whether evidence playback and missing-information markers fit their review workflow.

Where FHIR/SMART or another standard is actually available, verify the destination's supported version/resources/scopes and the institution's review/write rules. Do not label the demo export FHIR-compatible simply because it is JSON. An iframe alone is not integration: it still needs encounter launch, identity, permission, status synchronization and a tested adapter. “No extra login/re-entry” is a design target dependent on host support, not a promise made by this prototype.

## Build decisions and alternatives

- **Static, buildless prototype now:** quick private sharing, low dependency cost and browser-local interactions. Alternative: a hosted backend immediately. Deferred until identity, provider permissions and persistence requirements are known; using localStorage with real records is not an acceptable replacement.
- **Deterministic drafting now:** transparent, inspectable sources and reliable demo state. Alternative: unconfigured live model calls from the browser. Avoided because it exposes credentials/data and could imply a validated model path that has not been built.
- **Evidence beside the note:** maintains context during review. Alternative: links to a separate page for every fact. More disruption for a common review task; test both with clinicians.
- **Missing sections remain empty:** prevents invented template completion. Alternative: guess normal findings or an assessment. Conflicts with the reported failure and requires a different intended use.
- **Explicit version-bound review:** changes cannot inherit old approval. Alternative: a generic “approved patient” flag. Too broad and unsafe for regenerated content.
- **Local copy/download first:** truthful end-to-end handoff without a fabricated connector. Alternative: a fake “Sent to EHR” success screen. Would conceal integration work and undermine buyer trust.
- **Two layouts over the same evidence:** tests clinician preference without generating new medical content. A future patient-facing summary requires its own language/omission/approval evaluation; it is not silently repurposed from a clinician note.

## Demo presentation for a nontechnical clinical audience

“After the visit, you need a clear note you can trust enough to review efficiently. Here is the original statement behind this section. The clinician's uncertainty is preserved, and an unspoken exam is left blank. You can correct the draft, approve this exact version, and take the note into your next step. When a source changes, the system asks for a fresh review. We would use a limited pilot to measure note corrections, completion and review effort before claiming savings.”

Five-minute walkthrough: Avery's review → source 03 → one edit → approval → local export → Riley's clarification → optional changed-source stale approval. For the technical audience, follow with the API/state and adapter plan. Explicitly identify deterministic demo behavior and the transcription/model/EHR work still to connect.

## Evaluation and release evidence

Software checks cover family-versus-patient attribution retention, explicit clinician uncertainty, unresolved-source blocking, correction/rebuild, source/format/edit invalidation, nurse-versus-clinician section policy, empty note rejection, export scope labeling and version increments. These are curated prototype tests, not clinical-performance estimates.

Before a pilot, compare candidate model paths on authorized representative clinician-labeled encounters with held-out patient/session separation. Report unsupported assertions, diagnostic invention, certainty/negation/subject errors, required-fact omissions, audio entity errors, reviewer corrections/time, manual fallback, approved completion, cost and latency. Test the verifier's false accepts/rejects. Set release targets and stop rules with clinical/product owners before final evaluation. Zero observed failures on a finite corpus cannot prove perfect reliability.
