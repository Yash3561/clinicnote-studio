# ClinicNote connected-workspace v2 — models, data and deployment

Independent development prototype, November 15, 2026. This document replaces the v1 browser-only scope description where they differ. It is not a claim that Navierre uses this architecture or that clinical/production readiness is achieved.

## What is running and where

The owner-private Sites URL is a responsive synthetic product preview. It includes notes, a dated patient-context timeline, clerical tasks, evidence, review and export. It uses device-local demo data and does not call the laptop's model service. No tunnel or model endpoint was exposed to the internet.

On the laptop, `scripts/serve-local.sh` serves the same UI and a working FastAPI backend at http://127.0.0.1:8784/. It provides SQLite persistence, an actual durable job/state loop, server-side authorization and optimistic concurrency, source snapshots, exact-version approval/export checks, read-only source access, context and clerical-task APIs, append-only event/source constraints, cancellation, lease recovery and limited retries. Model/speech paths run locally from this service. SQLite and the loopback demo-session bootstrap are development infrastructure, not enterprise multi-user identity or a distributed production database.

No system can be made “scale-proof” or “future-proof.” The implemented boundaries make evolution testable; deployment capacity, clinical quality, security and integration still need evidence.

## Model choices and observed checks

| Component | Current choice | Reason and observed result | Limits |
| --- | --- | --- | --- |
| Note wording | Deterministic exact-source renderer | Cheapest and most inspectable baseline. The application does not accept model-supplied medical prose in this path. | Source/transcription/speaker errors and omissions can remain. Reviewer edits are human-authored and need review. |
| Optional model audit | Installed Qwen3.5 4B, local Ollama | Apache 2.0 model; fixed operator-owned endpoint, temperature 0, bounded context/output/time, versioned prompt. Checks exact source quotes and rejects missing/unknown/altered fields. | First four synthetic copy cases: 3 passed and the number/correction case was rejected. After reducing duplicated input fields, the same four development cases passed 4/4; this is prompt/input-format adaptation, not an independent holdout. This is a deliberately tiny development check, not medical validation. No fine-tuning occurred. The model is not required for the renderer and has not earned default use. |
| Speech | faster-whisper, CPU int8; small.en development default | Same synthetic 5.4-second spoken fixture: tiny.en misheard “cause” as “calls”; small.en preserved that sentence. Two cached-weight small.en runs measured 3001ms and 1915ms, including adapter work. | Single system-TTS clip; no clinical audio, diarization or general WER/clinical accuracy claim. Every returned segment has Unknown speaker until the user confirms roles. |
| Model training | No trained adapter yet | Public data is staged with pinned provenance and original split information; unreviewed candidate records are ineligible for training by default. | A model trained without a task policy/held-out review could simply learn fluent unsupported notes. See training/README.md. |

Qwen model card: https://huggingface.co/Qwen/Qwen3.5-4B . Runtime documentation: https://docs.ollama.com/api/chat . Speech implementation/license and benchmark caveats: https://github.com/SYSTRAN/faster-whisper . Benchmarks published by those projects are not measurements of our app. We did not run large-model comparisons or establish an optimal production model.

The initial sandboxed model process could not access Metal. The existing loopback runtime was then run with GPU access; local smoke results use that working process. No paid model API was invoked. A PyAV compatibility failure was found and `av==15.1.0` pinned before the successful speech checks. See requirements-lock.txt for the resolved environment.

## What “no extra knowledge” means in this implementation

Pretrained knowledge cannot be guaranteed absent from a language model's behavior. The implemented guarantee is narrower and mechanical: model-generated quote text must match an authorized input span exactly, all supplied spans must be accounted for, and only span_id/quote fields are accepted. Novel text, altered numbers, omitted spans and unknown source references are rejected. The final note is rendered from source content and fixed section labels. The model has no tool, database-write, diagnosis, prescribing or export authority.

Attribution, subject, negation, uncertainty and the correctness of the original source remain fallible. Speaker labels supplied by a transcript/user are not proof of identity. The renderer only places explicitly labeled clinician Assessment/Plan statements in those sections; it never fills missing findings with medical plausibility. Exact quotation does not establish medical truth. Human edits are marked manual and invalidate approval rather than falsely certified as source-extracted.

