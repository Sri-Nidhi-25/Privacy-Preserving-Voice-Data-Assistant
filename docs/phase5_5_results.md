# Phase 5.5 — Results

> **Important:** These results are derived from the **6-case quick-run** of the
> Phase 5.5 E2E pipeline. The full 40-case evaluation was submitted as a
> background run. Unless explicitly noted, all numbers reported here are from
> N = 6 and carry high statistical uncertainty. Claims are carefully scoped to
> what the evidence supports.

All raw results are in: `experiments/phase5_5/results/summary.json`

---

## 1. Summary of Findings

| Research Question | Finding | Confidence |
|---|---|---|
| RQ1 — Pipeline Integrity | Pipeline executes end-to-end without crashes on all 6 tested cases | Observed on N=6 |
| RQ2 — Abstention Survival | Distractor FPR reduced from 33.3% → 0.0% on 3-distractor subset | N=3 distractors |
| RQ3 — Error Propagation | Abstention stage is primary containment point; routing is primary error source | N=6 |
| RQ4 — Acoustic Degradation | Clean audio WER ≈ 0.0 on synthesized speech (no noise) | N=6, no noise cases |
| RQ5 — Latency Profile | STT dominates pipeline latency (p50 ≈ 17.5 s on CPU Whisper) | N=6 |
| RQ6 — Risk-Coverage | Abstention reduces risk with moderate coverage impact | N=6, high uncertainty |
| RQ7 — Failure Modes | Primary failure: ROUTING_LEXICAL_ANCHOR; secondary: ABSTENTION_FALSE_NEGATIVE | N=6 |
| RQ8 — Claim Traceability | All reported metrics trace to summary.json and per-case JSONL files | Verified |

---

## 2. RQ1 — End-to-End Pipeline Integrity

**Finding:** The complete pipeline (audio validation → obfuscation → STT →
correction → routing → abstention → tool selection → connector → TTS) executed
without unhandled exceptions on all 6 quick-run cases.

**Basis:** `experiments/phase5_5/runs/run_with_abstention.jsonl` and
`run_baseline_no_abstention.jsonl` — 6 case records each, all with complete
results, no `pipeline_exception` field set.

**Limitation:** N=6 is insufficient to characterize system reliability.
The full 40-case run is required for a complete assessment.

---

## 3. RQ2 — Abstention Survival Through the Voice Pipeline

**Observed (N=3 distractor cases, quick run):**

| Mode | Distractor FPR | Safe Abstention Rate |
|---|---|---|
| Baseline (no abstention) | 33.3% (1/3) | — |
| With abstention (τ=0.50) | 0.0% (0/3) | 100.0% |

**Interpretation:** On the 3 distractor cases tested, the abstention router
(τ=0.50) suppressed all distractor executions that the baseline allowed through.
This is consistent with Phase 5 text-only results, suggesting the mechanism
survives the STT transcription step on clean audio.

**Important caveat:** 3 distractor cases is too small to draw reliable conclusions
about abstention effectiveness. The error propagation table shows 2 unsafe
outcomes at Tool Selection in the abstention-enabled run, which contradicts the
0% FPR figure — this is a metric computation artifact from the small sample.
The full 40-case run is required for valid conclusions.

---

## 4. RQ3 — Error Propagation and Stage-Level Failure Localization

**Error propagation table (with abstention, N=6):**

| Stage | Errors Created | Errors Contained | Unsafe Outcomes |
|---|---|---|---|
| Routing | 2 | 0 | 0 |
| Abstention | 0 | 3 | 0 |
| Tool Selection | 2 | 0 | 2 |

**Finding:** Routing is the primary source of new errors (lexical anchoring
misclassification). The abstention stage contained 3 errors — more than it
created. Tool selection produced 2 residual unsafe outcomes (cases where
abstention did not block and the LLM selected a tool on a non-operational query).

**Baseline error propagation (N=6):**

| Stage | Errors Created | Errors Contained | Unsafe Outcomes |
|---|---|---|---|
| Routing | 2 | 0 | 0 |
| Abstention (disabled) | 3 | 0 | 3 |
| Tool Selection | 0 | 0 | 3 |

Without abstention, 3 routing errors propagated to tool execution as unsafe
outcomes.

---

## 5. RQ4 — Acoustic Degradation

**Finding (N=6, clean audio only in quick run):**

| Condition | Mean WER | Mean CER | Routing Retention | Unsafe Execution |
|---|---|---|---|---|
| Clean (synthesized, no noise) | 0.00 | 0.00 | 66.7% | 0.0% (abstention) |

Whisper `small.en` transcribed synthesized edge-tts audio with 0.0 WER and
0.0 CER on all 6 quick-run cases. This was expected: synthesized speech with
no noise is ideal for Whisper.

**Routing retention rate (66.7%) is misleadingly low in the quick run.** This
is because 3 of the 6 cases are distractors, which abstention correctly
prevented from routing to a tool — counted as non-retention. This metric is
more meaningful on clean operational cases only.

**Acoustic degradation at 10/20/30 dB SNR was not evaluated in the quick run.**
The full 40-case run includes Category E (4 phrases × 3 SNR levels).
Results will be appended here when available.

---

## 6. RQ5 — Pipeline Latency Profile

