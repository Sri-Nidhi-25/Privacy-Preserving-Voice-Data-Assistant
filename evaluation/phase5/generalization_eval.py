"""
evaluation/phase5/generalization_eval.py - Master Generalization & Abstention Benchmark for Phase 5.

Executes baseline vs abstention comparison across all 8 development, validation, frozen, and OOD datasets:
1. phase5_dev (N=20)
2. phase5_val (N=20)
3. frozen_held_out (N=30, SHA256 verified)
4. frozen_challenge (N=25, SHA256 verified)
5. phase5_distractors (N=20)
6. phase5_ambiguity (N=15)
7. phase5_adversarial (N=15)
8. phase5_ood (N=15)

Outputs:
  - experiments/phase5/generalization/summary.json
  - experiments/phase5/generalization/raw_evaluations.jsonl
  - experiments/phase5/generalization/failures.json
  - experiments/phase5/generalization/risk_coverage_curves.json
"""
import argparse
import json
import platform
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

from app.services.intent_router import classify_intent
from app.services.abstention_router import evaluate_abstention, Decision
from evaluation.phase5.failure_analysis import classify_failure_cause
from evaluation.phase5.risk_coverage import evaluate_selective_metrics, compute_risk_coverage_curve
from evaluation.provenance import get_git_commit, get_python_version, make_run_id
from evaluation.run_final_experiment import verify_frozen_datasets


DATASET_REGISTRY = [
    {"id": "phase5_dev", "path": Path("evaluation/datasets/phase5/dev/dev_phase5.jsonl"), "tier_type": "development"},
    {"id": "phase5_val", "path": Path("evaluation/datasets/phase5/validation/val_phase5.jsonl"), "tier_type": "validation"},
    {"id": "frozen_held_out", "path": Path("evaluation/datasets/held_out_test/held_out_test_v1.jsonl"), "tier_type": "frozen_test"},
    {"id": "frozen_challenge", "path": Path("evaluation/datasets/challenge/challenge_v1.jsonl"), "tier_type": "frozen_test"},
    {"id": "phase5_distractors", "path": Path("evaluation/datasets/phase5/distractors/distractors_v1.jsonl"), "tier_type": "distractors"},
    {"id": "phase5_ambiguity", "path": Path("evaluation/datasets/phase5/ambiguity/ambiguity_v1.jsonl"), "tier_type": "ambiguity"},
    {"id": "phase5_adversarial", "path": Path("evaluation/datasets/phase5/adversarial/adversarial_v1.jsonl"), "tier_type": "adversarial"},
    {"id": "phase5_ood", "path": Path("evaluation/datasets/phase5/ood/ood_v1.jsonl"), "tier_type": "ood"},
]


