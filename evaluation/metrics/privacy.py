"""
evaluation/metrics/privacy.py - Privacy metrics interface.

IMPORTANT: The current implementation records obfuscation parameters and pitch
statistics that can later be connected to speaker-verification experiments.
No privacy score is computed or claimed at this stage.

Privacy evaluation is pending: a valid experiment requires a speaker
verification or speaker identification model as a reference system.
See docs/evaluation_methodology.md for the full explanation.
"""
from typing import Optional
import numpy as np


PRIVACY_METRIC_STATUS = "not_yet_measured"


def pitch_statistics(audio: np.ndarray, sr: int) -> dict:
    """
    Compute basic F0-related statistics from a raw audio array.
    These are logged per evaluation case for future privacy analysis.
    """
    try:
        import pyworld as pw
        f0, t = pw.harvest(audio.astype(np.float64), float(sr))
        voiced = f0[f0 > 0]
        if len(voiced) == 0:
            return {"f0_mean": None, "f0_std": None, "f0_min": None, "f0_max": None, "voiced_frames": 0}
        return {
            "f0_mean": round(float(np.mean(voiced)), 2),
            "f0_std": round(float(np.std(voiced)), 2),
            "f0_min": round(float(np.min(voiced)), 2),
            "f0_max": round(float(np.max(voiced)), 2),
            "voiced_frames": int(len(voiced)),
        }
    except Exception as e:
        return {"f0_error": str(e)}


def privacy_placeholder() -> dict:
    """
    Returns a structured placeholder for the privacy metric.
    Replace with actual speaker-verification-based measurement in Phase 3.
    """
    return {
        "privacy_metric": PRIVACY_METRIC_STATUS,
        "note": (
            "Privacy evaluation requires a speaker verification model "
            "to measure whether the obfuscated voice can be de-anonymized. "
            "This is planned for Phase 3."
        ),
    }
