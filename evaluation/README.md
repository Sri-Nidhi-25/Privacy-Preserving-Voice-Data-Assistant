# Evaluation Framework

**Privacy-Preserving Voice Data Assistant — Phase 2**

This directory contains all evaluation code, datasets, and results for the
reliability benchmarking framework.

---

## Quick Start

```bash
# Routing heuristic evaluation (no audio, no LLM — runs in <5 seconds)
python -m evaluation.run_eval --runner routing --skip-llm --seed 42

# Routing + LLM tool-calling evaluation (requires Ollama running)
python -m evaluation.run_eval --runner routing --seed 42

# Transcript correction ablation (requires Ollama)
python -m evaluation.run_eval --runner correction --seed 42

# STT transcription quality (requires Whisper + edge-tts)
python -m evaluation.run_eval --runner transcription --seed 42 [--max-cases 10]

# Obfuscation benchmark — all 7 methods (requires Whisper + edge-tts)
python -m evaluation.run_eval --runner obfuscation --seed 42

# Full end-to-end pipeline (requires Whisper + Ollama + edge-tts)
python -m evaluation.run_eval --runner e2e --seed 42

# All text-only evaluations (routing + correction)
python -m evaluation.run_eval --runner all-text --seed 42
```

---

## Structure

```
evaluation/
├── datasets/
│   ├── README.md                # Dataset format documentation
│   └── voice_eval_v1.jsonl      # 30-case evaluation dataset (v1)
├── metrics/
│   ├── transcription.py         # WER, CER (custom implementation, no jiwer dependency)
│   ├── routing.py               # Accuracy, precision, recall, F1, FPR, FNR
│   ├── tool_calling.py          # Tool selection + argument field accuracy
│   ├── correction.py            # Correction ablation: improvement/degradation/false rate
│   ├── end_to_end.py            # Strict task success + failure stage taxonomy
│   └── privacy.py               # Placeholder (pending Phase 3 speaker verification)
├── runners/
│   ├── routing_runner.py        # Text-only routing + optional LLM tool-call test
│   ├── correction_runner.py     # Correction ablation (text input)
│   ├── transcription_runner.py  # WER/CER from TTS-synthesized audio
│   ├── obfuscation_runner.py    # 7-method obfuscation Pareto benchmark
│   └── end_to_end_runner.py     # Full pipeline: audio → STT → LLM → answer
├── reporting/
│   ├── aggregate.py             # Latency percentiles, reliability report printer
│   ├── tables.py                # Failure matrix + examples tables
│   └── export.py                # JSON/CSV/JSONL output with timestamped run dirs
├── results/                     # Created at runtime; one subdir per run
├── schemas.py                   # EvalRecord dataclass (common result schema)
├── provenance.py                # run_id, git_commit, Python version metadata
├── run_eval.py                  # Unified CLI entrypoint
├── benchmark_obfuscation.py     # Legacy benchmark (preserved as reference)
└── README.md                    # This file
```

---

## Baseline Results (Routing Heuristic — `_is_data_query()`)

Run: seed=42, dataset=voice_eval_v1.jsonl v1, skip-llm=true

| Metric | Value |
|---|---|
| Accuracy | **83.3%** |
| Precision (tool) | 80.0% |
| Recall (tool) | **100%** — no missed tool calls |
| F1 | 88.9% |
| False Positive Rate | **50.0%** — adversarial queries misclassified as tool |
| TP / FP / TN / FN | 20 / 5 / 5 / 0 |

**Key finding:** The routing heuristic never misses a data query (FNR=0%), but
classifies 5 out of 10 adversarial phrases (e.g. "My customer service was
excellent") as tool queries (FPR=50%). This is a known limitation of
keyword-based routing.

---

## Dataset

- **30 cases**, categories: `data_query` (13), `non_data_query` (5), `adversarial` (5), `ambiguous` (2), `stt_sensitive` (3), `boundary` (2)
- **Tools covered:** `get_crm_data`, `get_support_tickets`, `get_analytics`
- **Ground truth:** manually authored, independent of `_is_data_query()`

See [`datasets/README.md`](datasets/README.md) for format spec.

---

## Result Format

Every run creates `evaluation/results/<timestamp>_<run_id>/`:

```
metadata.json    — reproducibility metadata (git_commit, seed, models, dataset version)
summary.json     — all aggregate metrics for the run
cases.jsonl      — one EvalRecord per case with all stage-level detail
results.csv      — flattened CSV version of cases.jsonl
```

---

## Evaluation Methodology

See [`docs/evaluation_methodology.md`](../docs/evaluation_methodology.md) for:
- WER/CER formulas and text normalization
- Routing binary classification metrics
- Argument semantic equality definition
- End-to-end strict success definition
- Failure stage taxonomy
- Privacy evaluation status and what it means

---

## Tests

```bash
# Run all evaluation framework tests (86 tests, ~0.4s, no audio/LLM needed)
python -m pytest tests/test_evaluation/ -v
```

---

## Evaluation Questions This Framework Can Answer

| Question | Runner |
|---|---|
| How reliable is transcription (WER/CER)? | `transcription` |
| Does STT confidence correlate with WER? | `transcription` |
| Does the router correctly distinguish data vs. non-data queries? | `routing` |
| What is the false positive rate (unnecessary tool calls)? | `routing` |
| Does transcript correction improve or degrade routing? | `correction` |
| What fraction of corrections make things worse? | `correction` |
| Which obfuscation setting preserves the most utility (WER)? | `obfuscation` |
| What is the Pareto tradeoff between obfuscation strength and accuracy? | `obfuscation` |
| What percentage of complete voice tasks succeed end-to-end? | `e2e` |
| Where do failures occur (which stage)? | `e2e` |
| What is end-to-end latency at p50/p90/p99? | `e2e` |

---

## What This Framework Does NOT Claim

- Privacy protection (privacy metric is `not_yet_measured` — Phase 3)
- That evaluation results will hold for different audio environments or accents
- That the 30-case dataset is exhaustive
- That improving benchmark metrics means the system is production-ready