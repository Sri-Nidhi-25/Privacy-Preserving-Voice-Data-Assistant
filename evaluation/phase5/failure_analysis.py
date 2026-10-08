"""
evaluation/phase5/failure_analysis.py - Root Cause Failure Classification for Phase 5.

Classifies routing and pipeline failures into the formal Phase 5 Failure Taxonomy:
- LEXICAL_ANCHORING
- SEMANTIC_DISTRACTOR
- DOMAIN_AMBIGUITY
- MISSING_OPERATION
- MISSING_ARGUMENT
- CROSS_DOMAIN_CONFUSION
- TRANSCRIPT_ERROR
- CORRECTION_FAILURE
- TOOL_ALIGNMENT_FAILURE
- OTHER
"""
import re
from typing import Any, Dict, Optional


DISTRACTOR_KEYWORDS = [
    "concert ticket", "movie ticket", "plane ticket", "speeding ticket", "lottery ticket",
    "support dog", "support beam", "active volcano", "active volunteers",
    "customer feedback was", "customer satisfaction", "feedback was", "reviews from"
]

NON_OPERATIONAL_VERBS = [
    "bought", "attended", "discussed", "erupted", "booked", "cracked",
    "wonder if", "would be wonderful", "origin of"
]


def classify_failure_cause(
    input_text: str,
    expected_route: str,
    actual_route: str,
    expected_tool: Optional[str] = None,
    actual_tool: Optional[str] = None,
    error_message: Optional[str] = None,
) -> str:
    """
    Determines the root cause failure code based on linguistic and pipeline signals.
    """
    lowered = input_text.lower()

    # 1. Pipeline / Execution errors
    if error_message:
        if "align" in error_message.lower():
            return "TOOL_ALIGNMENT_FAILURE"
        if "schema" in error_message.lower() or "argument" in error_message.lower():
            return "MISSING_ARGUMENT"
        return "OTHER"

    # 2. Tool alignment mismatch
    if expected_route == "tool" and actual_route == "tool":
        if expected_tool and actual_tool and expected_tool != actual_tool:
            return "CROSS_DOMAIN_CONFUSION"

    # 3. False Positive Failures (Expected direct, got tool)
    if expected_route == "direct" and actual_route == "tool":
        # Check for distractor keywords
        if any(dk in lowered for dk in DISTRACTOR_KEYWORDS):
            return "SEMANTIC_DISTRACTOR"

        # Check for narrative verbs without operational requests
        if any(nv in lowered for nv in NON_OPERATIONAL_VERBS):
            return "SEMANTIC_DISTRACTOR"

        # Check for domain noun with no operational action verb
        has_domain_token = bool(re.search(r"\b(customer|ticket|support|analytics|crm|metric|dau)\b", lowered))
        has_action_verb = bool(re.search(r"\b(show|list|get|fetch|pull|retrieve|find|display)\b", lowered))

        if has_domain_token and not has_action_verb:
            return "MISSING_OPERATION"

        if has_domain_token:
            return "LEXICAL_ANCHORING"

        return "DOMAIN_AMBIGUITY"

    # 4. False Negative Failures (Expected tool, got direct)
    if expected_route == "tool" and actual_route == "direct":
        # Check for domain ambiguity
        domain_matches = 0
        if re.search(r"\b(customer|crm|client|account)\b", lowered):
            domain_matches += 1
        if re.search(r"\b(ticket|support)\b", lowered):
            domain_matches += 1
        if re.search(r"\b(analytics|dau|metric)\b", lowered):
            domain_matches += 1

        if domain_matches > 1:
            return "DOMAIN_AMBIGUITY"

        # Check for typos or OOD vocabulary
        return "LEXICAL_ANCHORING"

    return "OTHER"
