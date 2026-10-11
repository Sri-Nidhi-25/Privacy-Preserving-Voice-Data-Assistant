# Phase 5.5 Implementation Plan: End-to-End Voice Reliability Validation

Validate whether the reliability mechanisms developed through Phases 4.6 and 5 survive the complete real-world voice pipeline:
$$\text{Microphone Audio} \to \text{Audio Validation} \to \text{Voice Obfuscation} \to \text{Whisper STT} \to \text{Correction} \to \text{Routing} \to \text{Abstention} \to \text{Tool Selection} \to \text{Arguments} \to \text{Connector} \to \text{Answer} \to \text{TTS}$$

---

## 1. System Audit & Pipeline Integration (Backend)

1. **Integrate Phase 5 Abstention into `LLMOrchestrator`**:
   - In `app/services/llm_orchestrator.py`:
     - Update `process_query(user_text, enable_abstention=True)`.
     - After transcript correction, invoke `evaluate_abstention(corrected_text, threshold=0.50)` from `app.services.abstention_router`.
     - When `decision == Decision.ABSTAIN`: safely withhold tool invocation, return safe conversational explanation, and mark `execution_prevented_by_abstention = True`.
     - When `decision == Decision.DIRECT`: route directly to LLM without tools.
     - When `decision == Decision.EXECUTE`: authorize tool calling / tool execution.
     - Maintain backward compatibility with Phase 4.6 baseline when `enable_abstention=False`.
2. **Instrument Stage Latencies & Metadata in `app/routers/voice.py`**:
   - Expose detailed telemetry in `QueryResponse.metadata`:
     - `stt_latency_ms`, `correction_latency_ms`, `routing_latency_ms`, `abstention_latency_ms`, `tool_latency_ms`, `tts_latency_ms`, `total_latency_ms`.
     - `abstention_decision`, `abstention_reason`, `abstention_confidence`, `execution_prevented_by_abstention`.
     - Support optional query parameter `enable_abstention: bool = True` in `POST /voice/query`.

---

## 2. Minimal E2E Test Interface (Frontend)

1. **Enhance `voice_chat.html`**:
   - Add microphone recording with duration timer, Start/Stop toggle, and audio waveform/level indicator.
   - Add direct audio file upload (`.wav`, `.mp3`, `.webm`, `.ogg`) for reproducible testing.
   - Add recorded audio playback before/after submission.
   - Add "Enable Selective Abstention" toggle for side-by-side testing.
   - Add interactive pipeline stage progress indicator:
     $$\text{Recording} \to \text{Validation} \to \text{Obfuscation} \to \text{Transcription} \to \text{Correction} \to \text{Routing} \to \text{Abstention} \to \text{Tool Execution} \to \text{Response} \to \text{TTS}$$
   - Add rich turn inspector:
     - Raw vs Corrected Transcript (highlighting diffs).
     - Intent Classification & Abstention Decision badge (`EXECUTE` / `ABSTAIN` / `DIRECT`) + Reason.
     - Selected Tool & Parsed Arguments.
     - Connector Result & Freshness.
     - Final Text Answer + Audio Playback.
     - Telemetry breakdown: Request ID, per-stage latencies, failure code if any.

---

## 3. E2E Voice Dataset Protocol (`evaluation/datasets/phase5_5/`)

Create 40 diverse voice evaluation test cases across the 6 required categories:
- `clean/` (Category A: Normal Operational Requests, $N = 10$)
- `semantic_distractors/` (Category B: Semantic Distractors, $N = 10$)
- `ambiguous/` (Category C: Ambiguous Requests, $N = 6$)
- `linguistic_variation/` (Category D: Polite phrasing, fillers, disfluency, $N = 6$)
- `acoustic/` (Category E: Evaluated across Clean, 20 dB, 10 dB noise, $N = 4 \times 3$)
- `failure_cases/` (Category F: Fault injection, connector failure, malformed args, invalid audio, $N = 4$)

Every dataset record defines:
- `case_id`, `category`, `input_text`, `expected_route`, `expected_action`, `expected_tool`, `expected_args`, `acoustic_condition`, `notes`.

---

## 4. Evaluation Suite & Error Propagation Engine (`evaluation/phase5_5/`)

Build the modular evaluation scripts:
1. `evaluation/phase5_5/audio_generator.py`: Generates real speech audio using neural TTS and acoustic perturbation (additive noise at 20 dB and 10 dB).
2. `evaluation/phase5_5/run_e2e.py`: Master orchestrator running the complete voice pipeline for all cases.
3. `evaluation/phase5_5/failure_localization.py`: Stage-level attribution (`STT`, `CORRECTION`, `ROUTING`, `ABSTENTION`, `TOOL_SELECTION`, `ARGUMENT_VALIDATION`, `CONNECTOR`, `TTS`, `SYSTEM`).
4. `evaluation/phase5_5/error_propagation.py`: Calculates error entry, error generation, containment, and unsafe execution across pipeline stages.
5. `evaluation/phase5_5/risk_coverage.py`: E2E selective prediction metrics (Coverage, Risk, Selective Accuracy, AURC).
6. `evaluation/phase5_5/acoustic_eval.py`: Acoustic SNR interaction with WER and downstream routing.
7. `evaluation/phase5_5/latency_eval.py`: Measures p50, p90, p95 latencies across all pipeline stages.

---

## 5. Experiment Execution & Serialization (`experiments/phase5_5/`)

Run and serialize:
- `experiments/phase5_5/runs/`: Per-case execution JSON records.
- `experiments/phase5_5/results/`: Aggregate summary metrics (Baseline vs Abstention).
- `experiments/phase5_5/failures/`: Localized failure cases with stage attribution.
- `experiments/phase5_5/metadata/`: Reproducibility hashes, models, timestamp, parameters.

---

## 6. Test Suite (`tests/test_phase5_5/`)

Create automated tests:
1. `test_pipeline_integration.py`: Audio validation, obfuscation, STT, correction, abstention, tool execution.
2. `test_abstention_e2e.py`: Verifies that abstained audio queries do not execute backend tools.
3. `test_failure_localization.py`: Validates stage attribution and error propagation calculation.
4. Verify all Phase 4.6 and Phase 5 tests continue to pass (100% regression pass).

---

## 7. Documentation Deliverables

Author all 6 required documentation artifacts:
1. `docs/phase5_5_research_questions.md`: Formulation of RQ1 through RQ8.
2. `docs/phase5_5_methodology.md`: Complete theoretical and mathematical framework.
3. `docs/phase5_5_data_protocol.md`: Dataset taxonomy and schema specifications.
4. `docs/phase5_5_failure_analysis.md`: Detailed stage-level failure localization and error propagation analysis.
5. `docs/phase5_5_results.md`: Complete empirical results answering all research questions.
6. `docs/phase5_5_claim_audit.md`: Formal verification of supported, partially supported, and unsupported claims.

---

## Verification Plan

### Automated Tests
- Run `pytest tests/test_phase5_5/ -v`
- Run regression tests: `pytest tests/test_phase4_6/ -q` and `pytest tests/test_phase5/ -q`
- Run full test suite: `pytest tests/ -q`

### End-to-End Execution
- Execute `evaluation/phase5_5/run_e2e.py`
- Validate generated results in `experiments/phase5_5/`
