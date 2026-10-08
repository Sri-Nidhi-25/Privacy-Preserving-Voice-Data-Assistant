"""
evaluation/phase5/distribution_shift.py - Multi-Tier Distribution Shift & Degradation Evaluation.

Evaluates performance across the 6 formal Phase 5 Difficulty Tiers:
- Tier 0: Normal Operational Requests
- Tier 1: Linguistic Variation (Politeness, fillers, casing)
- Tier 2: Conversational Distractors (Domain nouns without operational request)
- Tier 3: Ambiguous Queries (Vague or missing specifications)
- Tier 4: Adversarial Traps (Subtle non-operational narratives)
- Tier 5: Out-Of-Distribution (OOD Synonyms, indirect searches, unusual framing)
"""
import json
from pathlib import Path
from typing import Any, Dict, List

from app.services.intent_router import classify_intent
from app.services.abstention_router import evaluate_abstention, Decision


def evaluate_tier_distribution(
    tier_cases: List[Dict[str, Any]],
    tier_name: str,
) -> Dict[str, Any]:
    total = len(tier_cases)
    if total == 0:
        return {"tier": tier_name, "sample_size": 0}

    # Baseline metrics
    base_correct = 0
    base_fp = 0
    base_fn = 0

    # Abstention metrics
    abs_executed = 0
    abs_correct_exec = 0
    abs_unsafe_exec = 0
    abs_safe_abstain = 0

    for c in tier_cases:
        text = c["input_text"]
        exp_route = c.get("expected_route", "direct")
        exp_tool = c.get("expected_tool")

        # Baseline evaluation
        b_res = classify_intent(text)
        if b_res.route == exp_route:
            base_correct += 1
        elif b_res.route == "tool" and exp_route in ("direct", "abstain"):
            base_fp += 1
        elif b_res.route == "direct" and exp_route == "tool":
            base_fn += 1

        # Abstention evaluation
        a_res = evaluate_abstention(text, threshold=0.50)
        is_exec = (a_res.decision == Decision.EXECUTE)

        if is_exec:
            abs_executed += 1
            if exp_route == "tool" and a_res.target_tool == exp_tool:
                abs_correct_exec += 1
            else:
                abs_unsafe_exec += 1
        else:
            if exp_route in ("direct", "abstain"):
                abs_safe_abstain += 1

    return {
        "tier": tier_name,
        "sample_size": total,
        "baseline_accuracy": round(base_correct / total, 4),
        "baseline_fpr": round(base_fp / total, 4),
        "abstention_coverage": round(abs_executed / total, 4),
        "abstention_unsafe_risk": round(abs_unsafe_exec / max(abs_executed, 1), 4) if abs_executed > 0 else 0.0,
        "abstention_unsafe_rate": round(abs_unsafe_exec / total, 4),
        "abstention_safe_rate": round(abs_safe_abstain / total, 4),
        "delta_unsafe_reduction": round((base_fp - abs_unsafe_exec) / total, 4),
    }


def run_distribution_shift_study(datasets_dir: Path) -> Dict[str, Any]:
    # Group cases by tier from dev, val, distractors, ambiguity, adversarial, ood
    files_to_load = [
        datasets_dir / "dev/dev_phase5.jsonl",
        datasets_dir / "validation/val_phase5.jsonl",
        datasets_dir / "distractors/distractors_v1.jsonl",
        datasets_dir / "ambiguity/ambiguity_v1.jsonl",
        datasets_dir / "adversarial/adversarial_v1.jsonl",
        datasets_dir / "ood/ood_v1.jsonl",
    ]

    tier_bins = {
        "tier_0_normal": [],
        "tier_1_linguistic": [],
        "tier_2_distractor": [],
        "tier_3_ambiguous": [],
        "tier_4_adversarial": [],
        "tier_5_ood": [],
    }

    for fpath in files_to_load:
        if not fpath.exists():
            continue
        with open(fpath, encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                record = json.loads(line)
                t = record.get("tier")
                # Infer tier if not explicitly present
                if not t:
                    if "distractor" in fpath.name: t = "tier_2_distractor"
                    elif "ambiguity" in fpath.name: t = "tier_3_ambiguous"
                    elif "adversarial" in fpath.name: t = "tier_4_adversarial"
                    elif "ood" in fpath.name: t = "tier_5_ood"
                    else: t = "tier_0_normal"

                if t in tier_bins:
                    tier_bins[t].append(record)

    results_by_tier = {}
    for tier_name, cases in tier_bins.items():
        results_by_tier[tier_name] = evaluate_tier_distribution(cases, tier_name)

    return {
        "results_by_tier": results_by_tier,
    }


if __name__ == "__main__":
    base = Path("evaluation/datasets/phase5")
    res = run_distribution_shift_study(base)
    print(json.dumps(res, indent=2))
