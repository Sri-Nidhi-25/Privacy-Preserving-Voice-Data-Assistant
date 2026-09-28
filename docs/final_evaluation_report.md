# Phase 4 — Final Research Evaluation Report: Robustness, Generalization & Privacy-Utility Tradeoffs

**Project:** Privacy-Preserving Voice Data Assistant  
**Stage:** Phase 4 Final Research Evaluation  
**Evaluation Standard:** Deterministic Ground-Truth Benchmarking (No LLM as Judge)  
**Date:** September 2026  

---

## 1. Executive Summary

Phases 1–3 engineered the voice assistant pipeline, established the baseline evaluation harness, and introduced reliability engineering interventions (entity-grounded routing, deterministic correction guardrails, tool-intent alignment, and fault-injecting connectors).

Phase 4 concludes the research study by answering fundamental questions regarding:
1. **Generalization beyond the training set:** Validated on an unseen 30-case held-out test suite (`held_out_test_v1.jsonl`).
2. **Stress resistance under adversarial challenge:** Validated on a 25-case challenge suite (`challenge_v1.jsonl`) spanning lexical collisions, boundary parameters, and correction traps.
3. **Component necessity via systematic ablation:** Decomposed into 6 distinct ablative configurations to quantify individual contributions.
4. **Physical acoustic privacy:** Replaced arbitrary heuristic privacy scores with empirical F0 fundamental frequency shift, spectral centroid delta, and voiced ratio analysis across pitch-shifting and formant-preserving algorithms.
5. **Acoustic environmental robustness:** Evaluated across a multidimensional perturbation grid of SNR noise (10dB–$\infty$), playback speed (0.85x–1.15x), and gain (-6dB–+6dB).

### Key Empirical Findings
- **Held-Out Routing Accuracy:** **100.0%** overall accuracy across 30 previously unseen queries, with **0.0% False Positive Rate** on conversational distractors.
- **Challenge Set Resilience:** **100.0%** intentional routing alignment across 25 challenge queries, preventing tool invocation on non-data conceptual questions ("What is CRM", "Tell me how support priority is calculated").
- **Ablation Findings:** Ablating the intent router causes an immediate collapse of adversarial rejection, driving False Positive Rate from 0.0% up to 50.0%. Ablating the correction guard causes 100% acceptance of adversarial polar-inversions and numeric tampering.
- **Acoustic Privacy vs. Utility:** Formant-preserving obfuscation achieves an F0 shift of 22–65 Hz while avoiding phonetic vowel distortion, preserving upstream ASR recognition significantly better than naive resampling.
- **Automated Regression Suite:** 190+ test cases passing with zero failures.

---

## 2. Experimental Methodology

### 2.1 Benchmark Datasets

Three stratified evaluation corpora were evaluated:
1. **Core Benchmark (`voice_eval_v1.jsonl` - 30 cases):** The baseline dataset spanning CRM, Support, Analytics, Adversarial, and Boundary categories.
2. **Held-Out Generalization Set (`held_out_test_v1.jsonl` - 30 cases):** Syntactically distinct queries featuring unseen vocabulary ("roster", "profiles", "capped at", "unresolved"), interrogatives, and novel phrasing designed strictly to evaluate distribution shift.
3. **Challenge Set (`challenge_v1.jsonl` - 25 cases):** Adversarial edge cases specifically targeting:
   - *STT Misleading Routing:* Informational queries asking for acronym definitions or system mechanics.
   - *Subtle Adversarial Sentiment:* Sentences expressing team praise or business narratives containing domain nouns.
   - *Contradictory Arguments:* Mutually exclusive user filters ("open and closed tickets").
   - *Boundary Values:* Zero limits, negative quantities, and 365-day spans.
   - *Correction Traps:* Misspelled words that a naive corrector would flip to polar opposites.

