# Phase 5 — Methodology: Evidence-Grounded Abstention & Distribution Shift

**Document Status:** FORMAL RESEARCH METHODOLOGY  
**Phase:** Phase 5 — Reliability Under Distribution Shift, Abstention & Generalization  
**Date:** October 8, 2026  

---

## 1. Architectural Problem Formulation

In Phase 4.6, independent audits proved that entity-grounded intent classification suffered from **lexical anchoring**:
When domain tokens (e.g., `ticket`, `customer`, `analytics`) appeared in conversational, narrative, or metaphorical queries, the router falsely treated lexical presence as sufficient evidence of operational intent.

Phase 5 introduces the **Evidence-Grounded Dual-Signal Model**, decoupling domain entity identification from operational speech-act modality.

---

## 2. Mathematical & Linguistic Formulation

Let an incoming transcript be $x$. The abstention engine decomposes $x$ into three continuous evidence signals:

### 1. Domain Relevance Evidence ($E_{\text{domain}} \in [0.0, 1.0]$)
Measures whether $x$ references entities belonging to supported databases:
$$E_{\text{domain}}(x) = \max \left( \mathbb{I}_{x \in \mathcal{E}_{\text{crm}}}, \mathbb{I}_{x \in \mathcal{E}_{\text{support}}}, \mathbb{I}_{x \in \mathcal{E}_{\text{analytics}}} \right)$$
where $\mathcal{E}$ represents entity concepts (e.g. customers, tickets, user metrics).

### 2. Operational Modality Evidence ($E_{\text{op}} \in [0.0, 1.0]$)
Grounds the request in **Speech-Act Theory** (Searle, 1969). To constitute an operational retrieval request, the user's utterance must express a **directive speech act** targeting the assistant:
- **Directives:** Imperative action verbs directed at the assistant (`show`, `list`, `get`, `fetch`, `retrieve`, `pull up`, `display`, `tabulate`).
- **Data Interrogatives:** Queries examining database state (`are there any`, `how many`, `what is the current count`).
- **Operational Constraints:** Non-default filter parameters (`active`, `inactive`, `open`, `closed`, `high priority`, `days`, `limit`).

$$E_{\text{op}}(x) = \min \left( 1.0, \max(S_{\text{directive}}, S_{\text{interrogative}}) + S_{\text{filter}} \right)$$

### 3. Contextual Distractor Penalty ($D_{\text{dist}} \in [0.0, 1.0]$)
Identifies non-operational framing:
- **Contextual Polysemy:** `concert ticket`, `movie ticket`, `speeding ticket`, `support dog`, `active volcano`.
- **Narrative / Past-Tense Verbs:** `bought`, `attended`, `erupted`, `cheered`, `cracked`.
- **Evaluative Sentiment:** `feedback was positive`, `satisfaction with`, `reviews from`.
- **Non-Retrieval Tasks:** `write a python script`, `draft an apology letter`, `explain the origin of`.

---

## 3. Decision Policy & Risk Calibration

The calibrated operational confidence score $C(x)$ is defined as:
$$C(x) = \begin{cases} 
0.20 \cdot E_{\text{op}}(x) & \text{if } D_{\text{dist}}(x) > 0 \\
0.40 \cdot E_{\text{domain}}(x) + 0.60 \cdot E_{\text{op}}(x) & \text{if } D_{\text{dist}}(x) = 0 
\end{cases}$$

Given an operating threshold $\tau$ (calibrated at $\tau = 0.50$ on validation data):

$$\text{Decision}(x) = \begin{cases}
\text{DIRECT} & \text{if } E_{\text{domain}}(x) = 0 \\
\text{EXECUTE}(T) & \text{if } C(x) \ge \tau \land E_{\text{op}}(x) > 0 \land D_{\text{dist}}(x) = 0 \\
\text{ABSTAIN} & \text{if } E_{\text{domain}}(x) > 0 \land (C(x) < \tau \lor D_{\text{dist}}(x) > 0)
\end{cases}$$

---

## 4. Outcome Classification

To prevent metric conflation, outcomes are formally partitioned:

1. **`CORRECT_EXECUTION`**: Tool was authorized and matched expected tool with valid arguments.
2. **`SAFE_ABSTENTION`**: System abstained on a distractor, ambiguous query, or adversarial trap.
3. **`UNSAFE_EXECUTION`**: System executed a tool on a non-operational query or invoked the wrong domain tool.
4. **`FALSE_ABSTENTION`**: System abstained on a legitimate operational query (lost coverage).

---

## 5. Threshold Calibration Protocol

The operational threshold $\tau = 0.50$ was selected strictly on `validation/val_phase5.jsonl` ($N=20$) by optimizing the objective:
$$\tau^* = \arg\max_\tau \left( \text{Coverage}(\tau) \times (1.0 - \text{Risk}(\tau)) \right)$$
The frozen test sets (`held_out_test_v1.jsonl`, `challenge_v1.jsonl`) were never observed during threshold calibration.
