# Reliability Invariants

This document specifies the core behavioral and safety invariants guaranteed by the Privacy-Preserving Voice Data Assistant pipeline.

---

## 1. Low-Confidence STT Safety
**Rule:** Transcriptions flagged by Whisper confidence heuristics (`avg_logprob < -1.0`, `no_speech_prob > 0.6`, or `compression_ratio > 2.4`) must never trigger data tools or connectors.
**Implementation:** When `stt_confidence["low_confidence"]` is true, the system abstains from calling `LLMOrchestrator.process_query()`. Instead, it provides a polite clarification prompt (`"Sorry, I didn't catch that clearly. Could you try again?"`) and sets `metadata["low_confidence_transcription"] = True`.

---

## 2. Tool Execution Safety
**Rule:** An invalid tool call must never reach a connector.
**Implementation:** Tool arguments are validated against strict JSON Schema definitions before any connector `fetch()` or `fetch_result()` call. If validation fails (due to wrong types, out-of-range bounds, or invalid enum values), the pipeline immediately returns a validation failure without executing the connector.

---

## 3. Transcript Correction Preservation
**Rule:** A failed or rejected transcript correction attempt must never overwrite or destroy the original transcript.
**Implementation:** `correct_transcript()` applies guardrails against hallucinations, length anomalies ($<40\%$ or $>200\%$ original length), and low token overlap. If the LLM call fails, times out, or fails guardrails, the raw transcript is preserved and `metadata["fallback_used"] = True` is reported.

---

## 4. Connector Failure Honesty
**Rule:** Connector failures must never be masked as successful queries or empty datasets.
**Implementation:** Connectors use `fetch_result()` returning a `ConnectorResult` structure. If database access or JSON reading fails, `success=False` and the exact error are recorded, and the orchestrator explicitly informs the user rather than claiming 0 records were found.

---

## 5. Honest Data Freshness
**Rule:** The current response generation timestamp must never be represented as the source data freshness.
**Implementation:** Responses distinguish `retrieved_at` (query execution time) from `source_last_updated` (actual underlying data modification timestamp). If data metadata lacks a valid timestamp, it is honestly labeled as `"unknown"`.

---

## 6. TTS Failure Resilience
**Rule:** Text-to-speech synthesis failures must not discard an otherwise successful text answer when text can be returned to the client.
**Implementation:** If Edge-TTS fails or times out, the pipeline logs the error, marks `metadata["tts_failed"] = True` and `metadata["fallback_used"] = True`, leaves `answer_audio_url = ""`, and returns the valid textual answer in `QueryResponse`.

---

## 7. Temporary Audio Artifact Lifecycle
**Rule:** Raw user voice uploads and intermediate processing files must be cleaned up on both successful completion and error termination.
**Implementation:** `voice_query` tracks all created temporary file paths in a `try ... finally` block. Raw user audio (`.mp3`/`.webm`) and intermediate uncompressed WAV files are deleted immediately in `finally`. Stale generated files are cleaned periodically via background tasks.

---

## 8. Request Traceability
**Rule:** Every incoming request must be assigned a unique, traceable request ID that correlates logs and response metadata.
**Implementation:** A UUID4 `request_id` is created at the start of each request and propagated across all structured log events (`log_event`), error handlers, and returned in `metadata["request_id"]`.

---

## 9. Observable Recoverable Fallbacks
**Rule:** When the system recovers from a partial failure using a fallback, the fallback must be measurable and explicitly exposed in metadata.
**Implementation:** All fallback events (e.g. `correction_attempted`, `correction_rejected`, `fallback_used`, `tts_failed`) are recorded in the response `metadata` dictionary and logged in structured JSON logs.

---

## 10. Reproducible Evaluation
**Rule:** Evaluation experiments and benchmarks must record their execution environment and configuration so results are reproducible.
**Implementation:** Benchmark scripts record `experiment_id`, ISO `timestamp`, `git_commit`, `random_seed`, `stt_model`, and `dataset_id` in output artifacts (`results.csv`).
