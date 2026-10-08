"""
evaluation/phase5/distractor_eval.py - Semantic Distractor Resistance & Matched-Pair Evaluation.

Evaluates system capability to distinguish operational database requests from sentences
that contain domain vocabulary but express non-operational or conversational intent.
"""
import json
from pathlib import Path
from typing import Any, Dict, List

from app.services.intent_router import classify_intent
from app.services.abstention_router import evaluate_abstention, Decision


def evaluate_distractor_dataset(distractor_path: Path) -> Dict[str, Any]:
    """
    Evaluates baseline router vs Phase 5 abstention router on distractors_v1.jsonl.
    """
    with open(distractor_path, encoding="utf-8") as f:
        cases = [json.loads(line) for line in f if line.strip()]

    baseline_false_positives = 0
    abstention_false_positives = 0
    abstention_safe_count = 0
    by_class_baseline = {}
    by_class_abstention = {}

    for c in cases:
        text = c["input_text"]
        tax_class = c.get("taxonomy_class", "GENERAL")

        if tax_class not in by_class_baseline:
            by_class_baseline[tax_class] = {"total": 0, "false_positives": 0}
            by_class_abstention[tax_class] = {"total": 0, "false_positives": 0, "safe_abstentions": 0}

        by_class_baseline[tax_class]["total"] += 1
        by_class_abstention[tax_class]["total"] += 1

        # 1. Baseline router
        base_res = classify_intent(text)
        if base_res.route == "tool":
            baseline_false_positives += 1
            by_class_baseline[tax_class]["false_positives"] += 1

        # 2. Phase 5 Abstention router
        abs_res = evaluate_abstention(text, threshold=0.50)
        if abs_res.decision == Decision.EXECUTE:
            abstention_false_positives += 1
            by_class_abstention[tax_class]["false_positives"] += 1
        else:
            abstention_safe_count += 1
            by_class_abstention[tax_class]["safe_abstentions"] += 1

    total = len(cases)
    return {
        "dataset": distractor_path.name,
        "sample_size": total,
        "baseline_fpr": round(baseline_false_positives / total, 4),
        "baseline_false_positives": baseline_false_positives,
        "abstention_fpr": round(abstention_false_positives / total, 4),
        "abstention_false_positives": abstention_false_positives,
        "safe_abstention_rate": round(abstention_safe_count / total, 4),
        "by_taxonomy_class": {
            k: {
                "total": by_class_baseline[k]["total"],
                "baseline_fpr": round(by_class_baseline[k]["false_positives"] / by_class_baseline[k]["total"], 4),
                "abstention_fpr": round(by_class_abstention[k]["false_positives"] / by_class_abstention[k]["total"], 4),
            }
            for k in by_class_baseline
        },
    }


def evaluate_matched_pairs(pairs_path: Path) -> Dict[str, Any]:
    """
    Evaluates 10 matched pairs (operational x vs distractor T(x)) containing identical domain words.
    """
    with open(pairs_path, encoding="utf-8") as f:
        pairs = [json.loads(line) for line in f if line.strip()]

    baseline_distinctions = 0
    abstention_distinctions = 0
    pair_results = []

    for p in pairs:
        op_text = p["operational"]
        dis_text = p["distractor"]
        expected_tool = p["op_tool"]

        # Baseline
        base_op = classify_intent(op_text)
        base_dis = classify_intent(dis_text)
        base_ok = (base_op.route == "tool" and base_dis.route == "direct")
        if base_ok:
            baseline_distinctions += 1

        # Abstention
        abs_op = evaluate_abstention(op_text, threshold=0.50)
        abs_dis = evaluate_abstention(dis_text, threshold=0.50)
        abs_ok = (abs_op.decision == Decision.EXECUTE and abs_dis.decision != Decision.EXECUTE)
        if abs_ok:
            abstention_distinctions += 1

        pair_results.append({
            "pair_id": p["pair_id"],
            "domain": p["domain"],
            "operational_text": op_text,
            "distractor_text": dis_text,
            "baseline_operational_route": base_op.route,
            "baseline_distractor_route": base_dis.route,
            "baseline_distinction_success": base_ok,
            "abstention_operational_decision": abs_op.decision.value,
            "abstention_distractor_decision": abs_dis.decision.value,
            "abstention_distinction_success": abs_ok,
        })

    total = len(pairs)
    return {
        "dataset": pairs_path.name,
        "pairs_count": total,
        "baseline_distinction_accuracy": round(baseline_distinctions / total, 4),
        "abstention_distinction_accuracy": round(abstention_distinctions / total, 4),
        "pairs": pair_results,
    }


def run_distractor_experiments(base_dir: Path) -> Dict[str, Any]:
    dis_file = base_dir / "distractors/distractors_v1.jsonl"
    pair_file = base_dir / "distractors/matched_pairs_v1.jsonl"

    dis_results = evaluate_distractor_dataset(dis_file)
    pair_results = evaluate_matched_pairs(pair_file)

    return {
        "distractors_evaluation": dis_results,
        "matched_pairs_evaluation": pair_results,
    }


if __name__ == "__main__":
    base = Path("evaluation/datasets/phase5")
    res = run_distractor_experiments(base)
    print(json.dumps(res, indent=2))
