"""
evaluation/phase5/failure_prediction.py - Pre-Execution Failure Prediction & Signal Evaluation.

Evaluates whether pre-execution signals can predict downstream unsafe tool execution
before an external action occurs:
- Signal 1: Operational Directive Absence (Domain noun present without action verb)
- Signal 2: Semantic Distractor Cue Presence (Narrative/idiomatic cues detected)
- Signal 3: Multi-Domain Conflict (Conflicting entities detected)
- Composite: Net Evidence Gap (Confidence < Threshold)

Metrics:
  - Precision, Recall, FPR, FNR
  - Unsafe Executions Prevented vs False Abstentions (Coverage Lost)
"""
import json
from pathlib import Path
from typing import Any, Dict, List

from app.services.intent_router import classify_intent
from app.services.abstention_router import evaluate_abstention, Decision


def evaluate_failure_predictors(dataset_paths: List[Path]) -> Dict[str, Any]:
    all_cases = []
    for p in dataset_paths:
        if not p.exists():
            continue
        with open(p, encoding="utf-8") as f:
            all_cases.extend([json.loads(line) for line in f if line.strip()])

    total = len(all_cases)
    # Ground truth: Is baseline execution UNSAFE? (i.e. baseline executes tool when it should not)
    ground_truth_unsafe = []
    signals = {
        "op_directive_absent": [],
        "distractor_cue_present": [],
        "domain_multiplicity": [],
        "composite_abstention": [],
    }

    for c in all_cases:
        text = c["input_text"]
        exp_route = c.get("expected_route", "direct")
        b_res = classify_intent(text)

        # Ground truth: Did the baseline perform an unsafe execution?
        is_unsafe = (b_res.route == "tool" and exp_route in ("direct", "abstain"))
        ground_truth_unsafe.append(is_unsafe)

        # Inspect pre-execution signals via abstention engine
        a_res = evaluate_abstention(text, threshold=0.50)

        sig_op_absent = (a_res.domain_evidence > 0 and a_res.operational_evidence == 0)
        sig_distractor = (a_res.distractor_penalty > 0)
        sig_multi_domain = (len(a_res.matched_domains) > 1)
        sig_composite = (a_res.decision != Decision.EXECUTE)

        signals["op_directive_absent"].append(sig_op_absent)
        signals["distractor_cue_present"].append(sig_distractor)
        signals["domain_multiplicity"].append(sig_multi_domain)
        signals["composite_abstention"].append(sig_composite)

    total_unsafe = sum(1 for u in ground_truth_unsafe if u)
    total_safe = total - total_unsafe

    results = {}
    for sig_name, preds in signals.items():
        tp = sum(1 for p, u in zip(preds, ground_truth_unsafe) if p and u)
        fp = sum(1 for p, u in zip(preds, ground_truth_unsafe) if p and not u)
        tn = sum(1 for p, u in zip(preds, ground_truth_unsafe) if not p and not u)
        fn = sum(1 for p, u in zip(preds, ground_truth_unsafe) if not p and u)

        precision = tp / max(tp + fp, 1) if (tp + fp) > 0 else 0.0
        recall = tp / max(total_unsafe, 1)
        fpr = fp / max(total_safe, 1)
        fnr = fn / max(total_unsafe, 1)

        results[sig_name] = {
            "total_evaluated": total,
            "actual_unsafe_executions": total_unsafe,
            "true_positives_prevented": tp,
            "false_positives_false_alarms": fp,
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "false_positive_rate": round(fpr, 4),
            "false_negative_rate": round(fnr, 4),
        }

    return {
        "dataset_sample_size": total,
        "actual_unsafe_rate_in_sample": round(total_unsafe / max(total, 1), 4),
        "predictor_evaluations": results,
    }


if __name__ == "__main__":
    paths = [
        Path("evaluation/datasets/phase5/dev/dev_phase5.jsonl"),
        Path("evaluation/datasets/phase5/validation/val_phase5.jsonl"),
        Path("evaluation/datasets/phase5/distractors/distractors_v1.jsonl"),
        Path("evaluation/datasets/phase5/adversarial/adversarial_v1.jsonl"),
        Path("evaluation/datasets/phase5/ambiguity/ambiguity_v1.jsonl"),
    ]
    res = evaluate_failure_predictors(paths)
    print(json.dumps(res, indent=2))
