# Phase 4.6 — Experimental Integrity & Forensic Audit

**Auditor:** Independent Critical Audit  
**Target:** Phase 4 Research Evaluation Framework & Artifacts  
**Status:** Comprehensive Audit Completed  
**Guiding Principle:** Evidence before adjectives.  

---

## 1. Executive Forensic Summary

Phase 4 claimed to deliver research-grade evaluation, out-of-distribution generalization, physical acoustic privacy, and systematic ablations. While foundational infrastructure was built, a critical audit revealed that several major claims were **empirically invalid, overstated, or measured using artificial proxies rather than the physical voice pipeline**.

| Investigation Area | Phase 4 Claim | Empirical Finding | Audit Verdict |
| :--- | :--- | :--- | :--- |
| **Held-Out Generalization** | "100.0% Accuracy across 30 cases" | Actual executed runner output: **86.7% (26/30)** | **INVALID / OVERSTATED** |
| **Adversarial False Positives** | "0.0% FPR on conversational distractors" | Actual executed output on held-out: **60.0% FPR (3/5 failed)** | **INVALID / OVERSTATED** |
| **Challenge Set Resilience** | "100.0% intentional alignment across 25 cases" | Actual executed runner output: **84.0% (21/25)** | **INVALID / OVERSTATED** |
| **Acoustic Privacy** | "Formant preservation balances privacy & utility" | $F_0$ shift $\ne$ speaker privacy. Spectral envelope ($sp$) was preserved, leaving biometric timbre cues intact. | **SCIENTIFICALLY FLAWED** |
| **Component Ablation** | "Systematic isolation of 5 mechanisms" | `ablate_tool_alignment` was a complete no-op; runner used decoupled micro-loops instead of the pipeline. | **METHODOLOGICALLY FLAWED** |
| **Metamorphic Invariance** | "Metamorphic testing of behavioral invariants" | Tests asserted against hardcoded expected labels ($f(x) == y_{\text{expected}}$) rather than relational transformations ($f(T(x)) \sim f(x)$). | **MISLABELED UNIT TESTS** |
| **End-to-End Voice Evaluation** | "Master reproducibility runner evaluates voice agent" | Master runner passed raw strings directly to `classify_intent()`, bypassing audio, STT, and LLM entirely. | **PROXY MISREPRESENTATION** |
| **Acoustic Robustness** | "Evaluates pipeline across SNR noise grid" | STT was never run on noisy speech; noise was simulated by dropping words from Python strings. | **SIMULATED PROXY** |

---

## 2. Detailed Claim-by-Claim Audit

### Claim 1: Held-Out Test Accuracy
- **Claim:** "100.0% accuracy across 30 previously unseen queries."
- **Source File:** `docs/final_evaluation_report.md` (Section 1 & 3.1), `experiments/results/dashboard.html`.
- **Runner Used:** `evaluation/run_final_experiment.py` (Step 1).
- **Dataset:** `evaluation/datasets/held_out_test/held_out_test_v1.jsonl` (SHA256: `82EFA536...`).
- **Actual Implementation:** Evaluated `classify_intent(c["input_text"]).route == c["expected_route"]`.
- **Actual Empirical Result:** **26/30 = 86.67%** accuracy (4 failures).
- **Validity:** **INVALID**.
- **Reason:** Narrative reports claimed perfection, directly contradicting the runner's serialized JSON manifest (`"overall_accuracy": 0.8667`).
- **Required Correction:** Report the genuine 86.7% metric in all documentation, dashboards, and reports. Document the 4 failure cases.

---

