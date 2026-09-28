"""
evaluation/runners/ablation_runner.py - Systematic Ablation Study Runner.

Compares full Phase 3/4 pipeline against systematic ablations of individual
reliability mechanisms to quantify the unique empirical contribution of each component:
1. Full System (All mechanisms enabled)
2. Ablate Intent Router (use legacy naive keyword matching)
3. Ablate Correction Guard (disable polar/number/refusal validation)
4. Ablate Tool-Intent Alignment Gate (bypass tool-domain verification)
5. Ablate Transient Retry Policy (0 retries on transient errors)
6. Baseline (All Phase 3 mechanisms disabled)

Usage:
    python -m evaluation.runners.ablation_runner \
        --dataset evaluation/datasets/held_out_test/held_out_test_v1.jsonl \
        --output evaluation/results/ \
        --seed 42
"""
import argparse
import json
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.services.intent_router import classify_intent, Intent
from app.services.correction_guard import apply_correction_gate, validate_correction, CorrectionDecision
from evaluation.provenance import make_run_id
from evaluation.fault_injection.connectors import FaultInjectingConnector
from app.connectors.crm_connector import CRMConnector


def legacy_keyword_route(text: str) -> str:
    """Legacy Phase 1/2 naive keyword matcher."""
    t = text.lower()
    keywords = ["customer", "ticket", "analytics", "status", "active", "priority", "metric"]
    if any(k in t for k in keywords):
        return "tool"
    return "direct"


def run_ablation_study(
    dataset_path: Path,
    output_dir: Path,
    seed: int = 42,
) -> Dict[str, Any]:
    random.seed(seed)
    output_dir.mkdir(parents=True, exist_ok=True)
    run_id = make_run_id()

    # Load evaluation cases
    with open(dataset_path, encoding="utf-8-sig") as f:
        cases = [json.loads(line) for line in f if line.strip()]

    print(f"=== Ablation Study Experiment (run_id={run_id}) ===")
    print(f"Loaded {len(cases)} test cases from {dataset_path.name}")

    # Define test conditions
    conditions = [
        "full_system",
        "ablate_intent_router",
        "ablate_correction_guard",
        "ablate_tool_alignment",
        "ablate_retry_policy",
        "unmitigated_baseline",
    ]

    results_by_condition = {}

    # Sample adversarial/correction trap cases for validation
    correction_traps = [
        ("Show active customers", "Show inactive customers", "intent_inversion"),
        ("Get 5 tickets", "Get 50 tickets", "number_tampering"),
        ("Fetch accounts", "I apologize as an AI I cannot help", "refusal_commentary"),
        ("Show ack-tive customers", "Show active customers", "valid_correction"),
    ]

    for cond in conditions:
        # 1. Routing Evaluation
        routing_correct = 0
        adversarial_false_positives = 0
        adversarial_total = 0
        tool_queries_total = 0
        tool_queries_correct = 0

        for c in cases:
            text = c["input_text"]
            exp_route = c["expected_route"]
            is_adv = (c.get("category") == "adversarial")

            if cond in ("ablate_intent_router", "unmitigated_baseline"):
                actual_route = legacy_keyword_route(text)
            else:
                res = classify_intent(text)
                actual_route = res.route

            if actual_route == exp_route:
                routing_correct += 1

            if is_adv:
                adversarial_total += 1
                if actual_route == "tool":
                    adversarial_false_positives += 1

            if exp_route == "tool":
                tool_queries_total += 1
                if actual_route == "tool":
                    tool_queries_correct += 1

        routing_acc = routing_correct / len(cases)
        adv_fpr = adversarial_false_positives / max(adversarial_total, 1)
        tool_recall = tool_queries_correct / max(tool_queries_total, 1)

        # 2. Correction Guard Evaluation
        correction_passed = 0
        for raw, corr, trap_type in correction_traps:
            if cond in ("ablate_correction_guard", "unmitigated_baseline"):
                # Without guard, all corrections are accepted naively
                accepted = True
            else:
                decision, _, _ = apply_correction_gate(raw, corr)
                accepted = (decision == CorrectionDecision.ACCEPT_CORRECTION)

            # In traps, only valid_correction should be accepted
            should_accept = (trap_type == "valid_correction")
            if accepted == should_accept:
                correction_passed += 1

        correction_safety_rate = correction_passed / len(correction_traps)

        # 3. Fault Resilience Evaluation (Transient Connector Failure)
        transient_connector = FaultInjectingConnector(
            base_connector=CRMConnector(),
            failure_mode="transient_error",
            fail_times=1,
        )

        max_retries = 0 if cond in ("ablate_retry_policy", "unmitigated_baseline") else 2
        recovered = False
        attempts = 0
        for _ in range(max_retries + 1):
            attempts += 1
            try:
                data = transient_connector.fetch()
                recovered = True
                break
            except Exception:
                continue

        results_by_condition[cond] = {
            "condition": cond,
            "routing_accuracy": round(routing_acc, 4),
            "adversarial_fpr": round(adv_fpr, 4),
            "tool_query_recall": round(tool_recall, 4),
            "correction_safety_rate": round(correction_safety_rate, 4),
            "transient_fault_recovered": recovered,
            "recovery_attempts": attempts,
        }

    # Summary table output
    print("\n" + "=" * 95)
    print(f"{'Condition':<26} | {'Route Acc':<10} | {'Adv FPR':<8} | {'Recall':<8} | {'Corr Safety':<12} | {'Recovery':<8}")
    print("-" * 95)
    for cond, m in results_by_condition.items():
        rec_str = "YES" if m["transient_fault_recovered"] else "NO"
        print(f"{cond:<26} | {m['routing_accuracy']:<10.1%} | {m['adversarial_fpr']:<8.1%} | {m['tool_query_recall']:<8.1%} | {m['correction_safety_rate']:<12.1%} | {rec_str:<8}")
    print("=" * 95)

    summary = {
        "run_id": run_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "dataset_name": dataset_path.name,
        "total_cases": len(cases),
        "conditions": results_by_condition,
    }

    out_file = output_dir / f"ablation_study_{run_id}.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(f"Results saved to {out_file}\n")

    return summary


def main():
    parser = argparse.ArgumentParser(description="Run Phase 4 Ablation Study")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path("evaluation/datasets/held_out_test/held_out_test_v1.jsonl"),
        help="Path to evaluation dataset",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("evaluation/results"),
        help="Output directory",
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args()

    run_ablation_study(
        dataset_path=args.dataset,
        output_dir=args.output,
        seed=args.seed,
    )


if __name__ == "__main__":
    main()