For a future paraphrasing model, these exact-copy guarantees would no longer suffice: per-claim semantic support, omission evaluation, number/unit/correction checks, representative clinical review and new release gates would be required. More agents or an LLM judge alone do not provide that guarantee.

## Public data available now

**MTS-Dialog:** downloaded 1,201 training and 100 validation pairs from the authors' repository at commit `3ff0801933608d6f570468c13125125fb5cabdea`. The repository states CC BY 4.0. Exact source URLs, byte hashes, license, citation and split manifest are in ignored work/datasets/mts-dialog. Test sets were not downloaded. `scripts/prepare_dataset.py` stages candidates with original split/source IDs and review flags; it performs no fine-tuning. Do not blindly treat a reference note as evidence that every detail was spoken. Source: https://github.com/abachaa/MTS-Dialog . Citation: Ben Abacha, Yim, Fan & Lin, EACL 2023, https://aclanthology.org/2023.eacl-main.168 .

**ACI-BENCH:** a candidate full-encounter benchmark, not imported or used for tuning here. The authors state CC BY 4.0 and specifically document swapped speaker tags in some transcripts. Source: https://github.com/wyim/aci-bench . Data-quality and split checks are essential before use.

Neither dataset defines Navierre's clinician preferences or validates this product for their patients. Publicly released benchmark data may already have appeared in foundation-model training. Keep a new clinician-reviewed held-out set for consequential product evaluation; report that contamination risk when interpreting public benchmark results. No dataset records were copied into the hosted pitch demo.

## Task customization and training plan

The implemented adaptation is source schema + explicit documentation policy + a constrained, versioned model interface + code-enforced acceptance. Before training: identify failure categories with clinicians, inspect public examples, preserve attribution and missingness, deduplicate and preserve lineage, and establish metrics and untouched splits. Build real source-span labels, not only free-form target summaries. Stage reviewer corrections for review rather than automatically learning from every edit.

Compare deterministic and prompt-only baselines before considering PEFT/LoRA. A trained adapter needs versioned base model/tokenizer/config/data, reproducibility, independent evaluation and a rollback artifact. Evaluate unsupported assertions, required-fact omissions, role/subject/certainty errors, number/unit errors, clinician review burden, completion, latency and cost. Fine-tuning is a candidate experiment, not a claim already made by this build. An open medical-QA model is not automatically suited to faithful documentation; its medical fluency can increase unwanted inference.

## Compatible with a longitudinal healthcare workspace

Navierre publicly describes Eterna as a connected health picture with physician review: https://www.navierre.com/eterna . That motivates a patient-context boundary, not a claim about their private schema or EHR.

Current implementation separates background records by patient/tenant with dated source IDs and status. Those records are displayed separately and are never silently supplied to the current-note renderer/model. The renderer's only input is the current encounter transcript. Context APIs and note/export permission checks are server-side in local mode. A context record can be Historical, Unverified or Metadata only rather than implicitly current fact.

Future adapter contract: trusted tenant/subject/encounter context, allowed purpose, consent/access revision, source versions, temporal context, lineage and revocation event. Do not accept tenant authority from a browser JSON field. A note may use a selected historical source only after the workflow expressly permits it, records the dependency and distinguishes historical facts from today's findings. Withdrawal/source changes must invalidate derived artifacts and cached retrieval; exports require a current authorization check. This full consent/revocation integration is not implemented here.

Keep member-authorized clinical context separate from insurance claims and de-identified portfolio reporting. A shared umbrella app does not justify making every data source available to every module or agent.

## Service boundaries and scaling sequence

Implemented as modules in one local API plus bounded background work: encounter/source service; job service; source-only drafting/model adapter; review/export service; context read service; clerical-task service; audit metadata. One local model request is processed per worker cycle, with source/output/time bounds. The UI reports actual job events and never fabricates a clinical quality score. Cancellation prevents a canceled result from publishing, even if the in-flight model request finishes later.

