# Phase 4 — Research Experiments & Reproduction Guide

This directory houses the reproduction manifests, experimental configs, and interactive visual dashboards for Phase 4 research evaluation.

---

## 1. Quick Reproduction

To run the complete Phase 4 experimental suite and generate fresh manifests, run:

```bash
# Run complete master experiment suite (deterministic, offline-ready)
python -m evaluation.run_final_experiment --output-dir experiments/results/ --seed 42

# Or run quick verification mode
python -m evaluation.run_final_experiment --output-dir experiments/results/ --seed 42 --quick
```

---

## 2. Directory Layout

```text
experiments/
├── README.md                          <- This document
└── results/
    ├── dashboard.html                 <- Interactive visual report & metric dashboard
    ├── master_experiment_manifest_latest.json <- Full serialized metrics & provenance
    ├── ablation_study_*.json          <- Detailed ablation matrix across 6 conditions
    ├── privacy_acoustic_profile_*.json<- Physical F0 fundamental frequency trajectories
    └── robustness_matrix_*.json       <- Audio perturbation stress evaluations
```

---

## 3. Individual Experiment Modules

You can execute each evaluation component independently:

### A. Generalization & Held-Out Test Evaluation
```bash
python -m evaluation.runners.routing_runner \
    --dataset evaluation/datasets/held_out_test/held_out_test_v1.jsonl \
    --output experiments/results/
```

### B. Systematic Component Ablation
```bash
python -m evaluation.runners.ablation_runner \
    --dataset evaluation/datasets/held_out_test/held_out_test_v1.jsonl \
    --output experiments/results/
```

### C. Empirical Acoustic Privacy Profile
```bash
python -m evaluation.runners.privacy_acoustic_runner \
    --audio-dir benchmark_audio/ \
    --output experiments/results/
```

### D. Environmental Audio Robustness Matrix
```bash
python -m evaluation.runners.robustness_runner \
    --dataset evaluation/datasets/held_out_test/held_out_test_v1.jsonl \
    --output experiments/results/
```

---

## 4. Verification & Testing

To execute all unit, metamorphic, calibration, and pipeline self-validation tests:

```bash
pytest tests/test_phase4/ -v
pytest tests/ -q
```
