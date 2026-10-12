"""
app/services/correction_guard.py - Reliability validation layer for transcript correction.

Ensures that LLM transcript corrections are validated deterministically
before they are accepted downstream.
"""
import re
from enum import Enum
from typing import Optional, Tuple, List, Set


class CorrectionDecision(str, Enum):
    KEEP_RAW = "KEEP_RAW"
    ACCEPT_CORRECTION = "ACCEPT_CORRECTION"
    ABSTAIN = "ABSTAIN"


_REFUSAL_MARKERS = (
    "i can't", "i cannot", "i can not", "i'm not able", "i am not able",
    "as an ai", "i apologize", "i'm sorry", "sorry, i", "i don't have the ability",
    "i do not have the ability", "as a language model", "i'm unable", "i am unable",
    "here is the corrected", "corrected transcript:", "here's the"
)

# Mutually exclusive polar domain terms that should not be inverted by correction
POLAR_PAIRS = [
    ("active", "inactive"),
    ("open", "closed"),
    ("low", "high"),
]


def looks_like_refusal_or_commentary(text: str) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in _REFUSAL_MARKERS)


def word_overlap_ratio(a: str, b: str) -> float:
    a_words = set(re.findall(r"[a-z0-9']+", a.lower()))
    b_words = set(re.findall(r"[a-z0-9']+", b.lower()))
    if not a_words:
        return 1.0
    return len(a_words & b_words) / len(a_words)


def extract_numbers(text: str) -> List[str]:
    """Extract discrete numbers from text."""
    return re.findall(r"\b\d+\b", text)


def validate_correction(raw: str, corrected: str) -> Tuple[bool, Optional[str]]:
    """
    Validate whether a proposed correction preserves intent, entities, numbers,
    and is not an adversarial hallucination.

    Returns:
        (is_valid, rejection_reason)
    """
    raw_clean = raw.strip()
    corr_clean = corrected.strip()

    if not corr_clean:
        return False, "empty_correction"

    # 1. Refusal and commentary markers (explicit refusal takes precedence)
    if looks_like_refusal_or_commentary(corr_clean):
        return False, "refusal_or_commentary"

    # 2. Length ratio validation (prevent runaway expansion or truncation)
    len_raw = len(raw_clean)
    len_corr = len(corr_clean)
    if len_corr > len_raw * 1.8:
        return False, "excessive_expansion"
    if len_corr < len_raw * 0.5:
        return False, "excessive_truncation"

    # 3. Word overlap threshold
    overlap = word_overlap_ratio(raw_clean, corr_clean)
    if overlap < 0.5:
        return False, f"low_word_overlap_{overlap:.2f}"

    # 4. Number preservation (arguments like limits/days must not be invented or altered)
    raw_nums = extract_numbers(raw_clean)
    corr_nums = extract_numbers(corr_clean)
    if raw_nums != corr_nums:
        # If numbers were altered or invented
        if set(corr_nums) - set(raw_nums):
            return False, "invented_numbers"
        if set(raw_nums) - set(corr_nums):
            return False, "dropped_numbers"
        if corr_nums != raw_nums:
            return False, "altered_numbers"

    # 5. Polar intent preservation (prevent active -> inactive, open -> closed)
    raw_lower = raw_clean.lower()
    corr_lower = corr_clean.lower()
    raw_tokens = set(re.findall(r"\b[a-z0-9']+\b", raw_lower))
    corr_tokens = set(re.findall(r"\b[a-z0-9']+\b", corr_lower))

    for word_a, word_b in POLAR_PAIRS:
        # If raw had word_a and not word_b, corrected should not have word_b
        if word_a in raw_tokens and word_b not in raw_tokens:
            if word_b in corr_tokens:
                return False, f"intent_inversion_{word_a}_to_{word_b}"
            # Also ensure the critical filter keyword was not dropped entirely
            if word_a not in corr_tokens:
                return False, f"dropped_filter_term_{word_a}"
        # If raw had word_b and not word_a, corrected should not have word_a
        if word_b in raw_tokens and word_a not in raw_tokens:
            if word_a in corr_tokens:
                return False, f"intent_inversion_{word_b}_to_{word_a}"
            # Also ensure the critical filter keyword was not dropped entirely
            if word_b not in corr_tokens:
                return False, f"dropped_filter_term_{word_b}"

    return True, None


def apply_correction_gate(raw: str, corrected: str) -> Tuple[CorrectionDecision, str, Optional[str]]:
    """
    Applies the correction gate decision:
    Returns (decision, final_text, reason)
    """
    if not corrected or corrected.strip() == raw.strip():
        return CorrectionDecision.KEEP_RAW, raw, None

    is_valid, reason = validate_correction(raw, corrected)
    if is_valid:
        return CorrectionDecision.ACCEPT_CORRECTION, corrected.strip(), None
    else:
        return CorrectionDecision.KEEP_RAW, raw, reason
