"""
tests/test_phase4/test_metamorphic.py - Genuine Oracle-Free Metamorphic Invariant Tests.

Metamorphic testing verifies invariant relations between outputs under systematic
input transformations:
    Relation: Intent(T(x)) == Intent(x)
              Route(T(x))  == Route(x)
              Tool(T(x))   == Tool(x)

Crucially, assertions do NOT compare against a hardcoded expected oracle label.
They evaluate whether the system's prediction is invariant to semantically neutral
transformations (politeness markers, casing, fillers, formatting).
"""
import re
import pytest
from app.services.intent_router import classify_intent, Intent
from app.services.correction_guard import apply_correction_gate, CorrectionDecision


# Base source queries spanning distinct domains
SOURCE_QUERIES = [
    "Show me active customers",
    "List all inactive accounts",
    "Show open tickets",
    "List high priority tickets",
    "Show analytics for last 30 days",
    "What is the daily active users count",
    "Hello there",
    "What is the capital of France",
    "Tell me a joke",
]


# Metamorphic Transformation Functions T(x)
def transform_politeness_prefix(text: str) -> str:
    return "Please " + text[:1].lower() + text[1:]


def transform_politeness_suffix(text: str) -> str:
    return text.rstrip(".!?") + ", please"


def transform_conversational_prefix(text: str) -> str:
    return "Can you " + text[:1].lower() + text[1:]


def transform_filler_words(text: str) -> str:
    words = text.split()
    if len(words) >= 2:
        return words[0] + ", uh, " + " ".join(words[1:])
    return "Um, " + text


def transform_uppercase(text: str) -> str:
    return text.upper()


def transform_lowercase(text: str) -> str:
    return text.lower()


def transform_whitespace_padding(text: str) -> str:
    return "   " + "   ".join(text.split()) + "   "


def transform_trailing_punctuation(text: str) -> str:
    base = text.rstrip(".!?")
    return base + "?" if not base.endswith("?") else base + "."


TRANSFORMATIONS = [
    ("politeness_prefix", transform_politeness_prefix),
    ("politeness_suffix", transform_politeness_suffix),
    ("conversational_prefix", transform_conversational_prefix),
    ("filler_words", transform_filler_words),
    ("uppercase", transform_uppercase),
    ("lowercase", transform_lowercase),
    ("whitespace_padding", transform_whitespace_padding),
    ("trailing_punctuation", transform_trailing_punctuation),
]


class TestOracleFreeMetamorphicRelations:
    """
    Genuine metamorphic testing:
    Checks relation R(f(x), f(T(x))) without referencing ground-truth labels.
    """

    @pytest.mark.parametrize("query", SOURCE_QUERIES)
    @pytest.mark.parametrize("trans_name,trans_fn", TRANSFORMATIONS)
    def test_routing_invariance_under_transformation(self, query, trans_name, trans_fn):
        orig_res = classify_intent(query)
        transformed = trans_fn(query)
        trans_res = classify_intent(transformed)

        # Invariant 1: Intent classification must be identical
        assert trans_res.intent == orig_res.intent, (
            f"Metamorphic violation [{trans_name}]:\n"
            f"Original:    '{query}' -> {orig_res.intent.value}\n"
            f"Transformed: '{transformed}' -> {trans_res.intent.value}"
        )

        # Invariant 2: Route decision (tool vs direct) must be identical
        assert trans_res.route == orig_res.route, (
            f"Route violation [{trans_name}]: '{query}' ({orig_res.route}) vs '{transformed}' ({trans_res.route})"
        )

        # Invariant 3: Tool target must be identical
        assert trans_res.target_tool == orig_res.target_tool, (
            f"Target tool violation [{trans_name}]: '{query}' ({orig_res.target_tool}) vs '{transformed}' ({trans_res.target_tool})"
        )


class TestCorrectionMetamorphicInvariants:
    """
    Tests metamorphic invariance of transcript correction guard.
    If a correction decision holds for (raw, corr), then wrapping both in
    identical harmless formatting must not invert the decision.
    """

    PAIR_CASES = [
        ("fetch inactve customers", "fetch inactive customers"),  # Typo fix
        ("get active customers", "get inactive customers"),        # Polar inversion
        ("show 5 tickets", "show 50 tickets"),                    # Number tampering
    ]

    @pytest.mark.parametrize("raw,corr", PAIR_CASES)
    def test_correction_casing_invariance(self, raw, corr):
        dec_orig, _, _ = apply_correction_gate(raw, corr)
        dec_upper, _, _ = apply_correction_gate(raw.upper(), corr.upper())
        dec_lower, _, _ = apply_correction_gate(raw.lower(), corr.lower())

        assert dec_upper == dec_orig, f"Casing inversion: {raw} vs {raw.upper()}"
        assert dec_lower == dec_orig, f"Casing inversion: {raw} vs {raw.lower()}"


class TestParaphraseClassificationOracles:
    """
    Labeled unit tests checking that known canonical clusters route properly.
    Explicitly labeled as unit/oracle tests, not metamorphic relations.
    """

    def test_canonical_crm(self):
        for text in ["Show me active customers", "List all active accounts"]:
            assert classify_intent(text).intent == Intent.CRM_QUERY

    def test_canonical_support(self):
        for text in ["Show open tickets", "List high priority tickets"]:
            assert classify_intent(text).intent == Intent.SUPPORT_QUERY

    def test_canonical_direct(self):
        for text in ["Hello", "What is the capital of France", "Tell me a joke"]:
            assert classify_intent(text).route == "direct"
