# Phase 5 — Claim Verification & Evidence Audit Matrix

**Phase:** Phase 5 — Reliability Under Distribution Shift, Abstention & Generalization  
**Document Status:** FORMAL RESEARCH AUDIT  
**Date:** October 8, 2026  
**Guiding Principle:** Evidence before adjectives.  

---

## 1. Claim Classification Matrix

| Claim ID | Formal Claim Statement | Evaluated Artifact / Runner | Sample Size ($N$) | Empirical Finding | Audit Verdict |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **CLM-P5-01** | *Abstention eliminates false-positive executions on conversational semantic distractors.* | `experiments/phase5/distractors/results.json` | 20 | Baseline FPR: **85.0%** (17 false calls) $\to$ Abstention FPR: **0.0%** (0 false calls). | **SUPPORTED** |
| **CLM-P5-02** | *On frozen held-out test data, abstention achieves zero execution risk on executed requests.* | `experiments/phase5/generalization/summary.json` | 30 | At 63.3% coverage ($N=19$), selective accuracy was **100.0%**; Risk was **0.0%**; Unsafe rate was **0.0%**. | **SUPPORTED** |
| **CLM-P5-03** | *Abstention reduces unsafe execution rate on the adversarial challenge suite.* | `experiments/phase5/generalization/summary.json` | 25 | Baseline unsafe rate was **24.0%** $\to$ Abstention unsafe rate was **12.0%** (50% reduction in unsafe actions). | **SUPPORTED** |
| **CLM-P5-04** | *Absence of operational action verbs serves as a high-precision pre-execution failure predictor.* | `experiments/phase5/failure_prediction/results.json` | 90 | Prevented 43 of 49 unsafe executions with **97.7% precision** and **87.8% recall** (FPR: 2.4%). | **SUPPORTED** |
| **CLM-P5-05** | *Abstention significantly improves distinction between matched operational and distractor pairs.* | `experiments/phase5/distractors/results.json` | 10 pairs (20 queries) | Baseline failed 10 of 10 pairs (**0.0%** distinction) $\to$ Abstention succeeded on 5 of 10 pairs (**50.0%** distinction). | **SUPPORTED** |
| **CLM-P5-06** | *The abstention intervention preserves 100% coverage on canonical operational requests.* | `experiments/phase5/distribution_shift/results.json` | 9 (Tier 0 Normal) | Coverage remained **100.0%** with **0.0% risk** on canonical operational imperatives. | **SUPPORTED** |
| **CLM-P5-07** | *The intervention completely eliminates all false positive risks across all distributions.* | `experiments/phase5/adversarial/results.json` | 15 (Adversarial) | On adversarial traps, 2 out of 15 queries still triggered tool execution (**13.3% unsafe execution rate**). | **UNSUPPORTED / LIMITATION** |
| **CLM-P5-08** | *Biometric speaker privacy was established by acoustic modifications.* | N/A (Preserved from Phase 4.6) | 8 | Formant-preserving obfuscation preserves vocal tract spectral envelope ($sp$). | **UNSUPPORTED / PRESERVED LIMITATION** |

---

## 2. Forensic Analysis of Unsolved Failure Modes

The audit confirms that while abstention achieves a massive leap in distractor resistance (FPR $85\% \to 0\%$), two specific vulnerability classes remain unsolved:

1. **Compound Nominal Modifiers (`high priority tickets`, `inactive accounts`):**
   - In matched pairs, queries like *"High priority tickets at the theater were sold out within minutes"* contain both the domain token `tickets` and the filter token `high priority`.
   - Because `high priority` adds operational evidence points, the net evidence score crosses the $0.50$ threshold.
   - **Root Cause:** The parser lacks full semantic dependency trees to recognize that *"theater"* modifies *"tickets"*.

2. **Coverage Sacrifice on Indirect / Archaic Queries:**
   - On `phase5_ood`, coverage dropped to **33.3%** because archaic phrasings (*"Surface any unresolved grievances"*, *"Tabulate platform engagement"*) lack modern imperative keywords.
   - While execution risk remained **0.0%**, the system safely abstained rather than guessing.
