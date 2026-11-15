# Architecture and call guide

This is a conversation aid for explaining ClinicNote to a clinician, product leader, data scientist, or backend engineer. It describes the current prototype honestly and separates proposed production architecture from code that exists today.

## Thirty-second explanation

“I built a working prototype for turning one clinic visit into a reviewable note. The important design choice is that the model is not trusted to invent the note: the draft is assembled from explicit source statements, linked back to transcript spans, and held for clinician review. I added local speech and optional model components, version-bound approval, a job worker, and a local database so we can demonstrate the full path. It is still a development prototype: it has no verified patient registry, EHR write-back, clinical validation, or production deployment.”

## For a nontechnical listener

Think of it as a careful assistant who prepares paperwork, not a doctor who makes decisions:

1. The visit is recorded or transcribed.
2. The system organizes what each person explicitly said.
3. The note shows where each statement came from and flags unclear parts.
4. A clinician edits and approves the exact version.
5. If anything changes afterward, the old approval no longer covers it.
6. Today the demo lets the reviewer copy or download the note; it does not put it into a real medical record.

The goal is less retyping and easier review. Whether it achieves that needs a measured clinic pilot.

## Current architecture: what is implemented

### Hosted demo path

The hosted page is static. It runs the interface and deterministic example workflow in the visitor's browser, with fictional state in browser storage. It does not call the laptop, model runtime, database, a cloud model, or an EHR.

### Local connected path

The browser calls a FastAPI process bound to `127.0.0.1`. That API manages a local demo session, validates requests, applies tenant/role checks, stores records in SQLite, and creates durable processing jobs. A local worker claims a job, invokes faster-whisper for speech recognition, and sends the transcript to a deterministic renderer. An optional Qwen step can check whether candidate text is copied exactly from source spans; deterministic code checks the result. Speakers remain Unknown until a person confirms them.

The API gates approval and export using the current source version, draft revision, reviewer state, and role. It supports copy/download, not an external clinical-system write.

### Current storage shape

SQLite holds tenant-scoped encounter bodies, processing jobs, append-only event metadata, separate context records and immutable transcript source versions. The current encounter body stores the active draft and immediate previous draft. There is no canonical patient registry, full note-version archive, or live clinical-history import.

## Main engineering decisions

| Decision | Why this prototype uses it | Cost / next check |
| --- | --- | --- |
| Deterministic source renderer first | Keeps the draft inspectable and reduces unnecessary model generation | Less natural prose; compare against clinician-approved examples |
| Optional local Qwen exact-copy audit | Experiments with local inference while constraining the model's job | Adds latency and still cannot validate meaning or truth |
| faster-whisper local transcription | Makes audio-to-text demonstrable without an external transcription service | Speaker identity is unresolved; accuracy is not clinically benchmarked |
| SQLite for local development | Easy to inspect and run on one laptop | Not the proposed multi-user production database |
| Separate source versions and exact-version approval | Makes corrections and stale review visible | Full note history and identity workflow still need design |
| Durable job rows, lease, bounded attempts and idempotency key | Supports restart/retry behavior in the local prototype | Requires load/failure testing and a managed queue at production scale |
| No tools or write-capable model access | Limits the model to its narrow, auditable check | Future integrations need explicit server-side authorization and review |
| Browser static deployment for the remote demo | Phone-accessible product walkthrough without exposing the laptop API | No shared server-side data or real account workflow |

## Planned system, if the team chooses this direction