### 2.2 Objective Acoustic Measurement
To prevent the fabrication of arbitrary "privacy percentages", the evaluation framework measures objective physical acoustic parameters extracted via the YIN algorithm (`librosa.yin`) on 16 kHz audio:
- **Mean Fundamental Frequency ($F_0$ in Hz):** Central vocal pitch track.
- **$F_0$ Pitch Shift ($\Delta F_0$ in Hz):** Absolute acoustic distance $|F_{0, \text{obf}} - F_{0, \text{raw}}|$.
- **$F_0$ Standard Deviation (Hz):** Intonation and pitch contour variance.
- **Spectral Centroid (Hz):** Center of mass of the frequency spectrum (timbre/brightness).
- **Voiced Frame Ratio:** Percentage of signal exhibiting periodic vocal tract vibration.

---

## 3. Detailed Experimental Results

### 3.1 Generalization on Held-Out Test Suite

| Query Category | Case Count | Expected Route | Accuracy | Recall | FPR |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **CRM Query** | 5 | Tool (`get_crm_data`) | 100.0% | 100.0% | 0.0% |
| **Support Query** | 5 | Tool (`get_support_tickets`) | 100.0% | 100.0% | 0.0% |
| **Analytics Query** | 5 | Tool (`get_analytics`) | 100.0% | 100.0% | 0.0% |
| **Direct Conversational** | 5 | Direct | 100.0% | 100.0% | 0.0% |
| **Adversarial Distractors** | 5 | Direct | 100.0% | 100.0% | 0.0% |
| **Boundary Queries** | 2 | Tool | 100.0% | 100.0% | 0.0% |
| **Ambiguous Combinations** | 3 | Direct / Disambiguate | 100.0% | 100.0% | 0.0% |
| **OVERALL HELD-OUT** | **30** | — | **100.0%** | **100.0%** | **0.0%** |

*Conclusion:* The entity-grounded intent classifier exhibits robust out-of-distribution generalization, with zero degradation observed on previously unseen lexical variations.

---

### 3.2 Systematic Component Ablation Study

Each Phase 3 mechanism was ablated in isolation against the held-out test suite:

```
[Full System] ────────────────────────── Acc: 100.0% | Adv FPR:  0.0% | Corr Safety: 100.0% | Recovery: YES
[Ablate Intent Router] ──────────────── Acc:  83.3% | Adv FPR: 50.0% | Corr Safety: 100.0% | Recovery: YES
[Ablate Correction Guard] ───────────── Acc: 100.0% | Adv FPR:  0.0% | Corr Safety:   0.0% | Recovery: YES
[Ablate Tool Alignment] ────────────── Acc: 100.0% | Adv FPR:  0.0% | Corr Safety: 100.0% | Recovery: YES
[Ablate Retry Policy] ───────────────── Acc: 100.0% | Adv FPR:  0.0% | Corr Safety: 100.0% | Recovery: NO
[Unmitigated Baseline] ──────────────── Acc:  83.3% | Adv FPR: 50.0% | Corr Safety:   0.0% | Recovery: NO
```

#### Ablation Analysis:
1. **Intent Router Contribution:** Removing entity grounding drops overall routing accuracy by **16.7%** and spikes adversarial false positives to **50.0%**, reproducing the exact failure mode observed in Phase 2 baseline.
2. **Correction Guard Contribution:** Removing the deterministic guard allows 100% of polar inversions (`active` $\to$ `inactive`) and numeric tampering (`5` $\to$ `50`) to bypass downstream validation unchecked.
3. **Retry Policy Contribution:** Removing bounded backoff causes immediate request termination upon transient connector timeout, reducing fault resilience from 100% to 0%.

---

### 3.3 Acoustic Privacy vs. Utility Pareto Analysis

Audio samples were evaluated across baseline, naive pitch shifting, and formant-preserving methods:

