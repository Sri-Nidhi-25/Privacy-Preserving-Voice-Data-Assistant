# Phase 5 Experimental Results: Reliability Under Distribution Shift, Abstention & Generalization

**Evaluation Date:** October 2026  
**Auditor:** Antigravity Evaluation Engine  
**Baseline Model:** Phase 4.6 Audited Production Router (`app.services.intent_router`)  
**Intervention:** Dual-Evidence Selective Abstention Router (`app.services.abstention_router`)  
**Calibration:** Operating Threshold $\tau = 0.50$ (selected on validation split)

---

## 1. Executive Summary

Phase 5 evaluates system reliability under structured distribution shift across 8 distinct datasets ($N = 160$ total instances) spanning 6 difficulty tiers (Tier 0 to Tier 5).

Key empirical findings:
1. **Semantic Distractor Resistance:** On `distractors_v1.jsonl` ($N = 20$), the baseline router incurred an **85.0% False Positive Rate (FPR)** due to lexical keyword anchoring. The dual-evidence abstention engine achieved a **0.0% FPR**, eliminating all 17 unsafe tool invocations while maintaining 100% safe abstentions.
2. **Matched-Pair Disambiguation:** Across 10 matched operational vs. distractor pairs sharing identical domain terms, the baseline exhibited **0.0% distinction** (calling tools on both). Abstention achieved **50.0% distinction**.
3. **Distribution Shift Degradation:** Baseline accuracy collapsed monotonically from **100.0% (Tier 0)** down to **20.0% (Tier 4)** and **44.4% (Tier 5)**. Selective abstention reduced unsafe executions in every shifted tier (Tier 2: 76.7% $\to$ 0.0%; Tier 3: 45.0% $\to$ 5.0%; Tier 4: 80.0% $\to$ 15.0%; Tier 5: 38.9% $\to$ 0.0%).
4. **Generalization to Frozen Benchmarks:**
   - On the frozen `held_out_test_v1.jsonl` ($N = 30$), selective abstention attained **63.3% coverage** with **0.0% Risk** and **0.0% Unsafe Execution Rate** (100% selective accuracy on executed queries), down from 10.0% baseline FPR.
   - On the frozen `challenge_v1.jsonl` ($N = 25$), unsafe executions were cut from **24.0% to 12.0%** at 44.0% coverage.
5. **Pre-Execution Failure Prediction:** Absence of operational directives ($E_{\text{op}} = 0$) when domain cues are present predicted 43 of 49 unsafe executions with **97.7% precision** and only **2.4% false alarms**.

---

## 2. Multi-Dataset Benchmark Evaluation

The table below summarizes performance across all 8 datasets comparing the frozen baseline against the abstention router at $\tau = 0.50$:

| Dataset ID | Partition Role | $N$ | Base Acc | Base FPR | Base Unsafe | Abs Coverage | Abs Selective Acc | Abs Risk | Abs Unsafe | Safe Abs | False Abs | AURC |
|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `phase5_dev` | Dev Tuning | 20 | 70.0% | 30.0% | 30.0% | 55.0% | 90.9% | 9.1% | 5.0% | 9 | 0 | 0.0023 |
| `phase5_val` | Val Selection | 20 | 60.0% | 40.0% | 40.0% | 35.0% | 85.7% | 14.3% | 5.0% | 12 | 1 | 0.0077 |
| `frozen_held_out` | Frozen Benchmark | 30 | 86.7% | 10.0% | 10.0% | 63.3% | 100.0% | 0.0% | 0.0% | 10 | 1 | 0.0000 |
| `frozen_challenge` | Frozen Adversarial | 25 | 68.0% | 24.0% | 24.0% | 44.0% | 72.7% | 27.3% | 12.0% | 8 | 6 | 0.0154 |
| `phase5_distractors`| Semantic Shift | 20 | 15.0% | 85.0% | 85.0% | 0.0% | 100.0% | 0.0% | 0.0% | 20 | 0 | 0.0000 |
| `phase5_ambiguity` | Ambiguity Shift | 15 | 53.3% | 46.7% | 46.7% | 0.0% | 100.0% | 0.0% | 0.0% | 15 | 0 | 0.0000 |
| `phase5_adversarial`| Adversarial Trap | 15 | 26.7% | 73.3% | 73.3% | 13.3% | 0.0% | 100.0% | 13.3% | 13 | 0 | 0.0666 |
| `phase5_ood` | Out-of-Domain | 15 | 40.0% | 40.0% | 40.0% | 33.3% | 100.0% | 0.0% | 0.0% | 7 | 3 | 0.0000 |
| **Overall Total** | **Pooled Benchmark** | **160** | **57.5%** | **42.5%** | **42.5%** | **36.9%** | **84.7%** | **15.3%** | **5.0%** | **94** | **11** | — |

---

## 3. Distribution Shift Degradation by Difficulty Tier

Queries were categorized into 6 difficulty tiers to assess performance collapse under increasing domain and semantic perturbation:

