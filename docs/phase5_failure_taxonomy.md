# Phase 5 — Failure Mode Taxonomy & Root Cause Classification

**Phase:** Phase 5 — Reliability Under Distribution Shift, Abstention & Generalization  
**Document Status:** FORMAL RESEARCH TAXONOMY  
**Date:** October 7, 2026  

---

## 1. Principles of Causal Failure Analysis

In traditional software evaluation, an error is merely recorded as a binary mismatch ($\hat{y} \ne y$). In reliability engineering, we require **causal classification**:
> *Why did the system fail, at what architectural stage did the failure originate, and what mechanism could prevent it?*

Phase 5 defines 10 formal failure codes across the end-to-end voice assistant pipeline:

```text
Input Speech / Text
      │
      ▼
[STT / Correction Layer]  ──▶ TRANSCRIPT_ERROR / CORRECTION_FAILURE
      │
      ▼
[Intent Routing Layer]    ──▶ LEXICAL_ANCHORING / SEMANTIC_DISTRACTOR /
      │                       DOMAIN_AMBIGUITY / MISSING_OPERATION
      ▼
[Argument Schema Layer]   ──▶ MISSING_ARGUMENT / CROSS_DOMAIN_CONFUSION
      │
      ▼
[Execution & Gate Layer]  ──▶ TOOL_ALIGNMENT_FAILURE / OTHER
```

---

## 2. Failure Code Definitions

| Failure Code | Description | Architectural Stage | Example Root Cause |
| :--- | :--- | :--- | :--- |
| **`LEXICAL_ANCHORING`** | The presence of a domain keyword triggers an operational tool route despite non-retrieval context. | Intent Routing | *"I bought a concert ticket for tomorrow"* triggering `get_support_tickets`. |
| **`SEMANTIC_DISTRACTOR`** | A sentence matches one of the 10 Distractor Taxonomy classes and is falsely routed to an operational database tool. | Intent Routing | *"Customer feedback was positive"* triggering `get_crm_data`. |
| **`DOMAIN_AMBIGUITY`** | Query mentions multiple competing domains without clear priority, or is too vague to assign a single tool safely. | Intent Routing | *"Tickets and customer data update"* triggering single arbitrary tool without abstaining. |
| **`MISSING_OPERATION`** | A query mentions a domain entity as a bare topic without any retrieval verb or action intent. | Intent Routing / Evidence Gate | *"Tell me about customers"* executing `get_crm_data` instead of answering conversationally. |
| **`MISSING_ARGUMENT`** | An operational tool is invoked, but required non-default arguments (e.g. date range for analytics) are completely absent. | Argument Extraction | *"Display analytics overview"* failing schema validation during connector fetch. |
| **`CROSS_DOMAIN_CONFUSION`** | Routing correctly identifies Domain A, but downstream LLM attempts to call Tool B from an unrelated domain. | Tool Selection | Routing to `CRM_QUERY` but LLM invokes `get_support_tickets`. |
| **`TRANSCRIPT_ERROR`** | High Word Error Rate (WER) or phoneme corruption by ASR alters critical entity tokens beyond recognition. | Speech-to-Text (STT) | *"List open tickets"* transcribed as *"Let's open cricket"*. |
| **`CORRECTION_FAILURE`** | Transcript correction either hallucinated a polar reversal or failed to fix a recognizable domain typo. | Correction Guard | *"Fetch inactve custumers"* failing to route because typo was uncorrected. |
| **`TOOL_ALIGNMENT_FAILURE`** | A tool execution is attempted that violates the Intent-Tool Alignment Gate. | Alignment Gate | `get_analytics` executed when intent was classified as `SUPPORT_QUERY`. |
| **`OTHER`** | Infrastructure timeouts, transient network drops, or unhandled exceptions. | Connector / Platform | Database SQLite file lock or connection reset. |
