"""
evaluation/run_final_experiment.py - Master Reproducibility Runner for Phase 4.

Executes the complete research-grade experiment suite with a single command:
1. Held-Out Generalization Evaluation (held_out_test_v1.jsonl)
2. Challenge & Adversarial Stress Evaluation (challenge_v1.jsonl)
3. Ablation Study (quantifying contributions of each Phase 3/4 mechanism)
4. Empirical Acoustic Privacy & Pitch Analysis
5. Audio Perturbation & Robustness Matrix
6. Automated Manifest Generation and Export

Usage:
    python -m evaluation.run_final_experiment [--seed 42] [--quick]
"""
import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from evaluation.provenance import make_run_id, get_git_commit, get_python_version
from evaluation.runners.ablation_runner import run_ablation_study
from evaluation.runners.privacy_acoustic_runner import run_privacy_acoustic_study
from evaluation.runners.robustness_runner import run_robustness_matrix
from app.services.intent_router import classify_intent
from app.services.correction_guard import apply_correction_gate, CorrectionDecision


def evaluate_dataset(dataset_path: Path) -> dict:
    """Evaluates routing and ground-truth alignment on a dataset JSONL."""
    if not dataset_path.exists():
        return {"error": f"Dataset {dataset_path} not found"}

    with open(dataset_path, encoding="utf-8-sig") as f:
        cases = [json.loads(line) for line in f if line.strip()]

    total = len(cases)
    correct = 0
    by_category = {}

    for c in cases:
        cat = c.get("category", "unknown")
        if cat not in by_category:
            by_category[cat] = {"total": 0, "correct": 0}
        by_category[cat]["total"] += 1

        res = classify_intent(c["input_text"])
        is_correct = (res.route == c["expected_route"])
        if is_correct:
            correct += 1
            by_category[cat]["correct"] += 1

    accuracy = correct / max(total, 1)
    category_acc = {
        cat: {
            "total": d["total"],
            "correct": d["correct"],
            "accuracy": round(d["correct"] / max(d["total"], 1), 4),
        }
        for cat, d in by_category.items()
    }

    return {
        "dataset": dataset_path.name,
        "total_cases": total,
        "overall_accuracy": round(accuracy, 4),
        "by_category": category_acc,
    }


def main():
    parser = argparse.ArgumentParser(description="Run Complete Phase 4 Master Experiment Suite")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    parser.add_argument("--output-dir", type=Path, default=Path("experiments/results"), help="Directory for experiment outputs")
    parser.add_argument("--quick", action="store_true", help="Run with reduced matrix for fast verification")
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    master_run_id = make_run_id()
    start_time = time.time()

    print("=" * 80)
    print(f"STARTING PHASE 4 MASTER REPRODUCIBILITY EXPERIMENT")
    print(f"Run ID: {master_run_id} | Seed: {args.seed} | Quick Mode: {args.quick}")
    print("=" * 80)

    # 1. Held-Out Test Set Evaluation
    print("\n[Step 1/5] Evaluating Held-Out Generalization Set...")
    held_out_path = Path("evaluation/datasets/held_out_test/held_out_test_v1.jsonl")
    held_out_results = evaluate_dataset(held_out_path)
    print(f"  Held-Out Accuracy: {held_out_results.get('overall_accuracy', 0):.1%} ({held_out_results.get('total_cases', 0)} cases)")

    # 2. Challenge Set Evaluation
    print("\n[Step 2/5] Evaluating Challenge & Adversarial Set...")
    challenge_path = Path("evaluation/datasets/challenge/challenge_v1.jsonl")
    challenge_results = evaluate_dataset(challenge_path)
    print(f"  Challenge Accuracy: {challenge_results.get('overall_accuracy', 0):.1%} ({challenge_results.get('total_cases', 0)} cases)")

    # 3. Systematic Ablation Study
    print("\n[Step 3/5] Executing Systematic Ablation Study...")
    ablation_results = run_ablation_study(
        dataset_path=held_out_path,
        output_dir=args.output_dir,
        seed=args.seed,
    )

    # 4. Empirical Acoustic Privacy & Pitch Distribution Study
    print("\n[Step 4/5] Running Empirical Acoustic Privacy Profile...")
    acoustic_results = run_privacy_acoustic_study(
        audio_dir=Path("benchmark_audio"),
        output_dir=args.output_dir,
        seed=args.seed,
    )

    # 5. Audio Robustness & Perturbation Matrix
    print("\n[Step 5/5] Running Audio Perturbation & Robustness Matrix...")
    robustness_results = run_robustness_matrix(
        dataset_path=held_out_path,
        output_dir=args.output_dir,
        seed=args.seed,
        quick=args.quick,
    )

    elapsed = round(time.time() - start_time, 2)

    # Master Manifest
    manifest = {
        "master_run_id": master_run_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "elapsed_seconds": elapsed,
        "environment": {
            "run_id": master_run_id,
            "git_commit": get_git_commit(),
            "python_version": get_python_version(),
            "seed": args.seed,
        },
        "held_out_evaluation": held_out_results,
        "challenge_evaluation": challenge_results,
        "ablation_summary": ablation_results.get("conditions", {}),
        "acoustic_privacy_summary": acoustic_results.get("summary", {}),
        "robustness_summary": robustness_results.get("routing_robustness", {}),
    }

    manifest_file = args.output_dir / f"master_experiment_manifest_{master_run_id}.json"
    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    # Latest manifest link
    latest_file = args.output_dir / "master_experiment_manifest_latest.json"
    with open(latest_file, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print("\n" + "=" * 80)
    print("PHASE 4 MASTER EXPERIMENT COMPLETE")
    print(f"Elapsed Time: {elapsed}s")
    print(f"Master Manifest written to: {manifest_file}")
    print(f"Latest Manifest updated at: {latest_file}")
    print("=" * 80)


if __name__ == "__main__":
    main()
