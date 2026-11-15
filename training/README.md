# Task adaptation and promotion gates

No clinical model fine-tuning has been performed. Current Qwen integration is a versioned prompt and exact-copy validator; the model cannot supply free-form note wording in this path. The copy task is deliberately simple and deterministic rendering is cheaper and more reliable for it. A model earns use only if it improves a harder measured task such as segmentation/structured extraction while meeting attribution/omission criteria.

MTS-Dialog train (1,201) and validation (100) files were fetched at upstream commit 3ff0801933608d6f570468c13125125fb5cabdea. The downloaded LICENSE, citation, hashes and source URLs are in ignored work/datasets/mts-dialog. Test sets were not downloaded. scripts/prepare_dataset.py preserves the original splits and emits unreviewed candidates that are ineligible for fine-tuning by default. No public data is redistributed in the hosted demo. ACI-BENCH is a second candidate for full encounters, but it was not imported. Its README warns of speaker-tag swaps.

Proposed adaptation sequence:

1. Pin task policy and source schema, normalize speaker labels without pretending uncertain labels are correct, inspect references for facts not supported by the conversation.
2. Deduplicate by source and patient/session lineage where available; preserve upstream splits; keep a clinician-reviewed holdout for final acceptance.
3. Build extraction examples with exact source spans, speaker, subject, negation, certainty, chronology and missingness. Reviewer corrections become candidates, not automatically accepted training labels.
4. Run prompt-only and deterministic baselines first; compare unsupported assertions, important omissions, attribution errors, review effort, latency and resource use.
5. If needed, train a PEFT/LoRA adapter on reviewed development examples in a separate compute environment with pinned model/tokenizer/data revisions and reproducible seeds/configuration. Do not train on test examples or tune to a final holdout score.
6. Evaluate the adapter on the same untouched splits with human review and failure slices; record license/lineage and configuration; retain the baseline and rollback artifact.
7. A clinical/product owner approves a limited pilot; promotion is never based only on ROUGE, a copy-check score, or a synthetic smoke test.

Removing pretrained knowledge from a language model is not something a prompt or adapter guarantees. The implemented defense is narrower: machine-generated rendered text must be exact authorized source content, with deterministic section labels; model-introduced words are rejected. Source transcription, speaker/subject labels, selection/omission and manual reviewer edits can still be wrong. This source-only mode makes no clinical correctness guarantee.