This is intentionally not many independently deployed microservices. Splitting before measured load/integration requirements adds queues, consistency and operational overhead without proving value. Next deployment stages:

1. Integrate the existing host's identity and encounter launch; real users/roles, scoped grants and patient matching. The current loopback cookie is not enterprise SSO.
2. Migrate transactional state to managed PostgreSQL with reviewed migrations, scoped authorization and operational credentials. SQLite WAL serializes writes and is not our horizontal-scaling claim.
3. Move approved audio to private object storage with lifecycle policy, signed URLs and deletion propagation; the current transcription endpoint processes bounded bytes and does not build a production recording archive.
4. Use a durable queue/outbox and separate STT/model workers when measured volume requires it; idempotent effects, leases, concurrency limits, backpressure, dead-letter/recovery and budget limits remain explicit.
5. Deploy model inference as a private service with a pinned artifact/adapter, measured batching/quantization and resource budgets. A copied model card context limit is not the chosen serving configuration.
6. Add actual observability, alerts, backup/restore drills, controlled rollout, security/clinical review and a measured load test. Record throughput, error rates, queue age, p50/p95, inference resources and total cost under a defined workload.
7. Implement and verify the host/EHR adapter in their sandbox, including versioned write-back, conflict handling, external request reconciliation and no duplicate export. No “sent to EHR” success state exists in this demo.

Dockerfile and compose.yaml are development scaffolds, not built/run/production-validated in this session. The app port is published only on 127.0.0.1; the Docker model service has no published port. Pull the selected model explicitly. Native Ollama on this Mac uses the existing isolated local runtime at 127.0.0.1:11435. No public access to it was added.

## State, provenance and failure controls

Append-only SQLite constraints protect audit events and immutable transcript snapshots against application-level updates/deletes. They are not tamper-proof against a database administrator. Expected revisions protect concurrent saves/reviews. Approval is bound to draft/source/revision, and the server re-checks eligibility before export. Jobs have a unique operation key/fingerprint, bounded attempts and a lease; canceled or stale jobs cannot publish a new result. Cross-tenant access, unknown source speakers, unclear passages, empty notes, changed inputs and model-copy failures are exercised by tests.

Local endpoint authorization is a development boundary. There is no production threat assessment, real patient-data approval, formal clinical validation, external audit, complete deletion system, patient consent workflow or regulatory determination. Do not use real patient records in either runtime.

## Running the local version

1. From the repo: create .venv with Python 3.12 and install requirements-lock.txt using uv or pip.
2. Start the existing isolated Ollama runtime only if testing Qwen: `../local-assistant/runtime.sh serve` from projects/clinicnote-studio, or its absolute path. On macOS it needs normal GPU access; no public listener is needed.
3. Run `scripts/serve-local.sh`, then open http://127.0.0.1:8784/ . The page bootstraps a local demo session and seeds fictional encounters. This is a laptop URL, not a phone/cloud model endpoint.
4. Default drafting uses the exact-source renderer. The optional Qwen audit can be selected after an initial draft; a failed audit does not publish unverified replacement content.
5. Audio capture/upload offers Transcribe locally in connected mode. small.en may need a one-time model download. All resulting speakers start Unknown and require confirmation.
6. Run `node --test tests/core.test.mjs` and `.venv/bin/python -m pytest -q`. Model/speech smoke scripts and data preparation are separate; don't confuse a structural test with a medical benchmark.

## Visual design and pitch

Public-site inspection found a navy/white/coral palette and Poppins typography. v2 uses those cues with an independent ClinicNote identity, bundled open-font files and their OFL license; no Navierre logo, endorsement or official-app claim is used. The product now places encounter notes, separate background records, clerical tasks and service boundaries in one workspace. Loaders show real processing stages rather than invented progress percentages. The phone preview keeps these workflows available without exposing laptop services.

Pitch the reviewable result: an attributed draft, accessible source, visible missingness, version-bound approval and a clear handoff. Demonstrate one unsupported or unclear case stopping rather than hide it. Show the local API/model path only when it is actually connected; the hosted preview does not pretend to run it. Any claim of time savings, clinical quality or readiness needs the relevant measured pilot.
