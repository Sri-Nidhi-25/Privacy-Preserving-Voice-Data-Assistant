"""
evaluation/phase5/run_all_experiments.py - Master Orchestrator for Phase 5 Experiments.

Executes and serializes all Phase 5 empirical studies:
1. Baseline reproduction (experiments/phase5/baseline/)
2. Abstention & Risk-Coverage evaluation (experiments/phase5/abstention/)
3. Multi-tier distribution shift study (experiments/phase5/distribution_shift/)
4. Semantic distractor & matched-pair study (experiments/phase5/distractors/)
5. Failure prediction study (experiments/phase5/failure_prediction/)
6. Generalization benchmark (experiments/phase5/generalization/)
"""
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from evaluation.phase5.reproduce_baseline import main as run_baseline
from evaluation.phase5.generalization_eval import run_full_generalization_benchmark
from evaluation.phase5.distribution_shift import run_distribution_shift_study
from evaluation.phase5.distractor_eval import run_distractor_experiments
from evaluation.phase5.failure_prediction import evaluate_failure_predictors
from evaluation.phase5.risk_coverage import compute_risk_coverage_curve, evaluate_selective_metrics
from evaluation.provenance import get_git_commit, get_python_version, make_run_id


def main():
    print("=" * 80)
    print("STARTING PHASE 5 MASTER EMPIRICAL EXPERIMENTS")
    print("=" * 80)
    start_time = time.time()
    exp_base = Path("experiments/phase5")
    exp_base.mkdir(parents=True, exist_ok=True)
    run_id = make_run_id()

    # 1. Baseline Reproduction
    print("\n[Step 1/5] Capturing Phase 5 Baseline...")
    run_baseline()

    # 2. Generalization Benchmark
    print("\n[Step 2/5] Running Generalization Benchmark across all tiers...")
    gen_dir = exp_base / "generalization"
    gen_results = run_full_generalization_benchmark(gen_dir, threshold=0.50)

    # 3. Distribution Shift Study
    print("\n[Step 3/5] Running Multi-Tier Distribution Shift Study...")
    dist_shift_results = run_distribution_shift_study(Path("evaluation/datasets/phase5"))
    shift_dir = exp_base / "distribution_shift"
    shift_dir.mkdir(parents=True, exist_ok=True)
    with open(shift_dir / "results.json", "w", encoding="utf-8") as f:
        json.dump(dist_shift_results, f, indent=2)

    # 4. Semantic Distractor & Matched Pairs Study
    print("\n[Step 4/5] Running Semantic Distractor & Matched-Pair Study...")
    distractor_results = run_distractor_experiments(Path("evaluation/datasets/phase5"))
    dist_dir = exp_base / "distractors"
    dist_dir.mkdir(parents=True, exist_ok=True)
    with open(dist_dir / "results.json", "w", encoding="utf-8") as f:
        json.dump(distractor_results, f, indent=2)

    # 5. Failure Prediction Study
    print("\n[Step 5/5] Running Pre-Execution Failure Prediction Study...")
    failure_pred_paths = [
        Path("evaluation/datasets/phase5/dev/dev_phase5.jsonl"),
        Path("evaluation/datasets/phase5/validation/val_phase5.jsonl"),
        Path("evaluation/datasets/phase5/distractors/distractors_v1.jsonl"),
        Path("evaluation/datasets/phase5/adversarial/adversarial_v1.jsonl"),
        Path("evaluation/datasets/phase5/ambiguity/ambiguity_v1.jsonl"),
    ]
    fail_pred_results = evaluate_failure_predictors(failure_pred_paths)
    fail_dir = exp_base / "failure_prediction"
    fail_dir.mkdir(parents=True, exist_ok=True)
    with open(fail_dir / "results.json", "w", encoding="utf-8") as f:
        json.dump(fail_pred_results, f, indent=2)

    # 6. Abstention & Risk-Coverage Specific Synthesis
    print("\n[Step 6/6] Compiling Abstention Synthesis...")
    abs_dir = exp_base / "abstention"
    abs_dir.mkdir(parents=True, exist_ok=True)
    abstention_synthesis = {
        "run_id": run_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "optimal_threshold": 0.50,
        "generalization_summary": gen_results.get("summaries", {}),
        "distractors_fpr_reduction": {
            "baseline_fpr": distractor_results["distractors_evaluation"]["baseline_fpr"],
            "abstention_fpr": distractor_results["distractors_evaluation"]["abstention_fpr"],
        },
        "matched_pairs_gain": {
            "baseline_accuracy": distractor_results["matched_pairs_evaluation"]["baseline_distinction_accuracy"],
            "abstention_accuracy": distractor_results["matched_pairs_evaluation"]["abstention_distinction_accuracy"],
        },
    }
    with open(abs_dir / "abstention_synthesis.json", "w", encoding="utf-8") as f:
        json.dump(abstention_synthesis, f, indent=2)

    elapsed = round(time.time() - start_time, 2)
    print("\n" + "=" * 80)
    print(f"ALL PHASE 5 EXPERIMENTS COMPLETED IN {elapsed}s")
    print(f"Artifacts preserved in: {exp_base}")
    print("=" * 80)


if __name__ == "__main__":
    main()
