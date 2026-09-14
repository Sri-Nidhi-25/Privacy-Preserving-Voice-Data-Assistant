"""
evaluation/metrics/routing.py - Routing accuracy metrics.

Routing is a binary classification: "tool" or "direct".
Positive class = "tool" (we care about false positives = unnecessary tool calls).
"""
from typing import List, Optional, Tuple


def _safe_div(a: float, b: float, default: float = 0.0) -> float:
    return a / b if b else default


def routing_metrics(
    expected_routes: List[str],
    actual_routes: List[str],
) -> dict:
    """
    Compute routing accuracy, precision, recall, F1, FPR, FNR.

    Positive class = "tool".
    TP: expected tool, got tool
    FP: expected direct, got tool  (false positive tool call)
    TN: expected direct, got direct
    FN: expected tool, got direct  (missed tool call)
    """
    assert len(expected_routes) == len(actual_routes), "Lengths must match"

    tp = fp = tn = fn = 0
    correct = 0
    for exp, act in zip(expected_routes, actual_routes):
        if exp == act:
            correct += 1
        if exp == "tool" and act == "tool":
            tp += 1
        elif exp == "direct" and act == "tool":
            fp += 1
        elif exp == "direct" and act == "direct":
            tn += 1
        elif exp == "tool" and act == "direct":
            fn += 1

    n = len(expected_routes)
    precision = _safe_div(tp, tp + fp)
    recall = _safe_div(tp, tp + fn)
    f1 = _safe_div(2 * precision * recall, precision + recall)
    fpr = _safe_div(fp, fp + tn)   # false positive rate
    fnr = _safe_div(fn, fn + tp)   # false negative rate

    return {
        "accuracy": round(correct / n, 4) if n else 0.0,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "false_positive_rate": round(fpr, 4),
        "false_negative_rate": round(fnr, 4),
        "tp": tp, "fp": fp, "tn": tn, "fn": fn,
        "n": n,
        "correct": correct,
    }