1. **Clinic entry point:** use the clinic's established identity and launch workflow. Resolve patient and encounter identifiers from an approved source.
2. **Application API:** authorize every request, enforce tenant boundaries, validate versions, and expose a small versioned contract.
3. **Durable processing:** enqueue audio/transcript work with idempotency, retries, timeouts, cancellation and observable states.
4. **Source processing:** speech recognition produces timestamped text; human confirmation establishes speaker roles; note extraction cites source spans.
5. **Review state machine:** show omissions, uncertain attribution, conflicts and manual edits. Approval is tied to the exact source and note version.
6. **Data layer:** PostgreSQL for normalized patient/encounter/version state; encrypted private object storage only if audio retention is required; append-only audit records.
7. **Workspace adapter:** perform a scoped, versioned write to the actual clinic system and confirm its result. Never treat a mock UI or HTTP success alone as proof of a saved note.
8. **Evaluation and operations:** measure quality slices, cost, latency, failures and reviewer corrections; set stop rules; validate access, restore, deletion and rollback.

These are design proposals. We have not selected the clinic's identity provider, EHR, cloud, model vendor, retention policy, queue technology, or regulated product scope.

## Data flow and guardrails

| Stage | Input | Output | What must not be inferred silently |
| --- | --- | --- | --- |
| Audio transcription | Visit audio | Timestamped words and uncertain segments | Speaker's identity or clinical role |
| Source correction | Transcript and audio | Confirmed transcript version | Missing or inaudible words |
| Note drafting | Confirmed source | Sectioned note with evidence references | Diagnosis, intent, or plan absent from source |
| History retrieval (future) | Verified patient + permission + purpose | Dated, attributed prior facts | That old information is true/current or belongs to today's visit |
| Review | Current source, draft, flags | Human edits and version-specific approval | That a checklist proves medical safety |
| Export (future integration) | Approved exact version + destination | Confirmed external write result | That network acceptance means chart update succeeded |

## Interview version: how I would improve the poor output

Start with the examples that users rejected. Ask what “diagnosing” means in observable terms: a new diagnosis appeared, a clinician's uncertainty became certainty, a patient report became a finding, a differential became a final assessment, or the model filled an undocumented section. Label those error types with clinicians before changing prompts or choosing another model.

Then set up a source-preserving baseline. Separate what the patient reports, what staff observe, and what the clinician explicitly assesses. Keep negation, time, speaker, certainty, and provenance. Leave unsupported sections blank and show an explicit clarification request. Do not solve this by deleting all assessment language: faithfully preserve a clinician-authored assessment while preventing model-authored additions.

Evaluate on held-out, consented/de-identified examples with an agreed reviewer rubric. Track unsupported assertion rate and severity, omission rate, attribution/certainty errors, transcription errors, human correction time, accepted-note completion, failure rate, latency, and cost. Review slices such as specialty, accent, noise, medication/number mentions, negation, overlap, and tentative language. A model-based verifier may help, but it needs its own false-accept/false-reject evaluation. No average score should hide a dangerous failure slice.

Roll out in shadow mode, compare against the existing workflow, then pilot with explicit review and a manual fallback. Keep a release stop condition for clinically consequential unsupported statements. Do not promise a “perfect” note; the target is a measurable, bounded workflow with clear responsibility.

## Likely backend engineer questions

### “Why have a queue and worker?”

Transcription and model work can outlast a normal request. A job record lets the UI show progress and lets the worker retry or recover after interruption. At production scale I would use a managed durable queue when its semantics fit, make job handlers idempotent, bound attempts and timeouts, and send exhausted failures to an operator-visible recovery path. Current queueing is database-backed and local.

### “How do you prevent duplicate processing?”

Give a logical operation a stable idempotency key and persist its fingerprint and status. A repeated request with the same key and same input returns the existing operation; the same key with different input is rejected. Workers claim jobs transactionally with a lease. The external side effect also needs an idempotency strategy; a database key alone cannot guarantee exactly-once behavior across a third-party EHR.

### “What happens when the source changes while a job runs?”

The job records the source version it was created from. Before publishing its output, the server checks that the encounter is still on that version and that the job was not canceled. If the source is newer, the old result becomes stale and must not replace the newer draft.

### “Why SQLite now and PostgreSQL later?”

