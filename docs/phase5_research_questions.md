# Phase 5 — Research Questions & Experimental Formulation

**Phase:** Phase 5 — Reliability Under Distribution Shift, Abstention & Generalization  
**Status:** ACTIVE  
**Guiding Principle:** Evidence before adjectives.  
**Baseline Anchor:** Phase 4.6 Frozen Baseline (Commit: `02aa494`)  

---

## 1. Context & Motivation

Phase 4.6 established that while deterministic guardrails (correction guard, tool-alignment check, bounded retry) perform with high fidelity, the intent routing layer exhibits a critical failure mode:

> **Lexical Anchoring Vulnerability:** The intent router relies disproportionately on domain vocabulary tokens (`customer`, `ticket`, `active`, `crm`, `metrics`) as sufficient evidence to trigger operational database retrieval, failing to determine whether the sentence expresses an **operational data request** or is merely **conversational, anecdotal, definitional, or metaphorical**.

This causes severe false positive tool executions on conversational distractors (e.g., *"I bought a concert ticket for tomorrow"* $\to$ support ticket lookup; *"Customer feedback was overwhelmingly positive"* $\to$ CRM database query).

Phase 5 investigates whether a principled **evidence-grounded abstention mechanism** can mitigate unsafe executions under distribution shifts, whether the system can distinguish operational imperatives from lexical distractors, and whether reliability gains generalize across unseen distributions without benchmark-specific overfitting.

---

## 2. Formal Research Questions

### RQ1 — Distribution Shift Degradation
> *How does intent-routing reliability degrade as user queries transition across increasing difficulty tiers: from canonical operational requests to linguistic variations, semantic distractors, ambiguous queries, adversarial traps, and true out-of-distribution (OOD) inputs?*

- **Hypothesis:** A purely lexical or token-matching router degrades monotonically and sharply as semantic divergence from the canonical imperative training distribution increases.
- **Evaluation Metric:** Multi-tier degradation curve (Accuracy, False Positive Rate, and Unsafe Execution Rate evaluated per tier).

---

### RQ2 — Semantic Distractor Resistance
> *Can the system reliably distinguish operational requests from sentences that contain identical domain vocabulary but do not express an operational database retrieval intent?*

- **Example Contrast:**
  - Operational: *"Show me the active customers."*
  - Semantic Distractor: *"The active customers attended our annual conference."*
- **Hypothesis:** By decoupling **domain entity detection** from **operational speech-act evidence** (imperative verbs, query framing, retrieval modalities), the system can reject or abstain on distractors without sacrificing operational coverage.
- **Evaluation Metric:** Paired Distractor False Positive Rate (FPR) and Matched-Pair Distinction Rate.

---

### RQ3 — High-Risk Abstention
> *Can an explicit abstention mechanism (`ABSTAIN`) eliminate high-risk false positive tool executions while preserving acceptable coverage of legitimate user requests?*

- **Core Distinction:** Abstaining on an ambiguous or non-operational query (`"I am not confident this is a CRM/support/analytics request"`) is a **safe behavior**, whereas executing the wrong tool and retrieving irrelevant records is an **unsafe action**.
- **Hypothesis:** A dual-signal decision policy (requiring both domain relevance *and* operational intent evidence) allows selective abstention on borderline inputs, reducing unsafe execution risk.
- **Evaluation Metric:** Unsafe Execution Rate, Safe Abstention Rate, and Net Useful Coverage.

---

### RQ4 — Reliability Intervention Generalization
> *Does an evidence-grounded abstention intervention tuned strictly on development and validation data generalize to unseen held-out, challenge, and out-of-distribution datasets without performance degradation?*

- **Hypothesis:** General linguistic framing of operational intent (speech act modality) generalizes broadly, whereas keyword-matching and regex patches overfit to specific vocabularies.
- **Evaluation Metric:** Generalization gap ($\Delta \text{Risk}$, $\Delta \text{FPR}$) between validation and frozen evaluation suites (`held_out_test_v1.jsonl`, `challenge_v1.jsonl`, Phase 5 OOD).

---

### RQ5 — Risk-Coverage Tradeoff
> *What is the empirical Pareto trade-off between coverage (the proportion of requests the system executes automatically) and risk (the proportion of executed actions that are erroneous) as the abstention threshold varies?*

- **Formulation:**
  $$\text{Coverage}(\tau) = \frac{|\{x : \text{confidence}(x) \ge \tau\}|}{N}, \quad \text{Risk}(\tau) = \frac{|\{x : \text{confidence}(x) \ge \tau \land \text{error}(x)\}|}{|\{x : \text{confidence}(x) \ge \tau\}|}$$
- **Evaluation Metric:** Selective Accuracy, Risk-Coverage Curve, and Area Under the Risk-Coverage Curve (AURC).

---

### RQ6 — Pre-Execution Failure Prediction
> *Can pre-execution signals (operational evidence score, domain token density, transcript length, STT log-probabilities, correction indicators) predict whether an automated tool execution will fail before an external database action occurs?*

- **Hypothesis:** Discrepancies between domain token presence and operational verb presence serve as strong pre-execution indicators of false-positive tool calls.
- **Evaluation Metric:** AUROC and AUPRC for failure discrimination, and Pre-Execution Prevention Rate.
