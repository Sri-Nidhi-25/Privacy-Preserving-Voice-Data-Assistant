"""
evaluation/calibration.py - STT confidence calibration and threshold optimization.

Phase 3 calibration framework:
  1. Computes decision matrices (correct continuation, false abstention, dangerous continuation, correct abstention).
  2. Implements a bounded STT reliability score.
  3. Performs threshold sweeps over (avg_logprob, no_speech_prob, compression_ratio).
  4. Evaluates Brier score, precision, recall, and F1 for bad-transcription detection.
"""
import math
from typing import Dict, List, Optional, Tuple


def compute_stt_reliability_score(
    avg_logprob: Optional[float],
    no_speech_prob: Optional[float],
    compression_ratio: Optional[float],
) -> float:
    """
    Computes a continuous reliability score in [0.0, 1.0] from Whisper acoustic signals.
    High score -> high confidence / low error likelihood.
    Low score -> high error likelihood / abstain.
    """
    if avg_logprob is None:
        return 0.0

    lp = max(-3.0, min(0.0, avg_logprob))
    nsp = max(0.0, min(1.0, no_speech_prob or 0.0))
    cr = max(1.0, min(3.5, compression_ratio or 1.5))

    # Logistic combination calibrated against Whisper empirical distributions:
    # lp: centered around -0.8 (penalty for values < -0.8)
    # nsp: penalty for values > 0.3
    # cr: penalty for repetitive/collapsed loops (> 2.0)
    z = 2.0 * (lp + 0.8) - 4.0 * (nsp - 0.3) - 1.5 * (cr - 1.8)
    # Sigmoid
    score = 1.0 / (1.0 + math.exp(-z))
    return round(score, 4)


def evaluate_decision(
    wer: float,
    avg_logprob: float,
    no_speech_prob: float,
    compression_ratio: float,
    logprob_threshold: float = -1.0,
    no_speech_threshold: float = 0.6,
    compression_threshold: float = 2.4,
    bad_wer_threshold: float = 0.3,
) -> Dict:
    """
    Evaluates system abstention decision against ground-truth WER:
      - is_bad_stt: WER > bad_wer_threshold
      - system_abstained: any confidence metric breaches threshold
    """
    is_bad_stt = (wer > bad_wer_threshold)

    system_abstained = (
        avg_logprob < logprob_threshold
        or no_speech_prob > no_speech_threshold
        or compression_ratio > compression_threshold
    )

    if not is_bad_stt and not system_abstained:
        outcome = "correct_continuation"
    elif not is_bad_stt and system_abstained:
        outcome = "false_abstention"
    elif is_bad_stt and not system_abstained:
        outcome = "dangerous_continuation"
    else:
        outcome = "correct_abstention"

    return {
        "is_bad_stt": is_bad_stt,
        "system_abstained": system_abstained,
        "outcome": outcome,
    }


def threshold_sweep(
    samples: List[Dict],
    logprob_thresholds: List[float] = [-1.5, -1.25, -1.0, -0.75, -0.5],
    no_speech_thresholds: List[float] = [0.4, 0.6, 0.8],
    compression_thresholds: List[float] = [2.0, 2.4, 2.8],
    bad_wer_threshold: float = 0.3,
) -> List[Dict]:
    """
    Performs grid sweep across STT signal thresholds.
    Target: Detect bad transcriptions (WER > bad_wer_threshold).
    """
    results = []

    for lp_t in logprob_thresholds:
        for ns_t in no_speech_thresholds:
            for cr_t in compression_thresholds:
                tp = fp = tn = fn = 0
                brier_sum = 0.0

                for s in samples:
                    wer = s.get("wer", 0.0)
                    lp = s.get("avg_logprob", -0.5)
                    nsp = s.get("no_speech_prob", 0.05)
                    cr = s.get("compression_ratio", 1.2)

                    res = evaluate_decision(
                        wer=wer,
                        avg_logprob=lp,
                        no_speech_prob=nsp,
                        compression_ratio=cr,
                        logprob_threshold=lp_t,
                        no_speech_threshold=ns_t,
                        compression_threshold=cr_t,
                        bad_wer_threshold=bad_wer_threshold,
                    )

                    is_bad = res["is_bad_stt"]
                    abstained = res["system_abstained"]

                    if is_bad and abstained:
                        tp += 1  # Correct abstention
                    elif not is_bad and abstained:
                        fp += 1  # False abstention
                    elif not is_bad and not abstained:
                        tn += 1  # Correct continuation
                    else:
                        fn += 1  # Dangerous continuation

                    prob_bad = 1.0 - compute_stt_reliability_score(lp, nsp, cr)
                    actual_bad = 1.0 if is_bad else 0.0
                    brier_sum += (prob_bad - actual_bad) ** 2

                n = len(samples)
                precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
                recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
                f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
                dangerous_rate = fn / n if n > 0 else 0.0
                false_abstention_rate = fp / n if n > 0 else 0.0
                brier_score = brier_sum / n if n > 0 else 0.0

                results.append({
                    "logprob_threshold": lp_t,
                    "no_speech_threshold": ns_t,
                    "compression_threshold": cr_t,
                    "precision": round(precision, 4),
                    "recall": round(recall, 4),
                    "f1": round(f1, 4),
                    "dangerous_continuation_rate": round(dangerous_rate, 4),
                    "false_abstention_rate": round(false_abstention_rate, 4),
                    "brier_score": round(brier_score, 4),
                    "tp": tp,
                    "fp": fp,
                    "tn": tn,
                    "fn": fn,
                    "n": n,
                })

    return sorted(results, key=lambda x: (x["dangerous_continuation_rate"], -x["f1"]))