SQLite keeps local setup small and supports the current single-laptop demonstration. A shared production service needs concurrent multi-user access, managed backup/restore, operational visibility, and explicit tenant and row-level authorization. PostgreSQL is a candidate for that transactional data, but choice depends on the actual deployment and security requirements.

### “How would you scale the services?”

First measure the workload and bottleneck; then separate latency-sensitive API work from bounded background inference. Scale API and worker pools independently, control concurrency against model capacity, use private object storage for large files if retention is justified, cache only safe/non-sensitive artifacts, and add admission limits and backpressure. A queue is not proof of scale; we need measured throughput, p95 latency, failure recovery, and cost under a representative workload.

### “How do you handle security?”

Use established identity, least privilege, tenant-scoped authorization on each operation, private transport and storage, managed secrets, minimum retention, audit logging, access review, deletion/backup procedures and incident response. Test cross-tenant access and expired/revoked grants. Current local checks are prototype controls, not an enterprise security certification.

### “Why not send everything to an agent?”

The core task is bounded and high consequence. A general agent with broad chart, messaging, and ordering tools adds a large permission and failure surface. Start with the narrowest deterministic workflow, give each future capability a specific contract and authorization, and require human review before consequential external writes.

## Likely data scientist / product leader questions

### “How do you define success?”

An acceptable, complete note with low unsupported-content risk and reasonable review effort. Measure acceptance and correction time together with unsupported statements, consequential omissions, attribution/certainty errors, transcription errors, failures, latency and cost. Define denominators and severity before looking at results.

### “How do you avoid leakage?”

Split by patient/session lineage and source provenance so near-duplicate notes or recordings do not cross train and holdout. Freeze a final set, track every prompt/model/rubric version, and do not tune on the holdout after reading its failures.

### “Would you fine-tune?”

Only after defining a stable task, obtaining examples that can be used lawfully, and establishing a reviewer-labeled baseline. Compare fine-tuning against deterministic extraction and prompting on held-out examples. Fine-tuning may improve consistent extraction or style; it cannot resolve identity, permission, missing evidence, or a bad workflow.

### “What is your X-factor?”

Right now, the defensible product thesis is **reviewable continuity**: preserve source and speaker context in today's visit, then add authorized, dated prior context without confusing it with a new finding. That is a design hypothesis—not a proven moat. The evidence would be fewer corrections, clearer provenance, faster review, and fewer unsafe cross-visit carryovers in a measured pilot.

### “How would you pitch the business value?”

“Let's start with one workflow and measure whether it helps your staff produce an acceptable note with less rework. We will compare it with today's process, inspect errors together, and keep the existing manual path. We should agree on the time, quality, and operational targets before expanding.”

## Five-minute walkthrough

1. **Set expectations:** “This uses fictional data. I'll show the prototype workflow, then separate current functionality from production ideas.”
2. **Open an encounter:** explain patient identity is not yet a canonical linked registry.
3. **Show source and draft:** select one explicit source statement and trace it to the note. Point out an unknown speaker or blank section.
4. **Correct and approve:** change a draft field, approve the exact revision, then show a source edit makes the old approval stale.
5. **Show the boundary:** copy/download is implemented; EHR write-back is not. Show the architecture map as the proposed integration path.
6. **Close with a question:** “Which rejected output or workflow step would be most valuable to measure first with your team?”

## Phrases that keep the explanation accurate

- Say **“local development prototype”**, not “production healthcare platform.”
- Say **“version-bound approval gate”**, not “clinically safe by design.”
- Say **“source-linked draft”**, not “hallucination-free.”
- Say **“future EHR adapter”**, not “integrates with the EHR.”
- Say **“we need representative, reviewer-labeled examples”**, not “the model has been tuned for the clinic.”
- Say **“candidate production architecture”**, not “deployed microservices.”
- Give the measured synthetic/local results only with their sample sizes and limits from `docs/VERIFICATION_V2.md`.
