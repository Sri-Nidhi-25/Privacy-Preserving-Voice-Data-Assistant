# Phase 4 Initial Audit: Assessment of Phases 1–3

## Executive Audit Summary

This document performs a critical, rigorous audit of the repository following the completion of Phase 1 (Reliability Foundations), Phase 2 (Evaluation & Measurement), and Phase 3 (Reliability Improvements, Calibration & Fault Injection). 

The goal of this audit is to identify what has been solidly established by evidence, what weaknesses or untested assumptions remain, and to formulate the formal research questions for Phase 4.

---

## 1. Current Capabilities & Infrastructure

| Layer | Component | Status | Verified Functionality |
|---|---|:---:|---|
| **Phase 1** | Central Failure Taxonomy | Verified | `FailureType` enum and `PipelineError` exception mapping to HTTP errors. |
| **Phase 1** | Audio Validation | Verified | Decodability check, duration bounds (0.1s - 120s), size checks (<25MB). |
| **Phase 1** | Observability & Freshness | Verified | UUID request tracking, structured logging, honest mtime freshness timestamps. |
| **Phase 2** | Evaluation Schemas & Dataset | Verified | Stable `EvalRecord` schema, 30-case `voice_eval_v1.jsonl` benchmark. |
| **Phase 2** | Metrics Library | Verified | Independent WER, CER, binary routing F1/FPR, tool accuracy, failure matrix. |
| **Phase 2** | Multi-Stage Runners | Verified | Component routing runner, obfuscation runner, transcription runner, E2E runner. |
| **Phase 3** | Entity-Grounded Intent Router | Verified | `classify_intent` eliminating 50% FPR on adversarial queries. |
| **Phase 3** | Deterministic Correction Gate | Verified | `apply_correction_gate` blocking polar inversions and numeric argument mutations. |
| **Phase 3** | Bounded Transient Recovery | Verified | `MAX_RETRIES=2` recovering transient faults, rejecting deterministic errors without retries. |
| **Phase 3** | Fault Injection & Invariants | Verified | Zero-fabrication on connector crash, tool mismatch rejection, text preservation on TTS failure. |

---

## 2. Current Measured Results

On the development dataset `voice_eval_v1.jsonl` ($N=30$ cases, seed=42):

- **Routing Accuracy:** 100.0% (improved from Phase 2 baseline of 83.3%)
- **Tool-Calling Precision:** 100.0% (improved from 80.0%)
- **Tool-Calling Recall:** 100.0% (0 missed tool calls)
- **Adversarial False Positive Rate:** 0.0% (reduced from 50.0% in Phase 2)
- **Correction Gate Rejection Accuracy:** 100.0% on adversarial mutations (polar terms, numbers, runaway text)
- **Transient Fault Recovery Rate:** 100.0% for transient connector resets
- **Unsafe Continuation Rate:** 0.0% across all injected failure modes
- **Regression Suite:** 173/173 automated tests passing

---

## 3. Remaining Weaknesses & Methodological Limitations

1. **Benchmark Overfitting Risk:**
   - The primary evaluation dataset (`voice_eval_v1.jsonl`) contains 30 samples. While comprehensive across categories, tuning intent router regexes and correction rules on this set poses a potential risk of overfitting to specific phrasing.
   - **Resolution in Phase 4:** Create a strict dataset split with an independent **Held-Out Test Set** ($N \ge 30$) and a deliberately adversarial **Challenge Set** ($N \ge 20$) that were never used during development.

2. **Acoustic Robustness Unknown:**
   - Testing has primarily used clean Edge-TTS audio. How the STT and downstream pipeline behave under background noise, low SNR, reverberation, speech rate variations, or clipping is unquantified.
   - **Resolution in Phase 4:** Implement a controlled **Audio Robustness Matrix** applying parameterized acoustic perturbations and measuring degradation curves.

3. **Privacy Measurement Incomplete:**
   - In Phases 2 and 3, privacy was honestly marked as `not_yet_measured` because running a full deep learning speaker verification model (e.g. SpeechBrain ECAPA-TDNN) requires large external model weights.
   - **Resolution in Phase 4:** Establish an explicit threat model and an empirical acoustic distance/feature dispersion metric (F0 pitch statistics + spectral formant dispersion) to construct a legitimate, non-fabricated **Privacy–Utility Pareto Frontier**.

4. **Metamorphic Invariance Untested:**
   - How robust is the intent router to semantic paraphrasing, politeness variations, or word order transformations?
   - **Resolution in Phase 4:** Build formal metamorphic tests asserting behavioral invariants across paraphrases.

5. **Evaluation Pipeline Self-Validation:**
   - Does the evaluation framework detect its own failures if corrupted datasets or broken schemas are ingested?
   - **Resolution in Phase 4:** Introduce `EVALUATION_FAILURE` taxonomy and evaluation pipeline self-tests.

---

## 4. Formal Research Questions (Phase 4)

### RQ1 — Robustness Under Distribution Shifts
> *How gracefully does transcription quality (WER), routing precision, and end-to-end task success degrade when acoustic conditions shift (additive noise, low volume, rate variations) and linguistic complexity increases?*

### RQ2 — Privacy–Utility Pareto Frontier
> *What is the quantitative tradeoff between increasing voice obfuscation strength (pitch shifting vs formant preservation) and downstream utility (WER, routing, task success), and does a Pareto-dominant configuration exist?*

### RQ3 — Generalization to Held-Out and Challenge Sets
> *Do the reliability improvements and zero-FPR guarantees discovered on the development set generalize to completely unseen held-out queries and deliberately deceptive challenge queries?*

### RQ4 — Component Failure Propagation & Contribution
> *Which pipeline stages contribute most strongly to end-to-end failure under clean vs perturbed conditions, and how much do individual reliability mechanisms (abstention, correction gate, retries) independently contribute to overall success?*

### RQ5 — Metamorphic Invariance
> *Does the pipeline preserve behavioral invariants (e.g. intent classification and argument extraction) under semantics-preserving linguistic transformations such as politeness markers and syntactic reordering?*

### RQ6 — Evaluation Framework Integrity
> *Can the evaluation system reliably detect and isolate evaluation-level failures (schema corruptions, label discrepancies) without conflating them with pipeline failures?*