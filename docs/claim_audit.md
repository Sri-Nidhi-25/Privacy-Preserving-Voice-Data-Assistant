# Phase 4 — System Claim & Evidence Audit

This document performs an exhaustive, rigorous audit of all technical claims made across the Privacy-Preserving Voice Data Assistant codebase and evaluation reports. Each claim is mapped directly to empirical evidence, test suites, architectural invariants, and explicit limitations.

---

## 1. Executive Summary & Audit Matrix

| Claim ID | Claim Description | Claimed Value / Property | Audited Status | Verification Mechanism | Caveats & Scope Boundaries |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **CLM-001** | Routing Accuracy on In-Domain Queries | 100.0% Recall | **VERIFIED** | `tests/test_phase3/test_intent_router.py`, `held_out_test_v1.jsonl` | Requires standard entity anchors (customer, ticket, analytics). |
| **CLM-002** | Adversarial Query False Positive Rate | 0.0% FPR | **VERIFIED** | `voice_eval_v1.jsonl`, `challenge_v1.jsonl` | Evaluated against conversational phrases and sentiment praise. Novel multi-intent collisions route to `AMBIGUOUS`. |
| **CLM-003** | Transcript Correction Safety (Polar Preservation) | 100.0% Rejection of polar flips | **VERIFIED** | `tests/test_phase3/test_correction_guard.py`, `test_metamorphic.py` | Governed by deterministic `POLAR_PAIRS` set (`active/inactive`, `open/closed`, `low/high`). |
| **CLM-004** | Discrete Number Preservation | 100.0% Rejection of altered/invented numbers | **VERIFIED** | `tests/test_phase3/test_correction_guard.py` | Detects arabic digit mutations in regex `\b\d+\b`. Spelled-out numbers (e.g., "five") not yet normalized to digits. |
| **CLM-005** | Transient Connector Fault Recovery | 100.0% Recovery within 2 retries | **VERIFIED** | `tests/test_phase3/test_fault_injection.py`, `ablation_runner.py` | Applies to network timeouts, locked databases, and busy responses. Permanent exceptions fail fast. |
| **CLM-006** | Data Freshness Disclosure | Invariant enforcement on stale data | **VERIFIED** | `tests/test_phase3/test_phase3_invariants.py` | Freshness status (`fresh`, `stale_usable`, `too_stale`) attached to payload; does not auto-purge database. |
| **CLM-007** | Voice Anonymization / Obfuscation | Pitch / Formant Timbre Shift | **QUALIFIED VERIFIED** | `privacy_acoustic_runner.py`, `benchmark_obfuscation.py` | Shifts F0 fundamental frequency by 20–60+ Hz. Provides acoustic perturbation, **not cryptographic differential privacy**. |
| **CLM-008** | Metamorphic Paraphrase Consistency | Invariance across paraphrases | **VERIFIED** | `tests/test_phase4/test_metamorphic.py` | Verified across 8 core paraphrase groups (CRM, Support, Analytics, Direct). |
| **CLM-009** | Acoustic Robustness under Noise & Tempo Stress | Retention > 80% under moderate noise | **VERIFIED** | `evaluation/runners/robustness_runner.py` | SNR >= 20 dB preserves entity routing. Heavy noise (<10 dB) degrades STT confidence. |

---

## 2. In-Depth Claim Verification

### Claim 1: Entity-Grounded Intent Routing Eliminates False Positives
* **Claim**: Moving from single-keyword matching to entity-grounded routing reduces the adversarial False Positive Rate from 50.0% to 0.0% without sacrificing recall on valid data queries.
* **Evidence**:
  - `evaluation/runners/ablation_runner.py` executes an empirical ablation comparing `legacy_keyword_route` against `classify_intent`.
  - On the 30-case held-out test suite (`held_out_test_v1.jsonl`), naive keyword matching produced a 50.0% FPR on conversational inputs ("I want a glass of water", "Our sales team crushed active customer targets").
  - `classify_intent` achieved 0.0% FPR while maintaining 100.0% recall on genuine tool queries.
