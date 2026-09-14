"""
evaluation/metrics/transcription.py - WER and CER computation.

Normalization applied before comparison:
  1. Lowercase
  2. Strip leading/trailing whitespace
  3. Collapse multiple spaces
  4. Remove punctuation marks: . , ! ? ; : ' " ( ) [ ] { }
  5. DO NOT remove meaningful content (numbers, hyphens, domain terms)

WER = (S + D + I) / N
  S = substitutions, D = deletions, I = insertions
  N = number of words in reference (ground truth)

CER applies the same formula at the character level.
"""
import re
from typing import Tuple


_PUNCT_RE = re.compile(r"[.,!?;:\"\'()\[\]{}]")


def _normalize(text: str) -> str:
    """Apply standard normalization before metric computation."""
    text = text.lower().strip()
    text = _PUNCT_RE.sub("", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _edit_distance(ref: list, hyp: list) -> Tuple[int, int, int]:
    """
    Compute (substitutions, deletions, insertions) using dynamic programming.
    Returns (S, D, I) so callers can inspect each component separately.
    """
    r, h = len(ref), len(hyp)
    d = [[0] * (h + 1) for _ in range(r + 1)]
    for i in range(r + 1):
        d[i][0] = i
    for j in range(h + 1):
        d[0][j] = j

    for i in range(1, r + 1):
        for j in range(1, h + 1):
            if ref[i - 1] == hyp[j - 1]:
                d[i][j] = d[i - 1][j - 1]
            else:
                substitute = d[i - 1][j - 1] + 1
                delete = d[i - 1][j] + 1
                insert = d[i][j - 1] + 1
                d[i][j] = min(substitute, delete, insert)

    # Back-trace to count S, D, I
    i, j = r, h
    s = d_count = ins = 0
    while i > 0 or j > 0:
        if i > 0 and j > 0 and ref[i - 1] == hyp[j - 1]:
            i -= 1; j -= 1
        elif i > 0 and j > 0 and d[i][j] == d[i - 1][j - 1] + 1:
            s += 1; i -= 1; j -= 1
        elif i > 0 and d[i][j] == d[i - 1][j] + 1:
            d_count += 1; i -= 1
        else:
            ins += 1; j -= 1

    return s, d_count, ins


def compute_wer(reference: str, hypothesis: str) -> float:
    """
    Word Error Rate.  Returns value in [0, inf).
    Returns 0.0 when both reference and hypothesis are empty.
    Returns 1.0 + insertion_rate when hypothesis is longer and ref is empty.
    """
    ref_norm = _normalize(reference)
    hyp_norm = _normalize(hypothesis)

    if not ref_norm and not hyp_norm:
        return 0.0
    if not ref_norm:
        # All insertions; define WER as number of inserted words (no reference to normalize by)
        return float(len(hyp_norm.split()))

    ref_words = ref_norm.split()
    hyp_words = hyp_norm.split() if hyp_norm else []

    s, d, ins = _edit_distance(ref_words, hyp_words)
    return (s + d + ins) / len(ref_words)


def compute_cer(reference: str, hypothesis: str) -> float:
    """
    Character Error Rate.  Uses same normalization as WER but at character level.
    Returns value in [0, inf).
    """
    ref_norm = _normalize(reference)
    hyp_norm = _normalize(hypothesis)

    if not ref_norm and not hyp_norm:
        return 0.0
    if not ref_norm:
        return float(len(hyp_norm))

    ref_chars = list(ref_norm)
    hyp_chars = list(hyp_norm) if hyp_norm else []

    s, d, ins = _edit_distance(ref_chars, hyp_chars)
    return (s + d + ins) / len(ref_chars)


def compute_metrics(reference: str, hypothesis: str) -> dict:
    """Convenience: compute WER, CER, and normalization text in one call."""
    return {
        "wer": round(compute_wer(reference, hypothesis), 4),
        "cer": round(compute_cer(reference, hypothesis), 4),
        "reference_normalized": _normalize(reference),
        "hypothesis_normalized": _normalize(hypothesis),
    }