### Claim 2: Adversarial Rejection / False Positive Rate
- **Claim:** "0.0% False Positive Rate on conversational distractors."
- **Source File:** `docs/final_evaluation_report.md` (Table 3.1), `experiments/results/dashboard.html`.
- **Runner Used:** `evaluation/runners/ablation_runner.py` / `run_final_experiment.py`.
- **Dataset:** `evaluation/datasets/held_out_test/held_out_test_v1.jsonl` (Adversarial subset, $N=5$).
- **Actual Implementation:** Evaluated if adversarial non-data queries triggered a `tool` call.
- **Actual Empirical Result:** 3 out of 5 adversarial queries triggered a `tool` route:
  - `"I bought a concert ticket for tomorrow performance"` $\to$ `tool` (FAILED)
  - `"Customer feedback was overwhelmingly positive during the product launch"` $\to$ `tool` (FAILED)
  - `"She showed great enthusiasm for customer satisfaction"` $\to$ `tool` (FAILED)
  - **Observed Adversarial FPR:** **60.0%** (2/5 correct = 40.0% accuracy).
- **Validity:** **INVALID**.
- **Reason:** The 0.0% FPR claim was true only for the Phase 2 training set (`voice_eval_v1.jsonl`) where regexes had been explicitly tuned. On the held-out set, naive keyword containment (`ticket`, `customer`) produced false positives.
- **Required Correction:** Report 60.0% observed FPR on held-out adversarial cases. Explicitly discuss the fragility of lexical entity anchoring.

---

### Claim 3: Challenge Set Resilience
- **Claim:** "100.0% intentional routing alignment across 25 challenge queries."
- **Source File:** `docs/final_evaluation_report.md` (Section 1 & 3.2), `dashboard.html`.
- **Runner Used:** `evaluation/run_final_experiment.py` (Step 2).
- **Dataset:** `evaluation/datasets/challenge/challenge_v1.jsonl` (SHA256: `0DED94AC...`).
- **Actual Implementation:** Evaluated `classify_intent(c["input_text"]).route == c["expected_route"]`.
- **Actual Empirical Result:** **21/25 = 84.00%** accuracy (4 failures).
- **Validity:** **INVALID**.
- **Reason:** Report claimed 100.0%, ignoring 4 real failures.
- **Required Correction:** Report 84.0% accuracy and analyze the failure modes.

---

### Claim 4: Speaker Privacy via $F_0$ Fundamental Frequency Shift
- **Claim:** "Formant-preserving obfuscation achieves an F0 shift of 22–65 Hz... providing the optimal empirical balance on the Pareto frontier between privacy and utility."
- **Source File:** `docs/final_evaluation_report.md` (Section 3.3).
- **Runner Used:** `evaluation/runners/privacy_acoustic_runner.py`.
- **Dataset:** `benchmark_audio/phrase_*.wav` ($N=8$).
- **Actual Implementation:** Measured mean $F_0$ difference using YIN algorithm (`librosa.yin`).
- **Validity:** **SCIENTIFICALLY INVALID**.
- **Reason:** 
  1. $F_0$ shift $\ne$ speaker privacy.
  2. The WORLD vocoder in `FormantPreservingObfuscator` explicitly holds the spectral envelope ($sp$) fixed to preserve phonetic intelligibility for Whisper. But $sp$ carries vocal tract resonances (formants), which are the primary acoustic features utilized by neural speaker identification systems (x-vectors, ECAPA-TDNN).
  3. A 26.9 Hz pitch shift (1.5–2 semitones) falls entirely within natural human prosodic and diurnal pitch variation.
- **Required Correction:** Rename all reporting to "Acoustic Obfuscation Analysis". Explicitly state: *"Speaker privacy was not empirically established in this study."*

---

### Claim 5: Component Ablation Study
- **Claim:** "Quantifies the unique empirical contribution of each component across 6 distinct conditions."
- **Source File:** `docs/final_evaluation_report.md` (Section 3.2), `evaluation/runners/ablation_runner.py`.
- **Actual Implementation:**
  - `ablate_tool_alignment` had no logic branch in `ablation_runner.py` and executed the identical code path as `full_system`.
  - The runner did not execute an end-to-end pipeline; it executed 3 disconnected micro-evaluations (routing on held-out text, correction on 4 hardcoded string pairs, and retry on 1 synthetic connector call).
  - `legacy_keyword_route` used an arbitrary 7-keyword list rather than the actual 18-keyword list from Phase 1.
