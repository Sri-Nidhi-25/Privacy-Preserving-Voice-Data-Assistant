"""
evaluation/metrics/correction.py - Transcript correction ablation metrics.

Measures whether transcript correction helps or hurts downstream reliability.

A correction is:
  IMPROVED   when corrected WER < raw WER (correction moved closer to ground truth)
  DEGRADED   when corrected WER > raw WER (correction moved further from ground truth)
  UNCHANGED  when corrected WER == raw WER (same or no correction applied)

False Correction Rate = degraded / (improved + degraded + unchanged)
"""
from typing import List, Optional


def correction_classification(
    raw_wer: float,
    corrected_wer: float,
    correction_attempted: bool,
) -> str:
    """Return 'improved', 'degraded', 'unchanged', or 'not_attempted'."""
    if not correction_attempted:
        return "not_attempted"
    if abs(corrected_wer - raw_wer) < 1e-6:
        return "unchanged"
    if corrected_wer < raw_wer:
        return "improved"
    return "degraded"


def correction_ablation_metrics(records: List[dict]) -> dict:
    """
    Accepts a list of EvalRecord dicts.
    Measures correction impact across the dataset.
    """
    attempted = [r for r in records if r.get("correction_attempted")]
    n_total = len(records)
    n_attempted = len(attempted)
    n_accepted = sum(1 for r in attempted if r.get("correction_accepted"))
    n_rejected = sum(1 for r in attempted if r.get("correction_rejected"))
    n_changed = sum(1 for r in attempted if r.get("correction_changed"))

    # Measure outcome where both WER values available
    measurable = [
        r for r in attempted
        if r.get("stt_wer") is not None and r.get("corrected_wer") is not None
    ]
    n_measurable = len(measurable)

    improved = [r for r in measurable if r["corrected_wer"] < r["stt_wer"] - 1e-6]
    degraded = [r for r in measurable if r["corrected_wer"] > r["stt_wer"] + 1e-6]
    unchanged_m = [r for r in measurable if abs(r["corrected_wer"] - r["stt_wer"]) <= 1e-6]

    avg_improvement = (
        sum(r["stt_wer"] - r["corrected_wer"] for r in improved) / len(improved)
        if improved else 0.0
    )
    avg_degradation = (
        sum(r["corrected_wer"] - r["stt_wer"] for r in degraded) / len(degraded)
        if degraded else 0.0
    )

    # Routing accuracy comparison: raw vs corrected
    raw_routing = [r for r in records if r.get("actual_route") is not None]
    routing_acc_overall = (
        sum(1 for r in raw_routing if r.get("routing_correct")) / len(raw_routing)
        if raw_routing else None
    )

    def _safe_rate(n, d):
        return round(n / d, 4) if d else None

    return {
        "n_total": n_total,
        "n_correction_attempted": n_attempted,
        "n_correction_accepted": n_accepted,
        "n_correction_rejected": n_rejected,
        "n_correction_changed": n_changed,
        "attempt_rate": _safe_rate(n_attempted, n_total),
        "acceptance_rate": _safe_rate(n_accepted, n_attempted),
        "rejection_rate": _safe_rate(n_rejected, n_attempted),
        "n_measurable_corrections": n_measurable,
        "n_improved": len(improved),
        "n_degraded": len(degraded),
        "n_unchanged": len(unchanged_m),
        "improvement_rate": _safe_rate(len(improved), n_measurable),
        "degradation_rate": _safe_rate(len(degraded), n_measurable),
        "unchanged_rate": _safe_rate(len(unchanged_m), n_measurable),
        "false_correction_rate": _safe_rate(len(degraded), n_measurable),
        "avg_wer_improvement_when_improved": round(avg_improvement, 4) if improved else None,
        "avg_wer_degradation_when_degraded": round(avg_degradation, 4) if degraded else None,
        "routing_accuracy": routing_acc_overall,
    }
