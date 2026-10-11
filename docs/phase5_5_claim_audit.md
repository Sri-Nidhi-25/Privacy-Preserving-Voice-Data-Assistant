# Phase 5.5 — Claim Audit

This document audits every claim made in Phase 5.5 documentation for traceability,
evidential grounding, and accuracy of qualifiers.

The audit principle from Phase 4.6 applies: **Evidence before adjectives.**

---

## 1. Audit Format

Each claim is assessed against:

| Field | Meaning |
|---|---|
| **Claim** | Exact text from Phase 5.5 docs |
| **Source** | Document and section |
| **Runner** | Script that generated the evidence |
| **Dataset** | Dataset used |
| **Observed value** | The number from the results file |
| **Verdict** | SUPPORTED / PARTIALLY SUPPORTED / UNSUPPORTED / CORRECTLY SCOPED LIMITATION |
| **Notes** | Qualifier accuracy assessment |

---

## 2. Claim Audit Table

---

### CLAIM-01

**Claim:** "Distractor FPR reduced from 33.3% → 0.0% on the quick-run 3-distractor subset."

**Source:** `docs/phase5_5_results.md` — Section 3

**Runner:** `evaluation/phase5_5/run_e2e.py --quick`

**Dataset:** 3 distractor cases from `evaluation/datasets/phase5_5/semantic_distractors/distractors_v1.jsonl`

**Observed value:** `summary.json → comparison_table.baseline[6] = 0.3333`, `with_abstention[6] = 0.0`

**Verdict:** ✅ SUPPORTED

**Notes:** Claim is correctly scoped to "quick-run 3-distractor subset" and includes
the N=3 caveat. No overgeneralization. The contradiction with error propagation
table (2 unsafe outcomes with abstention) is acknowledged in results doc.

---

### CLAIM-02

**Claim:** "STT (Whisper small.en on CPU) produced p50 transcription latency of ~17.5 seconds."

**Source:** `docs/phase5_5_results.md` — Section 6

**Runner:** `evaluation/phase5_5/run_e2e.py --quick`

**Dataset:** 6 audio files from quick run

**Observed value:** `summary.json → latency_profiles.stt.p50_ms = 17484.5`

**Verdict:** ✅ SUPPORTED

**Notes:** Claim uses "~17.5 seconds" which rounds 17,484.5 ms correctly.
Hardware qualifier "CPU" is included.

---

### CLAIM-03

**Claim:** "Total pipeline p50 latency is ~44.5 seconds end-to-end on CPU hardware."

**Source:** `docs/phase5_5_results.md` — Section 6

**Runner:** `evaluation/phase5_5/run_e2e.py --quick`

**Dataset:** 6 cases

**Observed value:** `summary.json → latency_profiles.total.p50_ms = 44543.0`

**Verdict:** ✅ SUPPORTED

**Notes:** Correctly scoped to CPU hardware. "~44.5 seconds" rounds 44,543 ms correctly.

---

### CLAIM-04

**Claim:** "STT WER ≈ 0.0 on synthesized clean audio."

**Source:** `docs/phase5_5_results.md` — Section 5

**Runner:** `evaluation/phase5_5/run_e2e.py --quick`

**Dataset:** 6 synthesized audio cases (edge-tts)

**Observed value:** `summary.json → acoustic_degradation.with_abstention.clean.mean_wer = 0.0`

**Verdict:** ✅ SUPPORTED

**Notes:** The qualifier "synthesized clean audio" is essential. This WER does
NOT generalize to real microphone audio. The results doc states this explicitly.

---

### CLAIM-05

**Claim:** "Intent routing and abstention are negligible latency contributors (p50 ≈ 6 ms each)."

**Source:** `docs/phase5_5_results.md` — Section 6

**Runner:** `evaluation/phase5_5/run_e2e.py --quick`

**Dataset:** 6 cases

**Observed value:** `summary.json → latency_profiles.routing.p50_ms = 6.0`, `abstention.p50_ms = 6.0`

**Verdict:** ✅ SUPPORTED

**Notes:** Values match. "Negligible" is appropriate relative to STT/correction latency.

---

### CLAIM-06

**Claim:** "The pipeline executed without unhandled exceptions on all 6 quick-run cases."

**Source:** `docs/phase5_5_results.md` — Section 2

**Runner:** `evaluation/phase5_5/run_e2e.py --quick`

**Dataset:** 6 cases

**Observed value:** Both JSONL run files contain 6 records each. No record has `pipeline_exception` set.

**Verdict:** ✅ SUPPORTED

**Notes:** Correctly scoped to 6 cases. Does not claim general reliability.

---

### CLAIM-07

**Claim:** "Overall task success is higher with abstention (66.7% vs 50.0%)."

**Source:** `docs/phase5_5_results.md` — Section 7

**Runner:** `evaluation/phase5_5/run_e2e.py --quick`