- **Validity:** **METHODOLOGICALLY FLAWED**.
- **Required Correction:** Reconstruct a genuine ablation framework where disabling a component removes that exact mechanism from the real execution path.

---

### Claim 6: Metamorphic Behavioral Invariant Testing
- **Claim:** "16/16 metamorphic tests passed, proving behavioral invariance across paraphrases."
- **Source File:** `tests/test_phase4/test_metamorphic.py`, `dashboard.html`.
- **Actual Implementation:**
  ```python
  expected = group["expected_intent"]
  for text in group["inputs"]:
      res = classify_intent(text)
      assert res.intent == expected  # Hardcoded test oracle
  ```
- **Validity:** **MISLABELED**.
- **Reason:** Metamorphic testing requires testing relational invariants under input transformations without reference to an oracle ($f(T(x)) \sim f(x)$). Testing $f(x) == \text{oracle}$ is standard unit testing.
- **Required Correction:** Implement true metamorphic relations (politeness markers, filler insertion, casing, punctuation) checking that transformed inputs match original input predictions.

---

### Claim 7: Master Experiment Voice Assistant Evaluation
- **Claim:** "Master reproducibility runner evaluates voice agent end-to-end."
- **Source File:** `evaluation/run_final_experiment.py`.
- **Actual Implementation:** `run_final_experiment.py` passed `.jsonl` text strings directly to `classify_intent(text)`. No audio was played or synthesized; Whisper was not invoked; LLM tool argument generation was not called.
- **Validity:** **PROXY MISREPRESENTATION**.
- **Required Correction:** Explicitly split evaluation into **Level A (Component Evaluation - Text)** and **Level B (Voice Pipeline Evaluation - Audio $\to$ STT $\to$ Tool Execution)**. Never call Level A "voice evaluation".

---

### Claim 8: Acoustic Robustness Evaluation
- **Claim:** "Evaluates pipeline performance under acoustic stress across additive Gaussian noise (SNR 10dB–$\infty$)."
- **Source File:** `evaluation/runners/robustness_runner.py`.
- **Actual Implementation:** In `robustness_runner.py`, noise was added to 1 audio sample for feature extraction, but pipeline routing robustness was tested by:
  ```python
  corrupted_words = [w for i, w in enumerate(words) if i != 1] # Dropped second word in string!
  ```
- **Validity:** **SIMULATED PROXY**.
- **Required Correction:** Run actual speech audio through physical perturbations, feed through Whisper STT, and measure real Word Error Rate (WER) and downstream routing retention.

---

## 3. Verified Current Baseline Metrics

These are the independently verified empirical metrics of the frozen datasets as of Phase 4.6 start:

| Evaluation Dataset | Sample Size ($N$) | Metric | Independently Verified Result |
| :--- | :--- | :--- | :--- |
| **Held-Out Generalization** (`held_out_test_v1.jsonl`) | 30 | Overall Routing Accuracy | **86.67% (26 / 30)** |
| — CRM Subcategory | 5 | Routing Accuracy | 100.0% (5 / 5) |
| — Support Subcategory | 5 | Routing Accuracy | 100.0% (5 / 5) |
| — Analytics Subcategory | 5 | Routing Accuracy | 100.0% (5 / 5) |
| — Direct General Subcategory | 5 | Routing Accuracy | 100.0% (5 / 5) |
| — Adversarial Subcategory | 5 | Routing Accuracy | **40.0% (2 / 5)** |
| — Adversarial Subcategory | 5 | False Positive Rate (FPR) | **60.0% (3 / 5)** |
| — Boundary Subcategory | 2 | Routing Accuracy | 100.0% (2 / 2) |
| — Ambiguous Subcategory | 3 | Routing Accuracy | 66.67% (2 / 3) |
| **Challenge Suite** (`challenge_v1.jsonl`) | 25 | Overall Routing Accuracy | **84.00% (21 / 25)** |
| — STT Misleading Subcategory | 5 | Routing Accuracy | **80.0% (4 / 5)** |
| — Subtle Adversarial Subcategory | 5 | Routing Accuracy | 100.0% (5 / 5) |
| — Contradictory Args Subcategory | 3 | Routing Accuracy | 100.0% (3 / 3) |
| — Boundary Args Subcategory | 6 | Routing Accuracy | **83.3% (5 / 6)** |
| — Correction Trap Subcategory | 3 | Routing Accuracy | **33.3% (1 / 3)** |
| — Near-Duplicate Paraphrase | 3 | Routing Accuracy | 100.0% (3 / 3) |

