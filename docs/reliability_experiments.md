# Reliability Experiments — Phase 3

This document records the hypothesis-driven reliability interventions implemented during Phase 3, along with their baseline measurements, post-intervention evaluations, and regression analyses.

---

## Experiment 01: Entity-Grounded Intent Routing vs. Keyword Matching

### Problem
In Phase 2 baseline evaluation (`run_id=4269913a`), routing had a **50.0% False Positive Rate (FPR)** on adversarial non-data queries. Five conversational requests were misrouted to tool calling:
- *"My customer service was excellent today"* -> Routed to CRM tool
- *"I want to show my active participation in the meeting"* -> Routed to CRM tool
- *"How many people were at the event"* -> Routed to CRM tool
- *"Get me a glass of water"* -> Routed to CRM tool
- *"Count the number of meetings we had"* -> Routed to CRM tool

**Root Cause:** The legacy `_is_data_query()` used single broad keywords like `get`, `count`, `how many`, `active`, `show me` without requiring a domain entity anchor.

### Hypothesis
Requiring explicit entity anchors (`customers`/`clients`/`accounts`, `tickets`/`issues`, `analytics`/`metrics`/`dau`) and filtering conversational sentiment patterns will reduce routing FPR from 50% to 0% on adversarial queries without reducing tool-calling recall on legitimate data queries.

### Baseline vs Intervention
- **Baseline:** Single-keyword matching (`DATA_KEYWORDS`) in `app/services/llm_orchestrator.py`
- **Intervention:** Entity-grounded intent classifier (`app/services/intent_router.py`) classifying into `CRM_QUERY`, `SUPPORT_QUERY`, `ANALYTICS_QUERY`, `DIRECT`, and `AMBIGUOUS`.

### Results

| Metric | Phase 2 Baseline | Phase 3 Intervention | Delta |
|---|---:|---:|---:|
| **Routing Accuracy** | 83.3% | **100.0%** | **+16.7%** |
| **Precision (tool)** | 80.0% | **100.0%** | **+20.0%** |
| **Recall (tool)** | 100.0% | **100.0%** | **0.0%** |
| **False Positive Rate** | 50.0% | **0.0%** | **-50.0%** |
| **Adversarial FPs** | 5 / 5 | **0 / 5** | **-5** |

### Regression Analysis
Zero regressions. All 20 legitimate data queries remain routed to `tool` (Recall = 100%).

### Decision
**ACCEPTED**.

---

## Experiment 02: Multi-Tier Deterministic Transcript Correction Gate

### Problem
LLM transcript correction (`CORRECTION_PROMPT`) had no semantic guard against:
1. **Polar intent inversion:** Mishearing or hallucinating polar opposites (e.g. `active` -> `inactive`, `open` -> `closed`, `low` -> `high`).
2. **Numerical argument mutation:** Adding, dropping, or altering numeric limits (e.g. `limit 1` -> `limit 100`).
3. **Runaway expansion:** LLM generating conversational apologies or preamble.

### Hypothesis
Applying a multi-tier deterministic validation gate with polar-pair conflict detection, discrete number preservation, and strict length bounds will prevent 100% of adversarial mutations while allowing valid phonetic corrections.

### Baseline vs Intervention
- **Baseline:** Word overlap ratio check (`_word_overlap_ratio < 0.5`) and refusal markers.
- **Intervention:** `app/services/correction_guard.py` implementing `apply_correction_gate()` with:
  - Refusal / conversational commentary detection
  - Length ratio bounds (0.5 <= length <= 1.8)
  - Number preservation (exact set of numbers must match)
  - Polar intent inversion checks (`active`/`inactive`, `open`/`closed`, `low`/`high`)
  - Gate returning explicit `KEEP_RAW` or `ACCEPT_CORRECTION` decisions.

### Results

| Scenario | Proposed Correction | Gate Action | Result |
|---|---|---|---|
| Polar inversion | "Show me active customers" -> "Show me inactive customers" | `KEEP_RAW` | **BLOCKED** |
| Polar inversion | "List open tickets" -> "List closed tickets" | `KEEP_RAW` | **BLOCKED** |
| Number tampering | "Give me 1 ticket" -> "Give me 100 tickets" | `KEEP_RAW` | **BLOCKED** |
| Number invention | "Show me customers" -> "Show me 50 customers" | `KEEP_RAW` | **BLOCKED** |
| Runaway commentary | "List accounts" -> "As an AI model, here is..." | `KEEP_RAW` | **BLOCKED** |
| Phonetic garble fix | "Show me all ack-tive customers" -> "active customers" | `ACCEPT_CORRECTION` | **ACCEPTED** |

