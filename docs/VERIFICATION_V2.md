# v2 verification — November 15, 2026

## Automated software checks

- 12 Python backend tests pass: unauthenticated/role and tenant boundaries, rejected cross-origin writes, durable job stages, exact-version reviewer approval/export, stale source/revision conflicts, idempotency identity, unknown/unclear passages, append-only audit/source constraints, expired-lease recovery, job cancellation, source-history isolation, model failure preventing publication, clerical task persistence and strict model quote rejection.
- 12 JavaScript core tests pass. Earlier deterministic renderer/version/export behavior remains covered. These are curated software checks, not clinical accuracy or exhaustive security results.
- Frontend JavaScript syntax and backend Python compilation checks passed.

## Actual local model/speech calls

The installed Qwen3.5 4B ran through the isolated loopback Ollama service with normal Mac GPU access. Initial sandbox access failed and was not counted as a model result. Four synthetic source-copy development cases initially passed 3/4; strict quote validation rejected the numbers/correction case. After removing duplicate input fields, those same four development cases passed 4/4, taking about 1.7–5.4 seconds per case. Reusing development cases is not an independent evaluation, not fine-tuning, not medical validation and not evidence of clinical completeness. Raw metadata is in ignored work/local-model-evaluation*.json.

A built-in system TTS voice produced one 5.4-second synthetic audio fixture. tiny.en transcribed “cause” as “calls.” small.en transcribed that sentence as supplied. With weights cached, two sequential small.en CPU-int8 runs measured 3001ms and 1915ms, returning timestamped segments with Unknown speakers. This is one synthetic clip, not representative clinical WER or latency under load. The first attempted sandboxed TTS output had no audio frames and was not treated as successful speech evidence. PyAV 19 caused an adapter incompatibility; av 15.1.0 was pinned before successful decoding/transcription. Empty speech results are now rejected.

## Public-data preparation

Downloaded MTS-Dialog training (1201) and validation (100) records from an immutable upstream commit, with license/citation/hash manifest. Prepared split-preserving unreviewed candidates; no training was run and no test data was downloaded. Dataset text/model weights/runtime data are ignored by Git and excluded from the hosted build. ACI-BENCH was researched, not downloaded or used for tuning.

## Browser flow checks

Observed local API bootstrap, persistent encounter list and actual durable source-to-draft job events; server-authorized version approval; context timeline kept separate from note input; clerical task persisted across reload. The existing v1 tests also exercised source corrections, edits invalidating approval, blocked export, new encounters and downloaded export contents. v2 adds a redesigned navy/coral workspace, bundled Poppins fonts and explicit mode labels. Final phone/layout and model-UI observations are recorded below after verification.

## Deliberate unverified work

No production identity provider, Navierre/EHR connection, clinical consent integration, real patient inputs, clinical study, distributed load test, cloud model deployment, real-user concurrency study, or trained LoRA adapter. Docker/Compose scaffolds were not built or run. Local inference is not exposed by the hosted Site. sqlite append-only triggers are not administrator-resistant tamper proofing. No frontier-model parity claim is made.


Bounded local-helper delegation: task f81b133b3119435e977039224f2f96b1 extracted two exact quotations from the pinned public license/citation excerpt. Main-agent review accepted only quotation integrity, not completeness or legal interpretation. Measured 401 input and 61 output tokens locally, 7.79 seconds; no hosted-token savings claim.

Browser v2: actual Qwen-backed job succeeded in the connected UI. Stored metadata recorded prompt quote-only-v2-minimal-source, exact-copy mode, 10,654ms, 241 input tokens and 124 output tokens for that encounter. A separate real HTTP audio request returned three timestamped small.en segments and speaker_confirmation_required=true. Phone view with 390px client and scroll width showed no horizontal page overflow; separate context records and source boundaries were visually inspected.

Final standalone-mode browser check: local hosted-preview mode avoided backend requests, showed no console errors, created an administrative task and displayed separate historical records. All five mobile tabs measured 71px wide inside a 390px viewport; page client and scroll widths both 390px. Temporary viewport reset. Native model API sessions and datasets are not exposed by static publication.
