# Phase 5.5 — Data Protocol

## 1. Dataset Overview

The Phase 5.5 benchmark consists of 40 text cases organized across 6 categories,
plus 12 acoustic variants (4 base phrases × 3 SNR levels) in Category E.

All datasets are located under:

```
evaluation/datasets/phase5_5/
├── clean/clean_v1.jsonl                    # Category A — 10 cases
├── semantic_distractors/distractors_v1.jsonl  # Category B — 10 cases
├── ambiguous/ambiguous_v1.jsonl            # Category C — 6 cases
├── linguistic_variation/variation_v1.jsonl # Category D — 6 cases
├── acoustic/acoustic_v1.jsonl             # Category E — 4 base phrases
└── failure_cases/failures_v1.jsonl        # Category F — 6 cases
```

---

## 2. Dataset Independence Rules

**These datasets are independent of Phase 4.6 and Phase 5 evaluation datasets.**

- Phase 4.6 held-out set (`evaluation/datasets/held_out_test/held_out_test_v1.jsonl`) is frozen and untouched.
- Phase 5 evaluation sets (`evaluation/datasets/phase5/`) are frozen and untouched.
- Phase 5.5 datasets contain **no duplicates** from prior evaluation sets.
- Phase 5.5 datasets were created before any E2E evaluation runs were performed.
- No case was added to any dataset after observing a pipeline failure.

---

## 3. Case Schema

Every case in the benchmark follows this schema:

```json
{
  "case_id": "e2e_clean_001",
  "category": "A",
  "reference_text": "What is the current customer engagement score?",
  "expected_action": "EXECUTE",
  "expected_tool": "get_crm_data",
  "notes": "Unambiguous CRM operational request."
}
```

| Field | Type | Description |
|---|---|---|
| `case_id` | string | Unique case identifier (prefix encodes category) |
| `category` | string | A–F category label |
| `reference_text` | string | Ground-truth text used for audio synthesis and WER computation |
| `expected_action` | string | `EXECUTE`, `ABSTAIN`, or `DIRECT` |
| `expected_tool` | string \| null | Required tool if `expected_action == EXECUTE` |
| `notes` | string | Human-readable rationale for the expected label |

---

## 4. Category Definitions

### Category A — Clean Operational (10 cases)

Unambiguous operational commands containing clear domain intent.
Audio is clean (no added noise).

**Expected action:** `EXECUTE`
**Labeling criterion:** A native speaker would unambiguously interpret the
utterance as a request for data from the system.

**Example:**
```json
{
  "case_id": "e2e_clean_001",
  "reference_text": "What is the current customer engagement score?",
  "expected_action": "EXECUTE",
  "expected_tool": "get_crm_data"
}
```

---

### Category B — Semantic Distractors (10 cases)

Sentences containing domain vocabulary (customer, ticket, analytics, data)
but expressing no operational intent. Modeled after the Phase 5 distractor
taxonomy.

**Expected action:** `ABSTAIN`
**Labeling criterion:** The sentence is non-operational; executing a tool
would be incorrect regardless of vocabulary overlap.

**Example:**
```json
{
  "case_id": "e2e_dist_001",
  "reference_text": "I bought a concert ticket for tomorrow.",
  "expected_action": "ABSTAIN",
  "expected_tool": null,
  "notes": "Contains 'ticket' but is purely conversational."
}
```

---

### Category C — Ambiguous (6 cases)

Utterances that are genuinely ambiguous between operational and conversational
intent. These test the boundary of the abstention threshold.

**Expected action:** Labeled `ABSTAIN` for safety (abstaining on ambiguous
input is preferable to unsafe execution).
**Labeling criterion:** Two annotators disagreed, or the sentence admits both
operational and non-operational interpretations.

---

### Category D — Linguistic Variation (6 cases)

Paraphrases, indirect phrasing, and colloquial expressions of legitimate
operational requests. Tests routing generalization beyond canonical phrasings.

**Expected action:** `EXECUTE`
**Labeling criterion:** Despite non-canonical phrasing, operational intent is
clearly present.

---

### Category E — Acoustic (4 base phrases × 3 SNR levels)

4 operationally valid phrases synthesized at three SNR levels by adding
Gaussian noise post-synthesis:

| SNR Level | Label | Noise Description |
|---|---|---|
| 30 dB | Clean-equivalent | Imperceptible noise |
| 20 dB | Moderate noise | Noticeable but intelligible |
| 10 dB | Heavy noise | Significant degradation |

**Noise model:** `numpy.random.normal(0, σ)` where σ is computed to achieve
target SNR. Seed = 42.

**Limitation:** This is Gaussian white noise, not real acoustic environment
noise. Results are not generalized to real-world SNR conditions.

---

### Category F — Known Failure Cases (6 cases)

Cases representative of failure modes identified in Phase 5 analysis —
specifically lexical-anchoring failures where routing misclassified conversational
sentences containing domain vocabulary.

**Expected action:** `ABSTAIN`
**Note:** These cases were constructed from the **pattern** of Phase 5 failures,
not from inspecting Phase 5.5 pipeline runs. They represent new instances of
the same failure mode.

---

## 5. Labeling Protocol

All expected labels were assigned **before any pipeline runs** were performed.
Labels were not changed after observing failures.

Label assignment procedure:
1. Write reference text.
2. Assign expected_action based on the labeling criterion above.
3. If assigning `EXECUTE`, identify expected_tool.
4. Record reasoning in `notes` field.
5. Lock the dataset file.

---

## 6. Audio Generation

Audio is synthesized using `edge-tts` with the voice `en-US-JennyNeural`.

```python
# evaluation/phase5_5/audio_generator.py
await edge_tts.Communicate(text, voice="en-US-JennyNeural").save(output_path)
```

Generated audio is cached under:
```
benchmark_audio/phase5_5_cache/<case_id>_clean.wav
benchmark_audio/phase5_5_cache/<case_id>_obfuscated.wav
```

Category E acoustic variants are cached as:
```
benchmark_audio/phase5_5_cache/<case_id>_snr30.wav
benchmark_audio/phase5_5_cache/<case_id>_snr20.wav
benchmark_audio/phase5_5_cache/<case_id>_snr10.wav
```

Cached files are reused across evaluation runs. If a cache file exists, it is
not regenerated (ensuring identical audio across repeated runs).

---

## 7. STT Caching

To ensure that baseline and intervention modes receive identical transcriptions
(so that any difference is attributable only to the abstention mechanism):

- The orchestrator is called once in baseline mode and once in intervention mode
  **per case**.
- STT is run only once. The transcript is stored in `stt_cache[case_id]` and
  reused for the second mode.
- This is enforced in `evaluation/phase5_5/run_e2e.py` (`E2EPipelineRunner.stt_cache`).

---

## 8. Frozen Datasets (Phase 4.6 and Phase 5)

The following datasets are **frozen and must not be modified**:

| Dataset | Path | SHA256 |
|---|---|---|
| Phase 4.6 held-out | `evaluation/datasets/held_out_test/held_out_test_v1.jsonl` | `82efa536…c9924f7` |
| Phase 4.6 challenge | `evaluation/datasets/challenge/challenge_v1.jsonl` | `0ded94ac…e0ab66` |

Phase 5.5 datasets are not independently SHA256-hashed at this time because they
were not used as tuning targets. They were constructed independently before
evaluation and locked before the E2E runner was executed.
