# Phase 5 — Dataset Hierarchy & Experimental Data Protocol

**Document Status:** ACTIVE & FROZEN  
**Phase:** Phase 5 — Reliability Under Distribution Shift, Abstention & Generalization  
**Creation Date:** October 7, 2026  

---

## 1. Principles of Experimental Partitioning

In accordance with Phase 5 Non-Negotiable Scientific Rules:
1. **Frozen Phase 4.6 Suites Are Untouchable:**
   - `evaluation/datasets/held_out_test/held_out_test_v1.jsonl` (SHA256: `82efa536...`)
   - `evaluation/datasets/challenge/challenge_v1.jsonl` (SHA256: `0ded94ac...`)
   These remain **strictly unobserved during development** and serve exclusively for final generalization measurement.
2. **Phase 5 Data Hierarchy:**
   Phase 5 establishes a dedicated distribution hierarchy to investigate how system reliability degrades under increasing semantic distance from standard imperative operational queries:

```text
evaluation/datasets/phase5/
├── dev/
│   └── dev_phase5.jsonl          # 20 cases: Exploratory development and rule iteration
├── validation/
│   └── val_phase5.jsonl          # 20 cases: Threshold selection & evidence weight calibration
├── distractors/
│   ├── distractors_v1.jsonl      # 20 cases: Semantic distractors across 10 taxonomy classes
│   └── matched_pairs_v1.jsonl    # 10 matched pairs (operational x vs distractor T(x))
├── ambiguity/
│   └── ambiguity_v1.jsonl        # 15 cases: Vague, fragmented, or under-specified queries
├── adversarial/
│   └── adversarial_v1.jsonl      # 15 cases: Domain nouns embedded in deceptive contexts
└── ood/
    └── ood_v1.jsonl              # 15 cases: Genuinely out-of-distribution vocabulary/syntax
```

---

## 2. Difficulty & Distribution Taxonomy (Tiers 0 – 5)

Every evaluation case in Phase 5 is categorized into an explicit difficulty tier:

| Tier | Label | Definition | Example | Expected Action |
| :--- | :--- | :--- | :--- | :--- |
| **Tier 0** | **Normal** | Direct imperative requests targeting canonical operational tooling. | *"Show me active customers."* | `EXECUTE` (`get_crm_data`) |
| **Tier 1** | **Linguistic Variation** | Same operational intent wrapped in politeness, fillers, casing, or contractions. | *"Could you please, um, pull up closed tickets?"* | `EXECUTE` (`get_support_tickets`) |
| **Tier 2** | **Conversational Distractors** | Contains domain vocabulary (`ticket`, `customer`) without operational retrieval intent. | *"I bought a concert ticket for tomorrow evening."* | `ABSTAIN` / `DIRECT` (Safe non-execution) |
| **Tier 3** | **Ambiguous** | Domain mentioned but operation is vague, fragmented, or missing parameters. | *"Tell me about customers."* | `ABSTAIN` (Request clarification) |
| **Tier 4** | **Adversarial** | Sentences constructed to trigger lexical shortcuts (anecdotes, idioms, sentiment). | *"Our sales team crushed active customer targets."* | `ABSTAIN` / `DIRECT` (Prevent false tool call) |
| **Tier 5** | **OOD (Out-of-Distribution)** | Synonyms, indirect searches, or metaphorical phrasings outside development lexicon. | *"Catalog every patron whose membership remains in good standing."* | `EXECUTE` if confident; else `ABSTAIN` |

---

## 3. Matched-Pair Formulation for Distractor Evaluation

To scientifically measure semantic discrimination rather than lexical memorization, the distractor suite includes **10 matched pairs**:
$$x_{\text{op}} = \text{Operational Imperative}, \quad x_{\text{dis}} = \text{Non-Operational Distractor}$$
where both sentences contain the exact same domain noun (e.g. `customer`, `tickets`, `daily active users`).

- **Success Criterion:**
  $$\text{route}(x_{\text{op}}) == \text{TOOL} \quad \land \quad \text{decision}(x_{\text{dis}}) \in \{\text{DIRECT}, \text{ABSTAIN}\}$$
  If the system executes a database tool on $x_{\text{dis}}$, it fails the matched-pair evaluation.
