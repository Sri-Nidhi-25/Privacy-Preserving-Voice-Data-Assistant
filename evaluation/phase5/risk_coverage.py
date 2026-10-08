"""
evaluation/phase5/risk_coverage.py - Risk-Coverage Trade-Off & Selective Prediction Evaluation.

Formulation (El-Yaniv & Wiener, 2010; Geifman & El-Yaniv, 2017):
  Coverage(tau) = |{x : confidence(x) >= tau}| / N
  Risk(tau)     = |{x : confidence(x) >= tau and error(x)}| / |{x : confidence(x) >= tau}|
  Selective Accuracy(tau) = 1.0 - Risk(tau)

Outcomes:
  - CORRECT_EXECUTION: System executes and choice matches expected tool.
  - SAFE_ABSTENTION:   System abstains on a distractor, ambiguous, or unanswerable query.
  - UNSAFE_EXECUTION:  System executes on a distractor or calls the wrong tool.
"""
from typing import Any, Dict, List, Tuple
import numpy as np


def evaluate_selective_metrics(
    records: List[Dict[str, Any]],
    threshold: float,
) -> Dict[str, float]:
    """
    Computes coverage, selective accuracy, risk, and safe abstention rate at threshold tau.
    """
    total = len(records)
    if total == 0:
        return {"coverage": 0.0, "risk": 0.0, "selective_accuracy": 0.0, "unsafe_execution_rate": 0.0}

    executed = 0
    correct_executions = 0
    unsafe_executions = 0
    safe_abstentions = 0
    false_abstentions = 0

    for r in records:
        conf = r.get("confidence", 0.0)
        exp_route = r.get("expected_route", "direct")
        exp_tool = r.get("expected_tool")
        act_tool = r.get("actual_tool")
        decision = r.get("decision", "EXECUTE" if conf >= threshold else "ABSTAIN")

        is_executed = (decision == "EXECUTE" and conf >= threshold)

        if is_executed:
            executed += 1
            if exp_route == "tool" and act_tool == exp_tool:
                correct_executions += 1
            else:
                unsafe_executions += 1
        else:
            # System abstained or routed direct without tool execution
            if exp_route in ("direct", "abstain"):
                safe_abstentions += 1
            else:
                false_abstentions += 1

    coverage = executed / total
    risk = unsafe_executions / executed if executed > 0 else 0.0
    selective_acc = correct_executions / executed if executed > 0 else 1.0
    unsafe_rate = unsafe_executions / total

    return {
        "threshold": round(threshold, 2),
        "coverage": round(coverage, 4),
        "risk": round(risk, 4),
        "selective_accuracy": round(selective_acc, 4),
        "unsafe_execution_rate": round(unsafe_rate, 4),
        "executed_count": executed,
        "correct_executions": correct_executions,
        "unsafe_executions": unsafe_executions,
        "safe_abstentions": safe_abstentions,
        "false_abstentions": false_abstentions,
    }


def compute_risk_coverage_curve(
    records: List[Dict[str, Any]],
    thresholds: List[float] = None,
) -> Dict[str, Any]:
    """
    Sweeps thresholds from 0.10 to 0.90 to produce the empirical Risk-Coverage curve.
    """
    if thresholds is None:
        thresholds = [0.10, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90]

    curve = []
    coverages = []
    risks = []

    for t in thresholds:
        m = evaluate_selective_metrics(records, threshold=t)
        curve.append(m)
        coverages.append(m["coverage"])
        risks.append(m["risk"])

    # Compute Area Under the Risk-Coverage curve (trapezoidal integration)
    sorted_pairs = sorted(zip(coverages, risks), key=lambda p: p[0])
    cov_sorted = [p[0] for p in sorted_pairs]
    risk_sorted = [p[1] for p in sorted_pairs]

    aurc = 0.0
    for i in range(1, len(cov_sorted)):
        dx = cov_sorted[i] - cov_sorted[i - 1]
        avg_y = (risk_sorted[i] + risk_sorted[i - 1]) / 2.0
        aurc += avg_y * dx

    return {
        "aurc": round(float(aurc), 4),
        "points": curve,
    }