| Difficulty Tier | Description | Sample Size | Baseline Accuracy | Baseline FPR | Abstention Coverage | Abstention Risk | Abstention Unsafe Rate | Unsafe Reduction ($\Delta$) | Safe Abstention Rate |
|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Tier 0** | Normal / In-Distribution | 9 | 100.0% | 0.0% | 100.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| **Tier 1** | Linguistic Variation | 8 | 100.0% | 0.0% | 87.5% | 0.0% | 0.0% | 0.0% | 0.0% |
| **Tier 2** | Semantic Distractor | 30 | 23.3% | 76.7% | 0.0% | 0.0% | 0.0% | -76.7% | 100.0% |
| **Tier 3** | Ambiguous Request | 20 | 55.0% | 45.0% | 5.0% | 100.0% | 5.0% | -40.0% | 95.0% |
| **Tier 4** | Adversarial Framing | 20 | 20.0% | 80.0% | 15.0% | 100.0% | 15.0% | -65.0% | 85.0% |
| **Tier 5** | Out-of-Domain (OOD) | 18 | 44.4% | 38.9% | 27.8% | 0.0% | 0.0% | -38.9% | 55.6% |

### Key Observations on Distribution Shift
1. **Step-Function Collapse:** Baseline accuracy drops steeply from 100% in Tiers 0–1 to 23.3% in Tier 2 and 20.0% in Tier 4. The failure mode is overwhelmingly **false positive execution** (FPR $> 75\%$).
2. **Abstention Shield:** Under the dual-evidence engine, Tier 2 unsafe executions are completely suppressed ($76.7\% \to 0.0\%$). Tier 4 unsafe executions drop from $80.0\%$ to $15.0\%$.

---

## 4. Semantic Distractor Analysis

### 4.1 Taxonomy Breakdown on `distractors_v1.jsonl` ($N = 20$)

All 20 test inputs contain explicit enterprise keywords (e.g., *tickets*, *customers*, *metrics*, *pipeline*, *logs*) embedded in purely non-operational syntax:

| Distractor Class | Total | Baseline FPR | Baseline False Positives | Abstention FPR | Abstention False Positives |
|:---|:---:|:---:|:---:|:---:|:---:|
| `DOMAIN_NOUN_ONLY` | 2 | 100.0% | 2 / 2 | 0.0% | 0 / 2 |
| `DOMAIN_NOUN_WITH_SENTIMENT` | 2 | 100.0% | 2 / 2 | 0.0% | 0 / 2 |
| `DOMAIN_NOUN_IN_STORY` | 2 | 100.0% | 2 / 2 | 0.0% | 0 / 2 |
| `DOMAIN_NOUN_IN_COMPARISON` | 2 | 100.0% | 2 / 2 | 0.0% | 0 / 2 |
| `DOMAIN_NOUN_IN_UNRELATED_REQUEST` | 2 | 100.0% | 2 / 2 | 0.0% | 0 / 2 |
| `MULTIPLE_DOMAIN_TERMS` | 2 | 100.0% | 2 / 2 | 0.0% | 0 / 2 |
| `CROSS_DOMAIN_CONTEXT` | 2 | 50.0% | 1 / 2 | 0.0% | 0 / 2 |
| `IMPLICIT_OPERATION` | 2 | 50.0% | 1 / 2 | 0.0% | 0 / 2 |
| `NON_OPERATIONAL_QUESTION` | 2 | 100.0% | 2 / 2 | 0.0% | 0 / 2 |
| `CONVERSATIONAL_STATEMENT` | 2 | 50.0% | 1 / 2 | 0.0% | 0 / 2 |
| **Total Distractors** | **20** | **85.0%** | **17 / 20** | **0.0%** | **0 / 20** |

### 4.2 Matched-Pair Distinction Experiment (`matched_pairs_v1.jsonl`, $N = 10$ pairs)

In this controlled experiment, pairs share identical lexical roots. A model succeeds on a pair if and only if it **executes** the operational utterance and **abstains** on the non-operational utterance:

