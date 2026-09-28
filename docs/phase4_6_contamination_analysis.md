# Phase 4.6 — Test-Set Contamination & Rule Decontamination Analysis

**Document Status:** COMPLETE & ENFORCED  
**Target:** `app/services/intent_router.py`  
**Date:** September 28, 2026  

---

## 1. Context & Motivation

During Phase 4 implementation, an independent audit detected that routing heuristics in `app/services/intent_router.py` were iteratively modified in response to test failures on the Challenge Suite and Metamorphic test cases.

Specifically, several regex patterns introduced in commit `13ae6fa` were 1:1 verbatim matches with test inputs rather than general linguistic principles. This constitutes **test set snooping (target contamination)**: optimizing the classifier to pass specific benchmark sentences rather than evaluating natural generalization.

---

## 2. Audit of Suspect Rules & Remediation Decisions

| Pattern in `intent_router.py` | Originating Test Case | Classification | Remediation Decision | Rationale |
| :--- | :--- | :--- | :--- | :--- |
| `r"^(what\s+is\|what's\|explain\|describe)\s+...\b"` | `ch_stt_001`, `ch_stt_002`, `test_metamorphic.py` | **Legitimate General Linguistic Pattern** | **RETAINED & GENERALIZED** | Explanatory/definitional queries (`"What is X"`, `"Explain X"`) are a genuine semantic class of non-retrieval user intents. |
| `r"\b(stands\s+for\|difference\s+between)\b"` | `ch_stt_002`, `ch_stt_003` | **Legitimate General Linguistic Pattern** | **RETAINED** | Definitional and acronym expansion queries are inherently conversational, not database lookups. |
| `r"\b(crushed\|crushing\s+it)\b"` | `ch_adv_001` (*"crushed active customer targets"*) | **Benchmark-Specific Patch** | **REMOVED** | Hyper-specific colloquial idiom. Does not capture other idioms (*"smashed"*, *"flooded"*). |
| `r"\b(flying\s+in)\b"` | `ch_adv_003` (*"Support tickets were flying in"*) | **Benchmark-Specific Patch** | **REMOVED** | Direct 1:1 patch to pass `ch_adv_003`. Brittle and unprincipled. |
| `r"\bresolved\s+all\s+tickets\b"` | `test_metamorphic.py` (*"Support team resolved all tickets today"*) | **Benchmark-Specific Patch** | **REMOVED** | Direct test patch. Replaced by general team narrative pattern. |
| `r"\breally\s+engaged\s+with\b"` | `ch_adv_004` (*"really engaged with our new CRM"*) | **Benchmark-Specific Patch** | **REMOVED** | Pure test patch. |
| `r"\b(launch\|outage\|product)\b.*\b(incredible\|awesome)\b"` | `ch_adv_002`, `ch_adv_003` | **Benchmark-Specific Patch** | **REMOVED** | Tailored specifically to `ch_adv_002` ("product launch were incredible"). |

---

## 3. Decontaminated Routing Architecture

The decontaminated intent router now relies solely on structural and grammatical patterns:

1. **Explanatory / Definitional Interrogatives:**
   ```python
   re.compile(r"^(what\s+is|what's|explain|describe|tell\s+me\s+about|what\s+does)\s+(the\s+meaning\s+of\s+)?(crm|analytics|support|tickets?|active\s+status|engagement)\b", re.IGNORECASE)
   re.compile(r"\b(stands\s+for|what\s+does\s+.*\s+mean|difference\s+between|definition\s+of)\b", re.IGNORECASE)
   re.compile(r"\b(how\s+is\s+.*\s+calculated|what\s+exactly\s+is)\b", re.IGNORECASE)
   ```
2. **Team Internal Activity Narratives:**
   ```python
   re.compile(r"\b(our\s+team|analysts?|sales\s+team|support\s+team)\b.*\b(doing|internally|reviewing|celebrat|praise)\b", re.IGNORECASE)
   ```

Any failure that occurs on the frozen held-out or challenge test sets under this decontaminated rule set is **preserved as an honest empirical result**.
No further edits to `intent_router.py` will be permitted based on test set failures.