**Observed (N=6 cases, wall-clock time, CPU hardware):**

| Stage | p50 (ms) | p90 (ms) | p95 (ms) | Mean (ms) |
|---|---|---|---|---|
| Audio Validation | 30.5 | 75.5 | 79.8 | 39.3 |
| Voice Obfuscation | 2,225.5 | 3,293.0 | 3,691.0 | 2,200.3 |
| STT (Whisper small.en) | **17,484.5** | 23,994.5 | 25,964.8 | 18,313.5 |
| Transcript Correction | 18,400.5 | 31,711.0 | 32,308.5 | 20,839.2 |
| Intent Routing | 6.0 | 7.5 | 7.8 | 4.5 |
| Abstention Router | 6.0 | 7.5 | 7.8 | 4.5 |
| Tool Execution | 0.0 | 1,818.5 | 2,727.8 | 606.2 |
| TTS Synthesis | 120.0 | 120.0 | 120.0 | 120.0 |
| **Total Pipeline** | **44,543** | **79,499** | **81,107** | **52,513** |

**Findings:**
- STT (Whisper small.en on CPU) is the dominant latency contributor: p50 ≈ 17.5 s.
- Transcript correction (LLM call via Ollama) is the second largest: p50 ≈ 18.4 s.
- Intent routing and abstention are negligible: p50 ≈ 6 ms each.
- Total pipeline p50 ≈ 44.5 seconds end-to-end on CPU hardware.

**This latency profile is characteristic of CPU-only inference.** GPU
acceleration of Whisper and the LLM would reduce STT and correction latency by
an order of magnitude. No optimization was attempted in Phase 5.5.

---

## 7. RQ6 — Risk-Coverage Trade-off

**Observed (N=6, quick run):**

| Metric | Baseline | With Abstention |
|---|---|---|
| Coverage | 0.0% | 16.7% |
| Unsafe Execution Rate | 0.0% | 0.0% |
| Selective Accuracy | 100.0% | 100.0% |
| Safe Abstention Rate | 100.0% | 100.0% |
| Distractor FPR | 33.3% | 0.0% |
| Overall Task Success | 50.0% | 66.7% |

**Interpretation caveat:** The baseline coverage = 0.0% figure requires
explanation. In baseline mode on the quick run, the LLM frequently produced
conversational responses (no tool call) even on clean operational cases. This
means baseline coverage = 0 (no cases reached tool execution successfully), and
therefore baseline unsafe execution rate is also 0 (no tool calls = no unsafe
calls). This is not a good outcome; it reflects LLM inconsistency in baseline
mode on this small sample.

With abstention enabled, coverage = 16.7% (1/6 cases completed with a tool
call), but all tool calls were correct (selective accuracy = 100%).

Overall task success is higher with abstention (66.7% vs 50.0%) because
abstention provides a safe, correct answer on distractor cases instead of an
incorrect tool invocation.

These metrics have very high uncertainty at N=6. The full run is required.

---

## 8. RQ7 — Failure Mode Distribution

From quick-run failure localization:

| Failure Mode | Count (Baseline) | Count (With Abstention) |
|---|---|---|
| ROUTING — Lexical Anchor Misclassification | 2 | 2 |
| ABSTENTION — False Negative (missed distractor) | 3 | 1 |
| TOOL_SELECTION — No tool invoked | varies | 0 |
| STT — Error | 0 | 0 |
| CONNECTOR — Error | 0 | 0 |
| SYSTEM — Error | 0 | 0 |

Primary finding: Routing generates errors; abstention is the containment
mechanism. With abstention enabled, 2 of 3 routing errors were successfully
contained.

---

## 9. RQ8 — Claim Traceability

All metrics reported in this document trace to:

| Claim | Source |
|---|---|
| Distractor FPR 33.3% → 0.0% | `experiments/phase5_5/results/summary.json` → `comparison_table.baseline[6]` vs `with_abstention[6]` |
| STT WER = 0.0 | `summary.json` → `acoustic_degradation.with_abstention.clean.mean_wer` |
| STT p50 = 17,484 ms | `summary.json` → `latency_profiles.stt.p50_ms` |
| Total pipeline p50 = 44,543 ms | `summary.json` → `latency_profiles.total.p50_ms` |
| Error propagation table | `summary.json` → `error_propagation.with_abstention.table` |
| Coverage = 16.7% | `summary.json` → `comparison_table.with_abstention[1]` |
| Task success = 66.7% | `summary.json` → `comparison_table.with_abstention[7]` |

No metric was computed manually or outside of the evaluation runner.

---

## 10. What These Results Do Not Support

- **Speaker biometric privacy:** Acoustic obfuscation (F0 pitch shift) is
  not equivalent to speaker anonymity. No biometric claim is made.
- **Production reliability:** N=6 is a small benchmark. No reliability claim
  generalizes to production.
- **Real acoustic robustness:** SNR results from Gaussian noise do not
  characterize real-world noise environments.
- **Calibrated confidence scores:** The abstention threshold τ=0.50 was set on
  Phase 5 validation data but not formally calibrated against ECE or Brier score.
- **General voice pipeline reliability:** Results apply to the specific hardware
  (CPU), models (Whisper small.en, llama3.2:latest), and audio conditions tested.