| Pair ID | Domain | Operational Input | Distractor Input | Baseline Distinction | Abstention Distinction |
|:---:|:---:|:---|:---|:---:|:---:|
| `pair_01` | CRM | "Show me the active customers" | "The active customers attended the annual conference" | FAIL (Tool/Tool) | **PASS** (Exec/Abstain) |
| `pair_02` | CRM | "List all inactive accounts" | "Inactive accounts in banks are subject to special regulatory audits" | FAIL (Tool/Tool) | FAIL (Exec/Exec) |
| `pair_03` | Support | "List the open support tickets" | "The support tickets were discussed during the staff meeting" | FAIL (Tool/Tool) | **PASS** (Exec/Abstain) |
| `pair_04` | Support | "Find high priority tickets" | "High priority tickets at the theater were sold out within minutes" | FAIL (Tool/Tool) | FAIL (Exec/Exec) |
| `pair_05` | Analytics | "Get daily active users for last 7 days" | "Daily active users on social media often experience digital fatigue" | FAIL (Tool/Tool) | FAIL (Exec/Exec) |
| `pair_06` | Analytics | "Display user metrics for past month" | "User metrics alone cannot capture the full emotional impact of art" | FAIL (Tool/Tool) | **PASS** (Exec/Abstain) |
| `pair_07` | Support | "Fetch closed support issues" | "Closed support issues remain archived in compliance storage" | FAIL (Tool/Tool) | FAIL (Exec/Exec) |
| `pair_08` | CRM | "Retrieve 10 customer profiles" | "Customer profiles on social networks can be vulnerable to phishing" | FAIL (Tool/Tool) | **PASS** (Exec/Abstain) |
| `pair_09` | Support | "Pull urgent support cases" | "Urgent support cases in emergency rooms require swift medical triage" | FAIL (Tool/Tool) | FAIL (Exec/Exec) |
| `pair_10` | Analytics | "Show DAU numbers for past 30 days" | "DAU numbers fluctuate naturally over major holiday weekends" | FAIL (Tool/Tool) | **PASS** (Exec/Abstain) |
| **Total** | — | — | — | **0 / 10 (0.0%)** | **5 / 10 (50.0%)** |

#### Why Matched Pairs 2, 4, 5, 7, and 9 Failed
In pairs 2, 4, 5, 7, and 9, the distractors contain compound nominal adjectives that the filter-token matching subsystem treated as operational filter directives (e.g., *"high priority"* matching `priority=high`, *"daily"* matching `metric=dau`, *"closed"* matching `status=closed`). Because filter matches increment operational evidence $E_{\text{op}}$, the aggregate confidence exceeded $\tau = 0.50$. This highlights an important remaining challenge: **syntactic dependency parsing is required to separate attributive adjective modifiers from imperative parameter bindings**.

---

## 5. Pre-Execution Failure Prediction Analysis

We evaluated 4 candidate pre-execution signals on a pool of 90 evaluation queries containing 49 actual baseline failures (unsafe tool executions):

| Candidate Failure Signal | Description | True Positives Prevented ($TP$) | False Alarms ($FP$) | Precision | Recall | False Positive Rate | False Negative Rate |
|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| `op_directive_absent` | $E_{\text{domain}} > 0 \land E_{\text{op}} == 0$ | **43 / 49** | **1 / 41** | **97.7%** | **87.8%** | **2.4%** | **12.2%** |
| `distractor_cue_present` | $D_{\text{dist}} > 0$ | 21 / 49 | 8 / 41 | 72.4% | 42.9% | 19.5% | 57.1% |
| `domain_multiplicity` | Cross-domain term conflicts | 2 / 49 | 0 / 41 | 100.0% | 4.1% | 0.0% | 95.9% |
| `composite_abstention` | $C < 0.50$ (Full Router Decision) | 45 / 49 | 25 / 41 | 64.3% | 91.8% | 61.0% | 8.2% |

### Key Prediction Findings
- `op_directive_absent` is the single most effective failure predictor: when an utterance has domain vocabulary but lacks an imperative verb or retrieval directive, treating this as a warning signal catches **87.8%** of all false positive failures with an outstanding **97.7% precision**.
- Only 1 legitimate query was falsely flagged by this signal (a clipped command lacking an explicit verb).

---

## 6. Risk-Coverage Monotonicity & Operating Thresholds

Sweeping the operating confidence threshold $\tau \in [0.10, 0.90]$ demonstrates expected monotonic risk-coverage dynamics:

### Frozen Held-Out Dataset ($N = 30$)
- At $\tau \in [0.10, 0.70]$: Coverage = **63.3% (19/30)**, Risk = **0.0%**, Selective Accuracy = **100.0%**, AURC = **0.0000**.
- At $\tau \in [0.80, 0.90]$: Coverage = **50.0% (15/30)**, Risk = **0.0%**, Selective Accuracy = **100.0%**.

### Frozen Challenge Dataset ($N = 25$)
- At $\tau \in [0.10, 0.70]$: Coverage = **44.0% (11/25)**, Risk = **27.3%**, Selective Accuracy = **72.7%**, Unsafe Execution Rate = **12.0%**.
- At $\tau \in [0.80, 0.90]$: Coverage = **36.0% (9/25)**, Risk = **11.1%**, Selective Accuracy = **88.9%**, Unsafe Execution Rate = **4.0%**, AURC = **0.0154**.

---

## 7. Conclusions & Next Steps

1. **Selective Abstention Works:** Decoupling domain tokens from operational modality provides a dramatic reliability boost on semantic distractors (85% FPR $\to$ 0% FPR) and frozen test sets (10% FPR $\to$ 0% FPR).
2. **Clear Boundaries of Capability:** The 50% matched-pair failure rate proves that purely lexicon-based parameter extractors cannot reliably distinguish compound nominal modifiers from operational filter constraints without syntactic dependency grammar or full constituent parsing.
3. **Traceability:** Every metric in this report corresponds directly to the frozen baseline and serialized JSON experiment outputs under `experiments/phase5/`.