- **Adversarial Rejection Rate:** 100% (5/5 blocked)
- **Legitimate Phonetic Acceptance:** 100% (1/1 accepted)

### Decision
**ACCEPTED**.

---

## Experiment 03: STT Confidence Calibration & Decision Matrix

### Problem
Whisper produces three primary acoustic confidence signals: `avg_logprob`, `no_speech_prob`, and `compression_ratio`. The default static thresholds (`-1.0`, `0.6`, `2.4`) had not been calibrated against transcription error (WER) to assess dangerous continuation vs false abstention tradeoffs.

### Hypothesis
Evaluating an empirical decision matrix and computing a bounded logistic `stt_reliability_score` provides measurable calibration connecting acoustic signals to transcription reliability.

### Implementation
- `evaluation/calibration.py`:
  - Normalized `stt_reliability_score` in [0.0, 1.0] using logistic combination.
  - Decision classification: `correct_continuation`, `false_abstention`, `dangerous_continuation`, `correct_abstention`.
  - Grid sweep across `avg_logprob` ([-1.5, -1.25, -1.0, -0.75, -0.5]), `no_speech_prob` ([0.4, 0.6, 0.8]), and `compression_ratio` ([2.0, 2.4, 2.8]).

### Results
- `avg_logprob = -1.0` and `no_speech_prob = 0.6` achieves Brier score = 0.04 on calibration data.
- Dangerous continuation rate is bounded at 0.0% for severe audio corruption.
- Monotonicity verified: high confidence samples produce reliability scores > 0.85; severe corruption produces scores < 0.15.

### Decision
**ACCEPTED**.

---

## Experiment 04: Connector Fault Injection & Zero-Fabrication Guarantee

### Problem
A silent failure in a connector or database query could theoretically result in empty records being treated as a successful empty response (`[]`), masquerading failure as valid business data.

### Hypothesis
Wrapping connectors in a fault injection layer and enforcing an explicit `ConnectorResult.success` invariant ensures that errors are always surfaced with `failure_type='connector_failed'` and zero fabricated data.

### Implementation
- `evaluation/fault_injection/connectors.py`: `FaultInjectingConnector` simulating `timeout`, `exception`, `empty`, `malformed`, `stale`, and `future_timestamp`.
- Hardened `LLMOrchestrator._execute_tool_calls` to inspect `conn_result.success`. If `False`, it returns error metadata and `result_count: 0`.

### Results
- Timeout fault: `success=False`, `error="Simulated connector timeout"`, `failure_type="connector_failed"` -> **Zero fabricated data**.
- Database exception: `success=False`, `error="Simulated connector database failure"`, `failure_type="connector_failed"` -> **Zero fabricated data**.

### Decision
**ACCEPTED**.

---

## Experiment 05: Safe Tool-Call Recovery with Bounded Retries

### Problem
Transient errors (such as network glitches or database lock contention) caused permanent query failures, while deterministic errors (such as invalid parameters) risked infinite retry loops if retried naively.

### Hypothesis
Implementing a retry policy that only retries transient errors up to `MAX_RETRIES=2` will recover transient connector glitches while failing deterministic validation errors immediately without retries.

### Implementation
- `MAX_RETRIES` configuration added to `app/config.py`.
- `_execute_tool_calls` identifies transient errors (`timeout`, `temporary`, `connection`, `locked`) and retries up to 2 times, recording `retry_attempted`, `retry_count`, and `retry_succeeded`.
- Deterministic invalid arguments fail immediately with `invalid_tool_arguments` and `retry_attempted=False`.

### Results
- Transient connection error (fails 1 time, recovers on 2nd attempt):
  - `retry_attempted: True`
  - `retry_count: 1`
  - `retry_succeeded: True`
  - Query completes successfully!
- Deterministic argument failure (`status='invalid_enum'`):
  - `retry_attempted: False`
  - `retry_count: 0`
  - Fails immediately with `invalid_tool_arguments`.

### Decision
**ACCEPTED**.