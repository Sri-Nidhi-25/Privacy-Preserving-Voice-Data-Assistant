# Evaluation Data Protocol & Dataset Freeze Policy

**Protocol Status:** ACTIVE & ENFORCED  
**Freeze Date:** September 28, 2026  
**Manifest:** `evaluation/datasets/manifest.json`  

---

## 1. Principles of Experimental Separation

To ensure scientific integrity and prevent data leakage, evaluation datasets are partitioned into four functionally isolated tiers:

```text
┌─────────────────────────────────────────────────────────────┐
│ 1. Development Set (dev/dev_v1.jsonl)                       │
│    • Iterative rule authoring, debugging, error inspection  │
│    • Prompt engineering & failure analysis                  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Validation Set (validation/validation_v1.jsonl)          │
│    • Decision threshold sweeps (avg_logprob, no_speech)     │
│    • Selection between candidate interventions              │
└─────────────────────────────────────────────────────────────┘
                              │
                   [STRICT FREEZE BOUNDARY]
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. Held-Out Test Set (held_out_test/held_out_test_v1.jsonl) │
│    • Evaluated ONLY after all rules/models are frozen       │
│    • Never used for error-driven rule modifications         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. Adversarial Challenge Set (challenge/challenge_v1.jsonl) │
│    • Out-of-distribution boundary and attack vectors        │
│    • Preserved failures represent persistent limitations    │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Dataset Roles & Non-Negotiable Rules

1. **Development Set (`evaluation/datasets/dev/dev_v1.jsonl`):**
   - **Role:** Active workspace for identifying edge cases, testing parser heuristics, and refining models.
   - **Status:** Unfrozen.
   - **Rule:** Failure on this set may legitimately prompt rule refinements.

2. **Validation Set (`evaluation/datasets/validation/validation_v1.jsonl`):**
   - **Role:** Statistical calibration of confidence thresholds (e.g. STT abstention cutoff $\tau$).
   - **Status:** Frozen.
   - **Rule:** Rules must not be hardcoded to match specific validation sentences.

3. **Held-Out Test Set (`evaluation/datasets/held_out_test/held_out_test_v1.jsonl`):**
   - **Role:** Objective measurement of generalization to unseen phrasing.
   - **Status:** **STRICTLY FROZEN**.
   - **Rule:** **Zero target modification permitted.** If the system scores 86.7%, that score must be reported honestly. Developers may not inspect held-out failures and add matching regex rules.

4. **Challenge Set (`evaluation/datasets/challenge/challenge_v1.jsonl`):**
   - **Role:** Stress testing against intentional semantic contradictions, boundary values, and typos.
   - **Status:** **STRICTLY FROZEN**.
   - **Rule:** Failures on the challenge set document scientific boundaries and must remain unpatched.

---

## 3. Cryptographic Hashes (Tamper Evident)

All frozen evaluation files are tracked by SHA256 cryptographic hashes:

| Dataset Tier | Relative Path | Case Count | SHA256 Checksum |
| :--- | :--- | :--- | :--- |
| **Dev** | `evaluation/datasets/dev/dev_v1.jsonl` | 30 | `1f881eed2fd710edca69755be15aee450f06b2b3798b12a76fd5f39b5ac3d4cb` |
| **Validation** | `evaluation/datasets/validation/validation_v1.jsonl` | 12 | `4844b091a30c09457ad45824e6a5ea9dfd4f4843dab7a1e816e099dc84aaa349` |
| **Held-Out Test** | `evaluation/datasets/held_out_test/held_out_test_v1.jsonl` | 30 | `82efa536759a51819176d576aa168ad12c03be7ac0db3487985457791c9924f7` |
| **Challenge** | `evaluation/datasets/challenge/challenge_v1.jsonl` | 25 | `0ded94acbe7bd6e3c050990b3073d989e3ab0b30678c92a2b4b59dd727e0ab66` |

CI test suites verify that test files match these hashes before running evaluation passes. Any file modification triggers a test failure.