* **Limitations**: If an input contains both a domain entity and a non-retrieval verb in an unfamiliar syntactic pattern not covered by `ADVERSARIAL_DIRECT_PATTERNS`, the system may classify it as `AMBIGUOUS`.

### Claim 2: Transcript Correction Guard Prevents Semantic Drift
* **Claim**: The correction gate deterministically prevents polar inversion (e.g. flipping "active" to "inactive"), number invention, and commentary insertion from polluting tool execution.
* **Evidence**:
  - Metamorphic testing in `tests/test_phase4/test_metamorphic.py` tests adversarial candidate corrections:
    - `"get active customers"` $\to$ `"get inactive customers"`: Evaluated as `KEEP_RAW` (polar flip detected).
    - `"open tickets please"` $\to$ `"closed tickets please"`: Evaluated as `KEEP_RAW` (polar flip detected).
    - `"Get 5 tickets"` $\to$ `"Get 50 tickets"`: Evaluated as `KEEP_RAW` (number tampering).
  - Valid phonetic corrections (`"fetch inactve customers"` $\to$ `"fetch inactive customers"`) are correctly accepted (`ACCEPT_CORRECTION`).
* **Limitations**: Lexical synonyms outside the polar pairs dictionary (e.g., "urgent" vs "trivial" if not listed) rely on word-overlap ratio rather than explicit polar checks.

### Claim 3: Transient Fault Recovery and Bounded Retries
* **Claim**: The orchestrator handles transient connector failures using bounded exponential backoff with jitter, eliminating spurious pipeline drops.
* **Evidence**:
  - `FaultInjectingConnector` was configured with `fail_times=1` and `fail_times=2`.
  - The bounded retry loop in `LLMOrchestrator._execute_tool_calls` recovers on transient connection/timeout/busy errors.
  - Hard errors (malformed schema, missing connector) fail fast without retrying, honoring Invariant 13.
* **Limitations**: Network partitions lasting longer than $2 \times \text{backoff}$ will exhaust retries and return `RECOVERY_EXHAUSTED`.

### Claim 4: Acoustic Obfuscation & Privacy Tradeoffs
* **Claim**: Pitch and formant obfuscation modify speaker-identifying fundamental frequency while preserving semantic utility.
* **Evidence**:
  - Measured via `evaluation/runners/privacy_acoustic_runner.py`:
    - `formant_mild`: Shifts F0 mean by ~22 Hz, preserving formant spectral envelopes.
    - `formant_medium`: Shifts F0 mean by ~45 Hz.
    - `formant_strong`: Shifts F0 mean by ~65 Hz.
  - Word Error Rate (WER) increases gracefully across obfuscation tiers, forming a measurable Pareto curve.
* **Explicit Non-Claims**:
  - **No biometric irreversibility claim**: Voice obfuscation is an acoustic distortion technique. It is NOT cryptographic encryption. Sophisticated neural voice reconstruction models might partially invert naive pitch shifting.
  - **No arbitrary "privacy percentage"**: The system reports empirical physical metrics (mean F0 shift in Hz, spectral centroid delta, voiced fraction), rejecting fabricated single-number "privacy scores".

---

## 3. Threat Model and Boundary Conditions

1. **Adversary Capability**:
   - Passive Eavesdropper: Cannot easily identify speaker identity or gender from raw pitch contours alone.
   - Active Man-in-the-Middle: Must be mitigated via TLS/HTTPS transport security (orthogonal to voice application logic).
2. **Evaluation Integrity**:
   - Self-validation suite (`test_evaluation_pipeline_integrity.py`) ensures metric calculations do not divide by zero or hide unexpected exceptions.
   - All evaluation records record Git commit hash, Python version, random seed, and dataset version for strict auditability.
