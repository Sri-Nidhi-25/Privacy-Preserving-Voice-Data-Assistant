"""Unit tests for the Phase 5 Dual-Evidence Selective Abstention Router."""

import pytest
from app.services.abstention_router import evaluate_abstention, Decision


def test_clear_operational_requests():
    """Clear imperative commands with domain targets should be executed with high confidence."""
    queries = [
        "Show me all active customers",
        "Fetch open tickets with high priority",
        "Display user metrics for last month",
    ]
    for q in queries:
        result = evaluate_abstention(q)
        assert result.decision == Decision.EXECUTE, f"Failed for '{q}': got {result.decision}"
        assert result.route == "tool"
        assert result.confidence >= 0.50
        assert result.operational_evidence > 0
        assert result.domain_evidence > 0
        assert result.target_tool is not None


def test_clear_conversational_requests():
    """General chatter without enterprise domain cues routes DIRECT."""
    queries = [
        "Hello, how are you doing today?",
        "What is the weather outside?",
        "Thank you so much for your help",
    ]
    for q in queries:
        result = evaluate_abstention(q)
        assert result.decision == Decision.DIRECT, f"Failed for '{q}': got {result.decision}"
        assert result.route == "direct"
        assert result.domain_evidence == 0.0


def test_semantic_distractors_abstain():
    """Domain words inside narrative, comparative, or conversational text should ABSTAIN."""
    distractors = [
        "The active customers attended the annual conference",
        "The support tickets were discussed during the staff meeting",
        "User metrics alone cannot capture the full emotional impact of art",
        "Customer profiles on social networks can be vulnerable to phishing",
    ]
    for q in distractors:
        result = evaluate_abstention(q)
        assert result.decision == Decision.ABSTAIN, (
            f"Expected ABSTAIN for distractor '{q}', got {result.decision} (confidence={result.confidence:.2f})"
        )
        assert result.target_tool is None
        assert "distractor" in result.reason.lower() or "insufficient" in result.reason.lower()


def test_adversarial_hypothetical_framing_abstains():
    """Hypothetical or explanatory queries containing tool words should be rejected or abstained."""
    adversarial_queries = [
        "What is the origin of support tickets?",
        "Explain the difference between customer satisfaction metrics",
        "Write a python script to parse logs",
    ]
    for q in adversarial_queries:
        result = evaluate_abstention(q)
        assert result.decision in (Decision.ABSTAIN, Decision.DIRECT), (
            f"Adversarial query '{q}' should NOT execute, got {result.decision}"
        )
        assert result.target_tool is None


def test_abstention_result_fields():
    """Ensure all required diagnostic fields are populated."""
    result = evaluate_abstention("Customers in retail often complain about wait times")
    assert result.domain_evidence > 0
    assert hasattr(result, "operational_evidence")
    assert hasattr(result, "distractor_penalty")
    assert hasattr(result, "matched_domains")
    assert isinstance(result.reason, str) and len(result.reason) > 0