---

## 4. Known Failure Cases Inventory (Preserved for Science)

The following 8 failed cases are documented and preserved. They must **not** be patched with ad-hoc regex rules:

### A. Held-Out Set Failures (4 cases)

1. **`ho_adv_001`**:
   - *Input:* `"I bought a concert ticket for tomorrow performance"`
   - *Expected Route:* `direct`
   - *Observed Route:* `tool` (`get_support_tickets`)
   - *Root Cause:* Containment of token `"ticket"` triggered `SUPPORT_PATTERNS`. The router lacks syntactic disambiguation for non-technical ticket domains.
2. **`ho_adv_002`**:
   - *Input:* `"Customer feedback was overwhelmingly positive during the product launch"`
   - *Expected Route:* `direct`
   - *Observed Route:* `tool` (`get_crm_data`)
   - *Root Cause:* Token `"customer"` triggered `CRM_PATTERNS`. Sentiment words like `"positive"` were not in the adversarial direct filter list.
3. **`ho_adv_005`**:
   - *Input:* `"She showed great enthusiasm for customer satisfaction"`
   - *Expected Route:* `direct`
   - *Observed Route:* `tool` (`get_crm_data`)
   - *Root Cause:* Token `"customer"` matched without recognizing `"customer satisfaction"` as a conversational abstract noun.
4. **`ho_amb_003`**:
   - *Input:* `"Display analytics overview"`
   - *Expected Route:* `tool` (`get_analytics`)
   - *Observed Route:* `tool` (`get_analytics` with confidence 0.85). Note: Evaluated as mismatch depending on expected argument schema requirements.

### B. Challenge Set Failures (4 cases)

5. **`ch_stt_004`**:
   - *Input:* `"Tell me how support ticket priority is calculated"`
   - *Expected Route:* `direct`
   - *Observed Route:* `tool` (`get_support_tickets`)
   - *Root Cause:* Informational inquiry contains domain nouns `"support ticket priority"`, overriding the intent classifier.
6. **`ch_bnd_006`**:
   - *Input:* `"List top negative five customers"`
   - *Expected Route:* `direct` (nonsensical query)
   - *Observed Route:* `tool` (`get_crm_data`)
   - *Root Cause:* The router matches `"list"` + `"customers"` and delegates argument parsing downstream rather than rejecting at routing.
7. **`ch_trp_001`**:
   - *Input:* `"Fetch inactve custumers"`
   - *Expected Route:* `tool` (`get_crm_data`)
   - *Observed Route:* `direct`
   - *Root Cause:* Uncorrected typos in `"custumers"` prevent exact regex matching on `"customer"`. (Demonstrates failure of text-only routing without transcript correction).
8. **`ch_trp_003`**:
   - *Input:* `"Retreive acive accunts"`
   - *Expected Route:* `tool` (`get_crm_data`)
   - *Observed Route:* `direct`
   - *Root Cause:* Double typo in `"acive accunts"` fails exact regex entity matching.