def evaluate_dataset_comparison(dataset_path: Path, dataset_id: str, threshold: float = 0.50) -> Tuple[Dict[str, Any], List[Dict], List[Dict]]:
    with open(dataset_path, encoding="utf-8-sig") as f:
        cases = [json.loads(line) for line in f if line.strip()]

    raw_records = []
    failures = []

    # Counters
    base_correct = 0
    base_fp = 0
    base_fn = 0
    total = len(cases)

    # Abstention records for selective prediction
    abs_eval_records = []

    for c in cases:
        case_id = c.get("case_id")
        text = c["input_text"]
        exp_route = c.get("expected_route", "direct")
        exp_tool = c.get("expected_tool")

        # 1. Baseline Router
        base_res = classify_intent(text)
        base_ok = (base_res.route == exp_route)
        if base_ok:
            base_correct += 1
        elif base_res.route == "tool" and exp_route in ("direct", "abstain"):
            base_fp += 1
        elif base_res.route == "direct" and exp_route == "tool":
            base_fn += 1

        # 2. Phase 5 Abstention Router
        abs_res = evaluate_abstention(text, threshold=threshold)

        record = {
            "dataset_id": dataset_id,
            "case_id": case_id,
            "input_text": text,
            "expected_route": exp_route,
            "expected_tool": exp_tool,
            "baseline_route": base_res.route,
            "baseline_tool": base_res.target_tool,
            "baseline_correct": base_ok,
            "abstention_route": abs_res.route,
            "abstention_decision": abs_res.decision.value,
            "abstention_confidence": abs_res.confidence,
            "abstention_domain_evidence": abs_res.domain_evidence,
            "abstention_operational_evidence": abs_res.operational_evidence,
            "abstention_distractor_penalty": abs_res.distractor_penalty,
            "abstention_tool": abs_res.target_tool,
            "abstention_reason": abs_res.reason,
        }
        raw_records.append(record)

        abs_eval_records.append({
            "confidence": abs_res.confidence,
            "expected_route": exp_route,
            "expected_tool": exp_tool,
            "actual_tool": abs_res.target_tool,
            "decision": abs_res.decision.value,
        })

        # Classify failures
        if not base_ok:
            cause = classify_failure_cause(text, exp_route, base_res.route, exp_tool, base_res.target_tool)
            failures.append({
                "dataset_id": dataset_id,
                "case_id": case_id,
                "system": "baseline",
                "failure_code": cause,
                "input_text": text,
                "expected": {"route": exp_route, "tool": exp_tool},
                "observed": {"route": base_res.route, "tool": base_res.target_tool},
            })

        # Unsafe execution in abstention system
        if abs_res.decision == Decision.EXECUTE:
            if not (exp_route == "tool" and abs_res.target_tool == exp_tool):
                cause = classify_failure_cause(text, exp_route, "tool", exp_tool, abs_res.target_tool)
                failures.append({
                    "dataset_id": dataset_id,
                    "case_id": case_id,
                    "system": "abstention_intervention",
                    "failure_code": cause,
                    "input_text": text,
                    "expected": {"route": exp_route, "tool": exp_tool},
                    "observed": {"route": "tool", "tool": abs_res.target_tool},
                })

    # Compute selective prediction metrics
    sel_metrics = evaluate_selective_metrics(abs_eval_records, threshold=threshold)
    rc_curve = compute_risk_coverage_curve(abs_eval_records)

    summary = {
        "dataset_id": dataset_id,
        "sample_size": total,
        "baseline": {
            "accuracy": round(base_correct / max(total, 1), 4),
            "false_positive_rate": round(base_fp / max(total, 1), 4),
            "false_negative_rate": round(base_fn / max(total, 1), 4),
            "unsafe_execution_rate": round(base_fp / max(total, 1), 4),
        },
        "abstention_intervention": {
            "coverage": sel_metrics["coverage"],
            "risk": sel_metrics["risk"],
            "selective_accuracy": sel_metrics["selective_accuracy"],
            "unsafe_execution_rate": sel_metrics["unsafe_execution_rate"],
            "safe_abstentions": sel_metrics["safe_abstentions"],
            "false_abstentions": sel_metrics["false_abstentions"],
            "aurc": rc_curve["aurc"],
        },
        "risk_coverage_curve": rc_curve["points"],
    }
    return summary, raw_records, failures


def run_full_generalization_benchmark(output_dir: Path, threshold: float = 0.50) -> Dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    run_id = make_run_id()
    start_time = time.time()

    # 1. Verify frozen datasets
    manifest_path = Path("evaluation/datasets/manifest.json")
    dataset_verification = verify_frozen_datasets(manifest_path)

    all_summaries = {}
    all_raw = []
    all_failures = []

    print("\n" + "=" * 105)
    print(f"PHASE 5 GENERALIZATION & ABSTENTION BENCHMARK (run_id={run_id})")
    print(f"{'Dataset':<22} | {'N':<4} | {'Base Acc':<9} | {'Base FPR':<9} | {'Abs Cov':<9} | {'Abs Risk':<9} | {'Unsafe Rate':<11}")
    print("-" * 105)

    for entry in DATASET_REGISTRY:
        d_id = entry["id"]
        d_path = entry["path"]
        if not d_path.exists():
            continue

        summary, raw_recs, fails = evaluate_dataset_comparison(d_path, d_id, threshold=threshold)
        all_summaries[d_id] = summary
        all_raw.extend(raw_recs)
        all_failures.extend(fails)

        b = summary["baseline"]
        a = summary["abstention_intervention"]
        print(f"{d_id:<22} | {summary['sample_size']:<4} | {b['accuracy']:<9.1%} | {b['false_positive_rate']:<9.1%} | {a['coverage']:<9.1%} | {a['risk']:<9.1%} | {a['unsafe_execution_rate']:<11.1%}")

    print("=" * 105 + "\n")

    elapsed = round(time.time() - start_time, 2)

    meta = {
        "run_id": run_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "elapsed_seconds": elapsed,
        "git_commit": get_git_commit(),
        "python_version": get_python_version(),
        "platform": platform.platform(),
        "threshold": threshold,
        "dataset_verification": dataset_verification,
        "summaries": all_summaries,
    }

    # Save outputs
    with open(output_dir / "summary.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    with open(output_dir / "raw_evaluations.jsonl", "w", encoding="utf-8") as f:
        for r in all_raw:
            f.write(json.dumps(r) + "\n")

    with open(output_dir / "failures.json", "w", encoding="utf-8") as f:
        json.dump({"total_failures": len(all_failures), "failures": all_failures}, f, indent=2)

    return meta


if __name__ == "__main__":
    out = Path("experiments/phase5/generalization")
    run_full_generalization_benchmark(out, threshold=0.50)
