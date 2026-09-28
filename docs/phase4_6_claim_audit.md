# Phase 4.6 — Evaluation Claim Verification & Classification Audit

**Document Status:** ACTIVE & ENFORCED  
**Audited Targets:** `docs/final_evaluation_report.md`, `experiments/results/dashboard.html`, `README.md`  
**Classification Taxonomy:**
- `SUPPORTED`: Claim directly substantiated by valid, executed, reproducible experimental artifacts.
- `PARTIALLY_SUPPORTED`: True under narrow conditions, but overgeneralized or missing error bars.
- `UNSUPPORTED`: Claim contradicted by empirical data or reliant on invalid proxy simulations.
- `OUTDATED`: Historical assertion superseded by Phase 4.6 findings.

---

## 1. Classification Master Matrix

| ID | Exact Claim Text / Assertion | Document Source | Audit Classification | Empirical Evidence / Counter-Evidence | Action Taken |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **CLM-01** | *"Held-Out Routing Accuracy: 100.0% overall accuracy across 30 previously unseen queries."* | `final_evaluation_report.md` §1 | **UNSUPPORTED** | Real executed runner on `held_out_test_v1.jsonl` yields **26/30 = 86.67%** (4 failures). | Corrected claim to 86.7% across all documents. |
| **CLM-02** | *"0.0% False Positive Rate on conversational distractors."* | `final_evaluation_report.md` §1 | **UNSUPPORTED** | On held-out adversarial distractors ($N=5$), 3 failed (`ho_adv_001`, `002`, `005`). Real FPR is **60.0%**. | Corrected claim to 60.0% FPR. Documented entity anchor fragility. |
| **CLM-03** | *"Challenge Set Resilience: 100.0% intentional routing alignment across 25 queries."* | `final_evaluation_report.md` §1 | **UNSUPPORTED** | Real executed runner yields **21/25 = 84.00%** (4 failures: `ch_stt_004`, `ch_bnd_006`, `ch_trp_001`, `ch_trp_003`). | Corrected claim to 84.0% across all documents. |
| **CLM-04** | *"F0 fundamental frequency shift provides speaker privacy on the Pareto frontier."* | `final_evaluation_report.md` §3.3 | **UNSUPPORTED** | $F_0$ shift (~27 Hz) does not disguise speaker identity against neural biometrics (ECAPA-TDNN). Formant-preserving obfuscation preserves vocal tract spectral envelope ($sp$), leaving identity cues intact. | Reclassified to "Acoustic Obfuscation Analysis". Stated explicitly: *Speaker privacy was not empirically established.* |
| **CLM-05** | *"Ablating tool alignment gate isolates tool-domain consistency."* | `final_evaluation_report.md` §3.2 | **OUTDATED / FORMERLY UNSUPPORTED** | Previously, `ablate_tool_alignment` was a no-op placeholder. | Rebuilt `ablation_runner.py` with genuine tool-intent gate isolation, exposing a 40.0% misaligned execution rate when ablated. |
| **CLM-06** | *"Metamorphic testing proves paraphrase behavioral invariance."* | `final_evaluation_report.md` §2.1 | **OUTDATED / FORMERLY UNSUPPORTED** | Previously, tests checked $f(x) == \text{oracle}$. | Rebuilt `test_metamorphic.py` to check 78 oracle-free relational transformations ($f(T(x)) \equiv f(x)$). Now **SUPPORTED**. |
| **CLM-07** | *"Master reproducibility runner evaluates voice agent end-to-end."* | `run_final_experiment.py` | **OUTDATED / FORMERLY UNSUPPORTED** | Previously, runner passed raw strings directly to `classify_intent()`. | Rebuilt runner to explicitly separate Level A (Text Component) from Level B (Real Speech Audio $\to$ STT $\to$ Tool Execution). Now **SUPPORTED**. |
| **CLM-08** | *"Voice pipeline is robust to physical noise across SNR levels."* | `final_evaluation_report.md` §3.4 | **OUTDATED / FORMERLY UNSUPPORTED** | Previously, noise was simulated by deleting words in strings. | Rebuilt `robustness_runner.py` to run real audio through physical Gaussian noise and actual Whisper STT. Now **SUPPORTED**. |
| **CLM-09** | *"Correction guard prevents polar intent inversion (active/inactive, open/closed)."* | `docs/claim_audit.md` §2 | **SUPPORTED** | Verified in `test_correction_guard.py` and `test_metamorphic.py` across all polar pairs. | Retained as verified invariant (INV-12). |
| **CLM-10** | *"Bounded exponential backoff recovers transient connector failures."* | `docs/claim_audit.md` §2 | **SUPPORTED** | Verified via `FaultInjectingConnector(mode='transient_error')` recovering within 2 retries. | Retained as verified invariant (INV-13). |

---

## 2. Summary of Adjustments Made for Scientific Integrity

1. **All perfection claims (100.0%) revoked:** The true numbers are now recorded in all reporting:
   - Level A Held-Out Generalization: **86.7%**
   - Level A Challenge Suite: **84.0%**
   - Held-Out Adversarial False Positive Rate: **60.0%**
2. **Decontamination applied:** Benchmark-specific regex patches were purged from `app/services/intent_router.py`. All 8 persistent failure cases are preserved in `experiments/results/failures.json`.
3. **Privacy claim retracted:** The project reports physical $F_0$ pitch transformation and vocal envelope preservation, explicitly disclaiming cryptographic or biometric speaker anonymity.
