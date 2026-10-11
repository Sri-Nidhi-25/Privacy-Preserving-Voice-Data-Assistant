# Phase 5.5 — Methodology

## 1. Objective

Phase 5.5 measures whether the reliability mechanisms established in Phases 4.6
and 5 remain effective when the system processes real audio through the complete
voice pipeline. It is a **measurement phase**, not a feature-development phase.

---

## 2. Pipeline Under Test

```
Real / Synthesized Audio (WAV)
        ↓
[1] Audio Validation          (app/services/voice_obfuscator.py — validate)
        ↓
[2] Voice Obfuscation         (app/services/voice_obfuscator.py — obfuscate)
        ↓
[3] Whisper STT               (app/services/stt_service.py — transcribe)
        ↓
[4] Transcript Correction     (app/services/llm_orchestrator.py — correct)
        ↓
[5] Intent Routing            (app/services/abstention_router.py — classify)
        ↓
[6] Selective Abstention      (app/services/abstention_router.py — evaluate)
        ↓
[7] Tool Selection & Args     (app/services/llm_orchestrator.py — tool call)
        ↓
[8] Connector Execution       (app/connectors/*.py)
        ↓
[9] Final Answer              (app/services/llm_orchestrator.py — response)
        ↓
[10] TTS Synthesis            (app/services/tts_service.py — synthesize)
```

The entry point under test is `POST /voice/query` (app/routers/voice.py) with
`enable_abstention` toggled between `True` (intervention) and `False`
(baseline).

---

## 3. Evaluation Modes

| Mode | `enable_abstention` | Description |
|---|---|---|
| Baseline | `False` | Uses `classify_intent()` only — Phase 4.6 behavior |
| Intervention | `True` | Uses `evaluate_abstention(τ=0.50)` — Phase 5 intervention |

Both modes are run on every case. The same synthesized audio is used for both
(STT output is cached to avoid transcription variance between modes).

---

## 4. Experimental Protocol

```
For each case in the 40-case Phase 5.5 benchmark:
  1. Synthesize audio via edge-tts (if not already cached).
  2. Validate and obfuscate audio.
  3. Transcribe once with Whisper (cache the transcript).
  4. Run orchestrator in BASELINE mode → record results.
  5. Run orchestrator in INTERVENTION mode → record results.
  6. Compute STT quality metrics (WER, CER) vs reference.
  7. Apply localize_failure() to identify responsible stage.
  8. Record per-stage latency measurements.
Aggregate:
  9. Compute summary metrics (coverage, risk, selective accuracy, FPR).
  10. Compute error propagation table across stages.
  11. Compute latency percentiles.
  12. Compute acoustic degradation table by SNR level.
```

STT caching ensures that any difference between baseline and intervention is due
solely to the abstention mechanism, not to transcription variance.

---

## 5. Fixed Parameters

| Parameter | Value | Source |
|---|---|---|
| Abstention threshold τ | 0.50 | Calibrated on Phase 5 validation data |
| Whisper model | `small.en` | Fixed since Phase 4.6 |
| LLM model | `llama3.2:latest` (Ollama) | Fixed since Phase 4.6 |
| Audio synthesis | edge-tts | Deterministic per text+voice pairing |
| Noise model | Gaussian (numpy) | `numpy.random.normal`, fixed seed `42` |
| Random seed | 42 | Reproducibility |

The abstention threshold was NOT tuned on Phase 5.5 datasets. It was set on
Phase 5 validation data and is frozen for this phase.

---

## 6. Evaluation Datasets

See `docs/phase5_5_data_protocol.md` for full dataset specification.

| Category | N cases | Description |
|---|---|---|
| A — Clean Operational | 10 | Unambiguous operational commands |
| B — Semantic Distractors | 10 | Lexical cues but no operational intent |
| C — Ambiguous | 6 | Genuinely ambiguous between operational and conversational |
| D — Linguistic Variation | 6 | Paraphrases, indirect phrasing, colloquial |
| E — Acoustic | 4 phrases × 3 SNR | Noise-degraded variants at 30/20/10 dB |
| F — Known Failure Cases | 6 | Failure modes identified in Phase 5 |
| **Total** | **40 + 12 acoustic variants** | |

---

## 7. Metrics

### Primary metrics (baseline vs intervention comparison)

| Metric | Definition |
|---|---|
| Coverage | Fraction of cases where the system executed a tool (not abstained) |
| Unsafe Execution Rate | Fraction of distractor/ambiguous cases that reached tool execution |
| Risk | Unsafe Execution Rate × fraction of distractors in the benchmark |
| Selective Accuracy | Accuracy on cases the system chose to execute (coverage ≥ 0) |
| Safe Abstention Rate | Fraction of distractor/ambiguous cases where abstention triggered |
| Distractor FPR | False positive rate: distractors incorrectly executed as operational |
| Task Success Rate | Fraction of cases that produced correct tool call + correct answer |

### Secondary metrics

| Metric | Definition |
|---|---|
| WER | Word Error Rate vs reference transcript |
| CER | Character Error Rate vs reference transcript |
| Routing Retention Rate | Fraction of clean cases where routing decision was unchanged by STT noise |
| Latency p50/p90/p95 | Per-stage and total pipeline latency percentiles (ms) |

---

## 8. Runner Scripts

| Script | Purpose |
|---|---|
| `evaluation/phase5_5/run_e2e.py` | Master E2E evaluation orchestrator |
| `evaluation/phase5_5/audio_generator.py` | Audio synthesis and noise perturbation |
| `evaluation/phase5_5/failure_localization.py` | Stage-level failure attribution |
| `evaluation/phase5_5/error_propagation.py` | Error propagation table computation |
| `evaluation/phase5_5/risk_coverage.py` | Risk/coverage metric computation |
| `evaluation/phase5_5/acoustic_eval.py` | SNR-degradation interaction analysis |
| `evaluation/phase5_5/latency_eval.py` | Latency profile computation |

---

## 9. Reproducibility

All results are reproducible with:

```bash
python -m evaluation.phase5_5.run_e2e
```

The runner serializes:
- `experiments/phase5_5/runs/run_with_abstention.jsonl` — per-case records
- `experiments/phase5_5/runs/run_baseline_no_abstention.jsonl`
- `experiments/phase5_5/results/summary.json` — aggregated metrics
- `experiments/phase5_5/failures/failures.json` — localized failure records
- `experiments/phase5_5/metadata/metadata.json` — run configuration + timestamps

Audio files are cached under `benchmark_audio/phase5_5_cache/` and are
deterministically synthesized (same text + voice → same audio).

---

## 10. Scope Boundaries

**In scope:**
- Measuring whether existing interventions survive the voice pipeline
- Measuring STT transcription quality on synthesized audio
- Measuring per-stage latency
- Classifying failures by responsible stage

**Out of scope:**
- Modifying routing behavior based on pipeline test results
- Tuning abstention threshold on Phase 5.5 datasets
- Benchmarking speaker biometric privacy
- Claiming production-grade reliability from N ≤ 40 benchmark
- Adding new reliability interventions
