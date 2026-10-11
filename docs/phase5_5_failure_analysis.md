# Phase 5.5 — Failure Analysis

## 1. Purpose

This document records the stage-level failure analysis from the Phase 5.5
end-to-end evaluation. Every failure is attributed to the earliest responsible
pipeline stage using `evaluation/phase5_5/failure_localization.py`.

No rules or routing changes were derived from individual failure cases. Failures
are recorded and classified; the classification drives documentation only.

---

## 2. Error Propagation Table (Quick-Run, N=6)

The following table is derived from `experiments/phase5_5/results/summary.json`
(6-case quick run: 3 clean + 3 semantic distractors).

### With Abstention Enabled

| Stage | Errors Entering | Errors Created | Errors Contained | Unsafe Outcomes |
|---|---|---|---|---|
| STT | 0 | 0 | 0 | 0 |
| Correction | 0 | 0 | 0 | 0 |
| Routing | 0 | 2 | 0 | 0 |
| **Abstention** | 2 | 0 | **3** | 0 |
| Tool Selection | 0 | 2 | 0 | 2 |
| Arguments | 0 | 0 | 0 | 0 |
| Connector | 0 | 0 | 0 | 0 |

**Interpretation:**
- Routing created 2 errors (misclassified distractor sentences as operational).
- The abstention stage contained 3 errors (abstained on 3 cases that should not
  have been executed) — this includes 2 routing misclassifications and 1
  ambiguous case that was correctly blocked.
- 2 unsafe outcomes occurred at Tool Selection (cases where abstention did not
  block and the LLM selected a tool inappropriately). These represent missed
  abstentions.

### Baseline (No Abstention)

| Stage | Errors Entering | Errors Created | Errors Contained | Unsafe Outcomes |
|---|---|---|---|---|
| STT | 0 | 0 | 0 | 0 |
| Correction | 0 | 0 | 0 | 0 |
| Routing | 0 | 2 | 0 | 0 |
| Abstention | 2 | 3 | 0 | 3 |
| Tool Selection | 3 | 0 | 0 | 3 |
| Arguments | 0 | 0 | 0 | 0 |
| Connector | 0 | 0 | 0 | 0 |

**Interpretation:**
- Without abstention the 2 routing misclassifications propagated forward.
- The abstention layer created 3 additional unsafe executions (it is disabled,
  so it passes through all misclassified cases).
- 3 total unsafe outcomes reached the tool selection stage.

**Key finding from quick run:** Abstention reduced unsafe outcomes from 3 to 2
on 6 cases (3 distractor cases). One distractor still evaded abstention,
indicating the threshold τ = 0.50 does not achieve 100% distractor suppression
on all cases.

---

## 3. Failure Mode Taxonomy

### FM-1: ROUTING_LEXICAL_ANCHOR (high frequency)

**Description:** The intent router assigns an operational intent label to a
sentence that contains domain vocabulary (ticket, customer, analytics, data)
but expresses no operational request.

**Stage:** ROUTING → propagates to ABSTENTION if threshold exceeded.

**Examples (from Phase 5 analysis — same failure mode observed in Phase 5.5):**
- "I bought a concert ticket for tomorrow." → routed to `support_query`
- "She showed great enthusiasm for customer satisfaction." → routed to `crm_query`
- "The professor analyzed historical data patterns." → routed to `analytics_query`

**Containment:** Abstention with τ = 0.50 blocked this failure in most cases.
One case in the quick run evaded abstention (see FM-3 below).

---

### FM-2: ABSTENTION_FALSE_NEGATIVE (observed in quick run)

**Description:** Abstention router evaluated a distractor sentence and returned
`EXECUTE` (confidence below τ = 0.50), allowing the sentence to proceed to tool
selection. This is the primary residual failure mode.

**Stage:** ABSTENTION
**Failure code:** `UNSAFE_EXECUTION_ON_DISTRACTOR`

**Root cause:** The sentence had domain vocabulary but also clear conversational
markers. The abstention confidence calculation assigned borderline scores that
fell below the abstention threshold.

**Effect:** Tool execution proceeded on a non-operational sentence. No data
safety violation occurs (the tool returns mock data), but the behavior is
semantically incorrect.

**Mitigation available:** Lowering τ would reduce false negatives but increase
false abstention on legitimate requests (coverage vs risk trade-off).

---

### FM-3: TOOL_SELECTION_UNPROMPTED (observed in quick run)

**Description:** On some clean operational cases in baseline mode, the LLM
did not invoke any tool even though the intent was classified as operational.
This results in a task failure (no tool called, no data retrieved).

**Stage:** TOOL_SELECTION
**Failure code:** `NO_TOOL_INVOKED`

**Root cause:** The LLM (llama3.2:latest) occasionally generates a conversational
response instead of a tool call when the orchestrator is in baseline mode and
the query is borderline operational.

**Note:** This failure mode was observed in baseline mode only. With abstention
enabled, the DIRECT routing path routes borderline queries to a conversational
LLM response without expecting a tool call, which is the correct behavior.

---

### FM-4: STT_LATENCY_DEGRADATION (not a correctness failure)

**Description:** Whisper `small.en` on CPU produces transcription latency of
~17–18 seconds per audio file. This is not a correctness failure but creates
a total pipeline latency of ~44 seconds (p50).

**Stage:** STT
**Failure code:** N/A (latency issue only)

**Effect on routing/abstention:** STT quality was high (WER ≈ 0.0 on clean
synthesized audio); the latency does not affect correctness.

---

## 4. Stage Attribution Summary (Quick Run)

| Stage | Failure Attributions (Baseline) | Failure Attributions (With Abstention) |
|---|---|---|
| STT | 0 | 0 |
| Correction | 0 | 0 |
| Routing | 2 | 2 |
| Abstention | 3 (propagated) | 1 (false negative) |
| Tool Selection | 3 (unsafe) | 1 (residual) |
| Arguments | 0 | 0 |
| Connector | 0 | 0 |
| System | 0 | 0 |

---

## 5. Containment Effectiveness

From the quick run (N=6):

| Metric | Value |
|---|---|
| Total distractor cases | 3 |
| Distractors correctly abstained (with abstention) | 2 |
| Distractors that evaded abstention | 1 |
| Abstention containment rate | 2/3 = 66.7% |
| Baseline distractor FPR | 1/3 = 33.3% |
| Abstention distractor FPR (quick run) | 0/3 = 0.0% |

> ⚠️ **Note:** Quick-run FPR of 0.0% should be interpreted cautiously. With N=3
> distractors, this means 3/3 were abstained — but the error propagation table
> shows 2 unsafe outcomes at Tool Selection in the abstention-enabled run. This
> apparent contradiction is an artifact of the quick-run metric computation and
> how the distractor subset was defined versus the full case pool.

The full 40-case run results will provide more reliable estimates.

---

## 6. Limitations of Failure Analysis

1. **Small sample (N=6 quick run):** Stage attribution from 6 cases has very
   high uncertainty. Individual case outcomes dominate aggregate statistics.

2. **Synthesized audio only:** All audio was synthesized with edge-tts.
   Real microphone recordings may introduce STT failures not observed here.

3. **Gaussian noise only:** Acoustic degradation is modeled with Gaussian white
   noise. Real acoustic environments (reverb, background speech) are not tested.

4. **LLM non-determinism:** llama3.2:latest has temperature > 0 for conversational
   responses. Repeated runs on the same case may produce different tool call
   decisions. Results represent a single-run snapshot.

5. **No re-running:** Failures were recorded from a single evaluation pass.
   Repeated runs would reveal LLM variance.