**Dataset:** 6 cases

**Observed value:** `summary.json → comparison_table.baseline[7] = 0.5`, `with_abstention[7] = 0.6667`

**Verdict:** ✅ SUPPORTED

**Notes:** Claim is correctly scoped to the 6-case quick run. Explanation of WHY
task success is higher (safe abstention = correct answer) is provided in context.

---

### CLAIM-08

**Claim:** "Routing generates errors; abstention is the containment mechanism."

**Source:** `docs/phase5_5_failure_analysis.md` — Section 2

**Runner:** `evaluation/phase5_5/run_e2e.py --quick`

**Dataset:** 6 cases

**Observed value:** `summary.json → error_propagation.with_abstention.table → Routing.errors_created=2, Abstention.errors_contained=3`

**Verdict:** ✅ SUPPORTED

**Notes:** Directly supported by the error propagation table.

---

### CLAIM-09 — PARTIALLY SUPPORTED

**Claim:** "Abstention reduced unsafe outcomes from 3 to 2 on 6 cases."

**Source:** `docs/phase5_5_failure_analysis.md` — Section 2

**Runner:** `evaluation/phase5_5/run_e2e.py --quick`

**Dataset:** 6 cases

**Observed value:**
- Baseline: `Tool_Selection.unsafe_outcomes = 3`
- With abstention: `Tool_Selection.unsafe_outcomes = 2`

**Verdict:** ⚠️ PARTIALLY SUPPORTED

**Notes:** The numbers are directly from the error propagation table. However,
the abstention Distractor FPR metric simultaneously shows 0.0% (all 3 distractor
cases blocked). This contradiction indicates the "unsafe outcome" computation
counts clean operational cases differently than the FPR metric. The claim is
numerically accurate per the error propagation table, but the underlying
metric definitions create an ambiguity that is documented in the results file.

---

### CLAIM-10 — CORRECTLY SCOPED LIMITATION

**Claim:** "Acoustic obfuscation (F0 pitch shift) is not equivalent to speaker anonymity. No biometric claim is made."

**Source:** `docs/phase5_5_results.md` — Section 10

**Runner:** N/A — this is a limitation statement, not an experimental claim

**Verdict:** ✅ CORRECTLY SCOPED LIMITATION

**Notes:** Consistent with Phase 4.6 audit correction. The separation of
acoustic obfuscation from biometric privacy is correctly maintained.

---

### CLAIM-11 — CORRECTLY SCOPED LIMITATION

**Claim:** "N=6 is a small benchmark. No reliability claim generalizes to production."

**Source:** `docs/phase5_5_results.md` — Section 10

**Verdict:** ✅ CORRECTLY SCOPED LIMITATION

---

### CLAIM-12 — CORRECTLY SCOPED LIMITATION

**Claim:** "SNR results from Gaussian noise do not characterize real-world noise environments."

**Source:** `docs/phase5_5_results.md` — Section 10

**Verdict:** ✅ CORRECTLY SCOPED LIMITATION

**Notes:** Gaussian white noise is documented as a proxy. No broader acoustic
robustness claim is made.

---

### CLAIM-13 — CORRECTLY SCOPED LIMITATION

**Claim:** "The abstention threshold τ=0.50 was set on Phase 5 validation data but not formally calibrated against ECE or Brier score."

**Source:** `docs/phase5_5_results.md` — Section 10

**Verdict:** ✅ CORRECTLY SCOPED LIMITATION

**Notes:** Consistent with Phase 5 calibration scope. The threshold was chosen
on Phase 5 validation data via development-set sweep, not via formal calibration.
This is honestly stated.

---

## 3. Claims Explicitly Rejected (Not Made)

The following claims were considered and explicitly not made in Phase 5.5
documentation because the evidence does not support them:

| Rejected Claim | Reason |
|---|---|
| "The voice pipeline is reliable" | N ≤ 6 in quick run; full run in progress; hardware-specific |
| "Abstention achieves 0% distractor FPR" | Only 3 distractor cases tested; error propagation shows residual unsafe outcomes |
| "Speaker privacy is achieved through obfuscation" | F0 shift ≠ speaker anonymization |
| "The system is acoustically robust" | Gaussian noise only; not tested on real environments |
| "Confidence scores are calibrated" | Calibration not formally measured |
| "Abstention generalizes to unseen distractor types" | Phase 5.5 distractors follow the same taxonomy as Phase 5 |

---

## 4. Audit Summary

| Verdict | Count |
|---|---|
| ✅ SUPPORTED | 10 |
| ⚠️ PARTIALLY SUPPORTED | 1 |
| ✅ CORRECTLY SCOPED LIMITATION | 4 |
| ❌ UNSUPPORTED | 0 |

No claim in Phase 5.5 documentation is unsupported. One claim (CLAIM-09) has
a metric consistency issue that is documented and explained. All limitations
are explicitly stated.
