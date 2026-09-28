# Phase 4.6 — Experimental Reproducibility & Protocol Guide

**Protocol Version:** 1.0.0  
**Verification Date:** September 28, 2026  
**Status:** FULLY REPRODUCIBLE (Deterministic Seed: 42)  

---

## 1. System Requirements & Determinism

All Phase 4.6 experiments are engineered to be 100% reproducible on local commodity hardware without external network or GPU dependencies:

- **OS:** Windows / Linux / macOS (Single-Node CPU)
- **Python:** 3.11+ (Standard Virtual Environment `venv`)
- **Speech-to-Text Model:** OpenAI Whisper (`base.en` or `base`, running in FP32 on CPU)
- **Evaluation Datasets:** Cryptographically locked with SHA256 verification in `evaluation/datasets/manifest.json`
- **Random Seed:** Set explicitly to `42` (`random.seed(42)`, `np.random.seed(42)`)

---

## 2. Single-Command Full Master Reproduction

To execute the entire Phase 4.6 experimental suite in one deterministic pass:

```powershell
.\venv\Scripts\python.exe -m evaluation.run_final_experiment --seed 42 --output-dir experiments/results
```

For quick verification mode (evaluating representative subsets of audio perturbations):

```powershell
.\venv\Scripts\python.exe -m evaluation.run_final_experiment --seed 42 --output-dir experiments/results --quick
```

---

## 3. Individual Experiment Reproduction Commands

### A. Level A: Text Component Evaluation (Held-Out & Challenge)
```powershell
.\venv\Scripts\python.exe -c "
from evaluation.run_final_experiment import run_component_evaluation, verify_frozen_datasets
from pathlib import Path
verify_frozen_datasets(Path('evaluation/datasets/manifest.json'))
ho, _, _ = run_component_evaluation(Path('evaluation/datasets/held_out_test/held_out_test_v1.jsonl'))
ch, _, _ = run_component_evaluation(Path('evaluation/datasets/challenge/challenge_v1.jsonl'))
print(f'Held-Out Accuracy: {ho[\"overall_accuracy\"]:.1%}')
print(f'Challenge Accuracy: {ch[\"overall_accuracy\"]:.1%}')
"
```
**Expected Deterministic Output:**
- `Held-Out Accuracy: 86.7%`
- `Challenge Accuracy: 84.0%`

### B. Reconstructed Architectural Ablation Study
```powershell
.\venv\Scripts\python.exe -m evaluation.runners.ablation_runner --seed 42
```
**Expected Deterministic Output:**
- `full_system`: Route Acc 86.7%, Adv FPR 60.0%, Corr Safe 100.0%, Align Acc 100.0%
- `ablate_intent_router`: Route Acc 80.0%, Adv FPR 100.0%
- `ablate_correction_guard`: Corr Safe 33.3%
- `ablate_tool_alignment`: Align Acc 60.0% (Misaligned executions allowed)
- `ablate_retry_policy`: Recovery NO
- `unmitigated_baseline`: Route Acc 80.0%, Corr Safe 33.3%, Align Acc 60.0%, Recovery NO

### C. Physical Acoustic Robustness Matrix (Real Audio $\to$ Whisper)
```powershell
.\venv\Scripts\python.exe -m evaluation.runners.robustness_runner --seed 42 --quick
```

### D. Physical Acoustic Obfuscation & Pitch Shift Analysis
```powershell
.\venv\Scripts\python.exe -m evaluation.runners.privacy_acoustic_runner --seed 42
```

### E. Oracle-Free Metamorphic Invariant Testing
```powershell
.\venv\Scripts\python.exe -m pytest tests/test_phase4/test_metamorphic.py -v
```
**Expected Result:** 78 passed in ~0.3s.

---

## 4. Generated Artifacts & Traceability

Every evaluation run automatically populates `experiments/results/` with immutable forensic records:

1. `experiments/results/metrics.json`: High-level structured metric matrix.
2. `experiments/results/failures.json`: Comprehensive failure log mapping each failed case to its stage, error code, and ground-truth expectation.
3. `experiments/results/component_results.jsonl`: Raw per-example predictions on held-out and challenge test suites.
4. `experiments/results/pipeline_results.jsonl`: Raw per-example audio pipeline runs tracking WER, CER, latencies, and tool execution status.
5. `experiments/results/config.json`: Hardware, platform, git commit hash, and random seed provenance.
6. `experiments/results/master_experiment_manifest_latest.json`: Unified master manifest linking all experiment components.

---

## 5. Verification of Run 1 == Run 2 Determinism

Because all datasets are cryptographically frozen and all pseudo-random generators use seed 42:
- Two sequential runs of `evaluation/run_final_experiment.py` produce identical predictions across all test cases.
- Any discrepancy indicates an unseeded stochastic component or unauthorized modification of frozen datasets.