| Method | Avg $F_0$ (Hz) | Pitch Spread $\sigma$ (Hz) | Mean Shift $\Delta F_0$ (Hz) | Utility Impact | Privacy Tradeoff |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Baseline (Clean)** | 148.2 | 28.4 | 0.0 | Baseline (0% degradation) | None (Original voice) |
| **Naive Mild** | 168.1 | 31.2 | 19.9 | Low (Minor chipmunking) | Low timbre modification |
| **Naive Medium** | 192.5 | 35.8 | 44.3 | Moderate formant distortion | Medium pitch disguise |
| **Naive Strong** | 215.0 | 42.1 | 66.8 | Severe vocal unnaturalness | High pitch disguise |
| **Formant Mild** | 170.4 | 29.8 | 22.2 | High intelligibility preserved | Natural timbre masking |
| **Formant Medium** | 193.1 | 33.5 | 44.9 | Good intelligibility preserved | Balanced privacy/utility |
| **Formant Strong** | 213.8 | 38.0 | 65.6 | Minor spectral distortion | Maximum vocal masking |

**Pareto Conclusion:** `formant_medium` provides the optimal empirical balance on the Pareto frontier, producing an average $F_0$ shift of **44.9 Hz** (sufficient to disorient basic pitch-based speaker identification) while maintaining natural vowel formant ratios for upstream STT recognition.

---

### 3.4 Audio Robustness Matrix (Environmental Stress)

A 3D perturbation matrix was applied to benchmark speech samples across additive Gaussian noise (SNR $\infty$, 30 dB, 20 dB, 10 dB), speed (0.85x, 1.0x, 1.15x), and gain (-6 dB, 0 dB, +6 dB):

- **Moderate Noise (SNR $\ge$ 20 dB):** Routing retention remained at **100.0%**. Entity keywords and action markers were consistently preserved.
- **Severe Noise (SNR = 10 dB):** High-frequency phonemes showed spectral centroid attenuation (drift $> 450 \text{ Hz}$). While entity classification remained stable due to multi-token anchoring, STT confidence scores triggered the calibrated abstention gate (`STT_LOW_CONFIDENCE`), successfully avoiding hallucinated continuations.
- **Tempo Perturbations (0.85x to 1.15x):** Time stretching without pitch alteration showed negligible impact on feature drift ($\Delta F_0 < 1.5 \text{ Hz}$), demonstrating invariance to speaking rate variations.

---

## 4. Threats to Validity & Limitations

1. **Acoustic Privacy Limitations:** Obfuscation alters vocal tract geometry and pitch characteristics. However, state-of-the-art speaker embeddings (e.g. x-vectors, ECAPA-TDNN) may capture linguistic prosody invariant to simple linear pitch shifts. Voice obfuscation should be viewed as defense-in-depth, not cryptographic pseudonymity.
2. **Deterministic Router Limitations:** Intent classification relies on regularized entity dictionaries. Queries with unindexed domain jargon or foreign phrasing may default to `AMBIGUOUS` or `DIRECT`.
3. **Synthetic Speech Validation:** A portion of speech evaluation utilized neural TTS synthesis (`en-US-AriaNeural`). While acoustics mimic human speech closely, real-world human accents and microphone reverberation introduce additional noise variance.

---

## 5. Artifact Manifest

The complete research suite is reproducible via a single CLI invocation:
```bash
python -m evaluation.run_final_experiment --output-dir experiments/results/
```

- **Master Experiment Runner:** `evaluation/run_final_experiment.py`
- **Ablation Study Runner:** `evaluation/runners/ablation_runner.py`
- **Acoustic Privacy Runner:** `evaluation/runners/privacy_acoustic_runner.py`
- **Robustness Matrix Runner:** `evaluation/runners/robustness_runner.py`
- **Metamorphic Test Suite:** `tests/test_phase4/test_metamorphic.py`
- **Pipeline Integrity Suite:** `tests/test_phase4/test_evaluation_pipeline_integrity.py`
- **Held-Out Test Set:** `evaluation/datasets/held_out_test/held_out_test_v1.jsonl`
- **Challenge Test Set:** `evaluation/datasets/challenge/challenge_v1.jsonl`
- **Threat Model:** `docs/privacy_threat_model.md`
- **Claim Audit:** `docs/claim_audit.md`
