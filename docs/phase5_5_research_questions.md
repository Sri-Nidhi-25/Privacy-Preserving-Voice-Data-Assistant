# Phase 5.5 — Research Questions

> **Do the reliability mechanisms developed through Phases 4.6 and 5 remain
> effective when the system receives real audio and processes it through the
> complete voice pipeline?**

---

## RQ1 — End-to-End Pipeline Integrity

> Does each component of the voice pipeline (audio validation → obfuscation →
> STT → correction → routing → abstention → tool selection → connector → TTS)
> execute in sequence without unhandled exceptions across the 40-case Phase 5.5
> benchmark?

**Operationalization:** Count pipeline completion rate; record any unhandled
exception by stage; confirm every case terminates with either a safe answer
or an explicit abstention response.

---

## RQ2 — Abstention Survival Through the Voice Pipeline

> Does the selective abstention mechanism (τ = 0.50) that was calibrated on
> text-only Phase 5 data continue to correctly suppress distractor execution
> when input arrives as real speech transcribed by Whisper?

**Operationalization:** Compare distractor False Positive Rate (FPR) between
baseline (no abstention) and abstention-enabled modes on Category B
(semantic distractors, 10 cases) using real synthesized audio → Whisper STT
→ abstention router.

**Null hypothesis:** STT transcription noise does not cause the abstention
router to change its decision compared to the text-only baseline.

---

## RQ3 — Error Propagation and Stage-Level Failure Localization

> When an E2E evaluation case fails, which pipeline stage is responsible, and
> does the error propagate or is it contained?

**Operationalization:**
- Apply `localize_failure()` to every failing case.
- Compute for each stage: errors entering, errors created, errors contained,
  unsafe outcomes.
- Report the error propagation table.

---

## RQ4 — Acoustic Degradation and SNR Interaction

> How does additive Gaussian noise (simulating acoustic degradation at SNR
> 30 dB, 20 dB, 10 dB) affect STT transcription quality (WER/CER), routing
> retention rate, and abstention behaviour?

**Operationalization:** For each of the 4 Category E base phrases, synthesize
audio at 3 SNR levels. Compute WER, routing retention, and abstention decision
rate across SNR levels. Report whether the abstention threshold adapts or
degrades with noise.

**Important limitation:** Noise is synthesized Gaussian (not real room noise).
This is documented explicitly as a proxy; no broader acoustic robustness
claim is made.

---

## RQ5 — Pipeline Latency Profile

> What is the per-stage latency distribution (p50/p90/p95) across the complete
> voice pipeline, and which stages dominate total latency?

**Operationalization:** Measure wall-clock time for each stage (validation,
obfuscation, STT, correction, routing, abstention, tool, TTS) across all cases.
Report p50/p90/p95 and the cumulative pipeline total.

---

## RQ6 — Risk-Coverage Trade-off in the E2E Setting

> Does selective abstention achieve a favorable risk-coverage trade-off in the
> E2E setting — i.e., does coverage decrease only moderately while risk
> (unsafe execution rate) decreases substantially?

**Operationalization:** Compute Coverage, Risk (unsafe execution rate on
distractors/ambiguous cases), Selective Accuracy, and Safe Abstention Rate
for both baseline and abstention-enabled modes. Plot the risk-coverage
frontier from the 40-case benchmark.

---

## RQ7 — Failure Mode Classification

> What are the primary categories of failure observed in the E2E pipeline,
> and how are they distributed across stages?

**Operationalization:** Classify every non-null failure stage from
`localize_failure()` into the taxonomy:
- STT_ERROR
- ROUTING_MISCLASSIFICATION
- ABSTENTION_FALSE_POSITIVE (over-abstains)
- ABSTENTION_FALSE_NEGATIVE (misses distractors)
- TOOL_SELECTION_ERROR
- CONNECTOR_FAILURE
- SYSTEM_FAILURE

Report counts and proportions.

---

## RQ8 — Claim Traceability

> Does every qualitative claim in Phase 5.5 documentation trace directly to
> an experiment, a dataset, a runner script, and actual observed values?

**Operationalization:** For every claim in `docs/phase5_5_results.md`, verify:
1. The runner script that produced it exists and is executable.
2. The dataset it ran on is named and its category is defined.
3. The reported number matches `experiments/phase5_5/results/summary.json` or
   the run JSONL files.
4. The claim qualifier (e.g. "substantially", "consistently") is grounded in
   the observed magnitude.

---

## Non-Questions (Out of Scope for Phase 5.5)

The following are explicitly **not** research questions for this phase:

- Speaker biometric privacy — F0 shift is **not** evidence of speaker anonymity.
- Production reliability — this is a small-N research benchmark (N ≤ 40).
- Real-world acoustic robustness — noise is synthesized, not captured.
- Latency optimization — this phase measures latency, not reduces it.
- New reliability interventions — Phase 5.5 measures existing ones, not new ones.
