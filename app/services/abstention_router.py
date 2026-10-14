"""
app/services/abstention_router.py - Evidence-Grounded Abstention Engine for Phase 5.

Decouples Domain Entity Evidence from Operational Speech-Act Evidence to prevent
lexical anchoring and false-positive tool executions on semantic distractors.

Core Formulation:
  E_domain: Strength of database domain relevance (CRM, Support, Analytics)
  E_op:     Strength of operational retrieval speech-act (imperative verbs, filters)
  D_dist:   Strength of conversational, narrative, or cross-domain distractor cues

Decision:
  - EXECUTE: High domain evidence AND high operational evidence, low distractor penalty.
  - ABSTAIN: Domain vocabulary present, but missing operational request evidence or high distractor penalty.
  - DIRECT:  No domain vocabulary present; standard conversational LLM handling.
"""
from dataclasses import dataclass
from enum import Enum
import re
from typing import Dict, List, Optional, Tuple

from app.services.intent_router import Intent


class Decision(Enum):
    EXECUTE = "EXECUTE"
    ABSTAIN = "ABSTAIN"
    DIRECT = "DIRECT"


@dataclass
class AbstentionResult:
    intent: Intent
    route: str                    # "tool", "direct", or "abstain"
    decision: Decision
    confidence: float             # Calibrated evidence score [0.0, 1.0]
    domain_evidence: float
    operational_evidence: float
    distractor_penalty: float
    target_tool: Optional[str]
    matched_domains: List[str]
    reason: str


# 1. Domain Entities
CRM_ENTITIES = re.compile(r"\b(customer|customers|crm|client|clients|account|accounts|roster|patron|patrons)\b", re.IGNORECASE)
SUPPORT_ENTITIES = re.compile(r"\b(ticket|tickets|support\s+tickets?|support\s+issue|support\s+issues|support\s+cases?|support\s+queue|helpdesk|grievance|grievances)\b", re.IGNORECASE)
ANALYTICS_ENTITIES = re.compile(r"\b(daily\s+active\s+users?|dau|analytics|user\s+metrics?|metrics?\s+trend|metric|engagement|retention|active\s+users?(\s+daily)?)\b", re.IGNORECASE)

# 2. Operational Directives & Modalities
OPERATIONAL_DIRECTIVES = re.compile(
    r"\b(show|list|get|give|display|fetch|pull|retrieve|find|search|look\s+up|check|surface|tabulate|catalog|inspect|export)\b",
    re.IGNORECASE
)
OPERATIONAL_INTERROGATIVES = re.compile(
    r"\b(how\s+many|are\s+there\s+(any)?|can\s+you\s+(show|list|get|fetch|pull|retrieve|find)|could\s+you\s+(show|list|get|fetch|pull)|what\s+is\s+our\s+(current\s+)?(daily\s+active\s+user|dau|count)|what('s|\s+is)\s+(the\s+)?(average|total|current|count))\b",
    re.IGNORECASE
)
OPERATIONAL_FILTERS = re.compile(
    r"\b(active|inactive|open|closed|high\s+priority|medium\s+priority|low\s+priority|urgent|critical|days|limit|capped\s+at|top\s+\d+)\b",
    re.IGNORECASE
)

# 3. Contextual Non-Operational Distractor Cues
NON_OPERATIONAL_DISTRACTORS = [
    re.compile(r"\b(concert|movie|plane|train|flight|speeding|parking|lottery|golden|theater|cinema)\s+tickets?\b", re.IGNORECASE),
    re.compile(r"\btickets?\s+(scalpers?|inspector|fines?|price|holders?|please)\b", re.IGNORECASE),
    re.compile(r"\bsupport\s+(dog|animal|beam|group|community|network|family|library|parents)\b", re.IGNORECASE),
    re.compile(r"\bactive\s+(volcano|volcanoes|volunteers?|ingredient|member|participation)\b", re.IGNORECASE),
    re.compile(r"\bcustomer\s+(service|satisfaction|loyalty|feedback|experience|reviews?|psychology|philosoph(y|ies))\b.*\b(was|were|received|reveals|evolved|enthusiasm|programs?)\b", re.IGNORECASE),
    re.compile(r"\b(feedback|responses?|reviews?)\s+was\s+(overwhelmingly\s+)?(positive|great|excellent|good|poor|negative)\b", re.IGNORECASE),
    re.compile(r"\b(bought|booked|attended|cheered|cracked|erupted|discussed\s+in|presented\s+at)\b", re.IGNORECASE),
    re.compile(r"^(what\s+is|what's|explain|describe|tell\s+me\s+about|what\s+does)\s+(the\s+meaning\s+of|the\s+difference\s+between|the\s+origin\s+of)\b", re.IGNORECASE),
    re.compile(r"^(write\s+a\s+(python\s+script|poem|letter|summary)|draft\s+a|compare\s+(zendesk|salesforce))\b", re.IGNORECASE),
]


