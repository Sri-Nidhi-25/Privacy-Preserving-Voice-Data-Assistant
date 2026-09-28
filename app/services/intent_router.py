"""
app/services/intent_router.py - Reliability-aware Intent Classification and Routing.

Replaces naïve single-keyword matching with entity-grounded intent classification.
Avoids false-positive tool calls on non-data queries like "Get me a glass of water"
or "My customer service was excellent today".
"""
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple


class Intent(str, Enum):
    CRM_QUERY = "CRM_QUERY"
    SUPPORT_QUERY = "SUPPORT_QUERY"
    ANALYTICS_QUERY = "ANALYTICS_QUERY"
    DIRECT = "DIRECT"
    AMBIGUOUS = "AMBIGUOUS"


@dataclass
class IntentResult:
    intent: Intent
    route: str                       # "tool" or "direct"
    target_tool: Optional[str]       # "get_crm_data", "get_support_tickets", "get_analytics", or None
    confidence: float                # 0.0 to 1.0
    matched_entities: List[str] = field(default_factory=list)
    reason: str = ""


# Conversational phrases that contain domain words but are strictly direct non-data queries
ADVERSARIAL_DIRECT_PATTERNS = [
    re.compile(r"\bcustomer\s+service\b.*\b(excellent|good|bad|terrible|great|horrible|poor)\b", re.IGNORECASE),
    re.compile(r"\b(service|support)\b.*\b(excellent|great|terrible|awesome)\b", re.IGNORECASE),
    re.compile(r"\bactive\s+participation\b", re.IGNORECASE),
    re.compile(r"\bglass\s+of\s+water\b", re.IGNORECASE),
    re.compile(r"\bcup\s+of\s+(coffee|tea)\b", re.IGNORECASE),
    re.compile(r"\bnumber\s+of\s+meetings\b", re.IGNORECASE),
    re.compile(r"\bpeople\s+were\s+at\s+the\b", re.IGNORECASE),
    re.compile(r"\b(capital\s+of|tell\s+me\s+a\s+joke|weather\s+like|what\s+time\s+is\s+it)\b", re.IGNORECASE),
    # Explanatory and definitional queries about domains (informational, not data requests)
    re.compile(r"^(what\s+is|what's|explain|describe|tell\s+me\s+about|what\s+does)\s+(the\s+meaning\s+of\s+)?(crm|analytics|support\s+tickets?|active\s+status|engagement)\b", re.IGNORECASE),
    re.compile(r"\b(explain\s+what|stands\s+for|what\s+does\s+.*\s+mean|difference\s+between)\b", re.IGNORECASE),
    re.compile(r"\b(how\s+is\s+.*\s+calculated|what\s+exactly\s+is)\b", re.IGNORECASE),
    # Team sentiment, narrative descriptions, or past-tense remarks
    re.compile(r"\b(crushed|crushing\s+it|doing\s+great|resolved\s+all\s+tickets|flying\s+in)\b", re.IGNORECASE),
    re.compile(r"\b(analysts?|sales\s+team|support\s+team)\b.*\b(reviewing|crushed|doing|targets?|internally)\b", re.IGNORECASE),
    re.compile(r"\b(launch|outage|product)\b.*\b(incredible|awesome|flying|great)\b", re.IGNORECASE),
    re.compile(r"\breally\s+engaged\s+with\b", re.IGNORECASE),
]

# Domain entity regexes
CRM_PATTERNS = [
    re.compile(r"\b(customer|customers|crm|client|clients|account|accounts)\b", re.IGNORECASE),
]

SUPPORT_PATTERNS = [
    re.compile(r"\b(ticket|tickets|support\s+tickets?|support\s+issue|support\s+issues|support\s+cases?|support\s+queue)\b", re.IGNORECASE),
    re.compile(r"\bopen\s+(items|cases|tickets?)\b", re.IGNORECASE),
    re.compile(r"\b(high|medium|low|urgent|critical)\s+(priority|support)?\b", re.IGNORECASE),
]

ANALYTICS_PATTERNS = [
    re.compile(r"\b(daily\s+active\s+users?|dau|analytics(\s+data)?|user\s+metrics?|metrics?\s+trend|metric(\s+for|\s+of)?\s+users?|average\s+metric|engagement(\s+data|\s+metrics?|\s+numbers?)?|metrics\b)", re.IGNORECASE),
]

# Supporting filter or action markers that strengthen domain intent
ACTION_VERBS = re.compile(r"\b(show(\s+me)?|list|get(\s+me)?|how\s+many|count|find|display|give\s+me|pull|fetch|retrieve|bring\s+up)\b", re.IGNORECASE)


def classify_intent(text: str) -> IntentResult:
    """
    Classifies the user query into a domain intent with entity anchoring.
    """
    clean = text.strip()
    if not clean:
        return IntentResult(
            intent=Intent.DIRECT,
            route="direct",
            target_tool=None,
            confidence=1.0,
            reason="empty_query",
        )

    # 1. Check for explicit conversational / adversarial false-positive patterns
    for pat in ADVERSARIAL_DIRECT_PATTERNS:
        if pat.search(clean):
            return IntentResult(
                intent=Intent.DIRECT,
                route="direct",
                target_tool=None,
                confidence=0.95,
                matched_entities=[],
                reason="conversational_pattern_matched",
            )

    # 2. Check for domain entity presence
    has_crm = any(pat.search(clean) for pat in CRM_PATTERNS)
    has_support = any(pat.search(clean) for pat in SUPPORT_PATTERNS)
    has_analytics = any(pat.search(clean) for pat in ANALYTICS_PATTERNS)

    entities = []
    if has_crm:
        entities.append("crm")
    if has_support:
        entities.append("support")
    if has_analytics:
        entities.append("analytics")

    has_action = bool(ACTION_VERBS.search(clean))

    # Single domain match with entity
    if has_crm and not has_support and not has_analytics:
        return IntentResult(
            intent=Intent.CRM_QUERY,
            route="tool",
            target_tool="get_crm_data",
            confidence=0.95 if has_action else 0.85,
            matched_entities=entities,
            reason="crm_entity_detected",
        )

    if has_support and not has_crm and not has_analytics:
        return IntentResult(
            intent=Intent.SUPPORT_QUERY,
            route="tool",
            target_tool="get_support_tickets",
            confidence=0.95 if has_action else 0.85,
            matched_entities=entities,
            reason="support_entity_detected",
        )

    if has_analytics and not has_crm and not has_support:
        return IntentResult(
            intent=Intent.ANALYTICS_QUERY,
            route="tool",
            target_tool="get_analytics",
            confidence=0.95 if has_action else 0.85,
            matched_entities=entities,
            reason="analytics_entity_detected",
        )

    # Multiple domain entities detected (e.g. CRM and tickets together) -> ambiguous routing
    if len(entities) > 1:
        return IntentResult(
            intent=Intent.AMBIGUOUS,
            route="tool",
            target_tool=None,
            confidence=0.5,
            matched_entities=entities,
            reason="multiple_domain_entities_detected",
        )

    # No domain entities detected
    # Even if verbs like "get" or "how many" or "count" are present,
    # without a domain entity it is a direct query (not a database query).
    return IntentResult(
        intent=Intent.DIRECT,
        route="direct",
        target_tool=None,
        confidence=0.9,
        matched_entities=[],
        reason="no_domain_entities_detected",
    )


def is_data_query(text: str) -> bool:
    """
    Drop-in replacement for the legacy _is_data_query function.
    Returns True only when a domain data entity is targeted.
    """
    res = classify_intent(text)
    return res.route == "tool"