def evaluate_abstention(text: str, threshold: float = 0.50) -> AbstentionResult:
    """
    Evaluates evidence components and renders an EXECUTE, ABSTAIN, or DIRECT decision.
    """
    trimmed = text.strip()
    lowered = trimmed.lower()

    # Step 1: Compute Domain Evidence
    matched_domains = []
    e_crm = 1.0 if CRM_ENTITIES.search(lowered) else 0.0
    e_sup = 1.0 if SUPPORT_ENTITIES.search(lowered) else 0.0
    e_ana = 1.0 if ANALYTICS_ENTITIES.search(lowered) else 0.0

    if e_crm: matched_domains.append("crm")
    if e_sup: matched_domains.append("support")
    if e_ana: matched_domains.append("analytics")

    domain_evidence = max(e_crm, e_sup, e_ana)

    # Step 2: Compute Operational Modality Evidence
    op_directive_score = 1.0 if OPERATIONAL_DIRECTIVES.search(lowered) else 0.0
    op_interrogative_score = 1.0 if OPERATIONAL_INTERROGATIVES.search(lowered) else 0.0
    op_filter_score = 0.5 if OPERATIONAL_FILTERS.search(lowered) else 0.0

    operational_evidence = min(1.0, max(op_directive_score, op_interrogative_score) + op_filter_score)

    # Step 3: Compute Distractor Penalty
    distractor_penalty = 0.0
    matched_distractor_pattern = None
    for pattern in NON_OPERATIONAL_DISTRACTORS:
        if pattern.search(lowered):
            distractor_penalty = 1.0
            matched_distractor_pattern = pattern.pattern
            break

    # Step 4: No domain entities detected -> Standard DIRECT
    if domain_evidence == 0.0:
        return AbstentionResult(
            intent=Intent.DIRECT,
            route="direct",
            decision=Decision.DIRECT,
            confidence=1.0,
            domain_evidence=0.0,
            operational_evidence=operational_evidence,
            distractor_penalty=distractor_penalty,
            target_tool=None,
            matched_domains=[],
            reason="No domain entities present; standard direct response.",
        )

    # Step 5: Multi-domain handling
    if len(matched_domains) > 1 and not distractor_penalty:
        if operational_evidence >= 0.5:
            # Genuine cross-domain operational request (e.g. correlating CRM and Support)
            return AbstentionResult(
                intent=Intent.MULTI_DOMAIN_QUERY,
                route="tool",
                decision=Decision.EXECUTE,
                confidence=min(1.0, domain_evidence * 0.40 + operational_evidence * 0.60),
                domain_evidence=domain_evidence,
                operational_evidence=operational_evidence,
                distractor_penalty=distractor_penalty,
                target_tool=None,
                matched_domains=matched_domains,
                reason=f"Cross-domain operational query correlating multiple entities: {matched_domains}.",
            )
        else:
            # Unfocused cross-domain mention without clear operational directive
            return AbstentionResult(
                intent=Intent.AMBIGUOUS,
                route="abstain",
                decision=Decision.ABSTAIN,
                confidence=0.30,
                domain_evidence=domain_evidence,
                operational_evidence=operational_evidence,
                distractor_penalty=distractor_penalty,
                target_tool=None,
                matched_domains=matched_domains,
                reason=f"Multiple conflicting domain entities detected without clear operational query: {matched_domains}.",
            )

    # Step 6: Map primary domain target
    target_tool = None
    if "crm" in matched_domains:
        primary_intent = Intent.CRM_QUERY
        target_tool = "get_crm_data"
    elif "support" in matched_domains:
        primary_intent = Intent.SUPPORT_QUERY
        target_tool = "get_support_tickets"
    elif "analytics" in matched_domains:
        primary_intent = Intent.ANALYTICS_QUERY
        target_tool = "get_analytics"
    else:
        primary_intent = Intent.DIRECT

    # Step 7: Calculate Net Operational Confidence
    # Calibrated confidence formula:
    # Requires both domain evidence AND operational modality, heavily penalized by distractor signals
    if distractor_penalty > 0:
        confidence = max(0.0, operational_evidence * 0.20)
    else:
        confidence = domain_evidence * 0.40 + operational_evidence * 0.60

    confidence = round(confidence, 3)

    # Step 8: Apply Decision Gate
    if distractor_penalty > 0:
        return AbstentionResult(
            intent=primary_intent,
            route="direct",  # Safely handle conversationally without executing tool
            decision=Decision.ABSTAIN,
            confidence=confidence,
            domain_evidence=domain_evidence,
            operational_evidence=operational_evidence,
            distractor_penalty=distractor_penalty,
            target_tool=None,
            matched_domains=matched_domains,
            reason=f"Semantic distractor detected; abstaining from tool execution.",
        )

    if confidence >= threshold and operational_evidence > 0.0:
        return AbstentionResult(
            intent=primary_intent,
            route="tool",
            decision=Decision.EXECUTE,
            confidence=confidence,
            domain_evidence=domain_evidence,
            operational_evidence=operational_evidence,
            distractor_penalty=distractor_penalty,
            target_tool=target_tool,
            matched_domains=matched_domains,
            reason="High domain and operational evidence; tool execution authorized.",
        )
    else:
        # Abstain due to low operational evidence (e.g. bare domain noun or vague query)
        return AbstentionResult(
            intent=primary_intent,
            route="abstain",
            decision=Decision.ABSTAIN,
            confidence=confidence,
            domain_evidence=domain_evidence,
            operational_evidence=operational_evidence,
            distractor_penalty=distractor_penalty,
            target_tool=None,
            matched_domains=matched_domains,
            reason="Domain vocabulary present, but operational request evidence is insufficient.",
        )
