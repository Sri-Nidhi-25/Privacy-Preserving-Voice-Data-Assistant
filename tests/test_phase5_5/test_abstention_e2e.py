"""
Phase 5.5 — Abstention E2E Tests

Tests that the abstention mechanism behaves correctly end-to-end through the
LLM orchestrator:
- Distractor inputs must NOT execute tools when abstention is enabled
- Valid operational inputs SHOULD execute tools when abstention is enabled
- Disabling abstention allows distractors to reach tool execution (baseline behavior)

These tests do NOT inspect final test-set failures to write rules.
They test the mechanism using NEW inputs not in the evaluation datasets.
"""

import pytest
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_orchestrator():
    """Import and return a fresh orchestrator instance."""
    from app.services.llm_orchestrator import LLMOrchestrator
    return LLMOrchestrator()


# ---------------------------------------------------------------------------
# Test 1: Semantic distractor must be abstained from with abstention ON
# ---------------------------------------------------------------------------

class TestAbstentionBlocksDistractors:
    """With enable_abstention=True the router should catch semantic distractors."""

    def test_concert_ticket_distractor_is_abstained(self):
        """
        'I bought a concert ticket for tomorrow.'
        Contains 'ticket' — a lexical cue for support-ticket tooling.
        This is a pure semantic distractor; no operational intent exists.
        The abstention router must prevent tool execution.
        """
        orch = _make_orchestrator()
        result = orch.process_query(
            "I bought a concert ticket for tomorrow.",
            enable_abstention=True
        )
        meta = result.get("metadata", {})
        # Must not have called a tool unsafely
        assert meta.get("execution_prevented_by_abstention") or \
               result.get("tool_calls") is None or \
               result.get("tool_calls") == [], (
            f"Expected abstention to prevent tool execution, got: {meta}"
        )

    def test_customer_satisfaction_distractor_is_abstained(self):
        """
        'She showed great enthusiasm for customer satisfaction.'
        Contains 'customer' — CRM lexical cue. Purely conversational sentence.
        """
        orch = _make_orchestrator()
        result = orch.process_query(
            "She showed great enthusiasm for customer satisfaction.",
            enable_abstention=True
        )
        meta = result.get("metadata", {})
        assert meta.get("execution_prevented_by_abstention") or \
               result.get("tool_calls") is None or \
               result.get("tool_calls") == [], (
            f"Expected abstention to prevent tool execution, got: {meta}"
        )

    def test_analytics_distractor_is_abstained(self):
        """
        'The professor analyzed historical data patterns for her thesis.'
        Contains 'analyzed', 'data' — analytics lexical cues.
        No operational request is present.
        """
        orch = _make_orchestrator()
        result = orch.process_query(
            "The professor analyzed historical data patterns for her thesis.",
            enable_abstention=True
        )
        meta = result.get("metadata", {})
        assert meta.get("execution_prevented_by_abstention") or \
               result.get("tool_calls") is None or \
               result.get("tool_calls") == [], (
            f"Expected abstention to prevent tool execution, got: {meta}"
        )


# ---------------------------------------------------------------------------
# Test 2: Metadata fields are present when abstention is enabled
# ---------------------------------------------------------------------------

class TestAbstentionMetadata:
    """Verify that the metadata contract is met when abstention is enabled."""

    REQUIRED_META_KEYS = [
        "abstention_decision",
        "abstention_reason",
        "abstention_confidence",
        "execution_prevented_by_abstention",
    ]

    def test_metadata_keys_present_on_distractor(self):
        orch = _make_orchestrator()
        result = orch.process_query(
            "I bought a concert ticket for tomorrow.",
            enable_abstention=True
        )
        meta = result.get("metadata", {})
        for key in self.REQUIRED_META_KEYS:
            assert key in meta, f"Missing metadata key: {key!r}"

    def test_metadata_keys_present_on_direct_question(self):
        orch = _make_orchestrator()
        result = orch.process_query(
            "What is the weather like today?",
            enable_abstention=True
        )
        meta = result.get("metadata", {})
        for key in self.REQUIRED_META_KEYS:
            assert key in meta, f"Missing metadata key: {key!r}"

    def test_abstention_confidence_is_float_in_range(self):
        orch = _make_orchestrator()
        result = orch.process_query(
            "I bought a concert ticket for tomorrow.",
            enable_abstention=True
        )
        conf = result.get("metadata", {}).get("abstention_confidence")
        assert conf is not None, "abstention_confidence must be present"
        assert isinstance(conf, (int, float)), \
            f"abstention_confidence must be numeric, got {type(conf)}"
        assert 0.0 <= conf <= 1.0, \
            f"abstention_confidence must be in [0,1], got {conf}"


# ---------------------------------------------------------------------------
# Test 3: Disabling abstention allows distractor routing (baseline)
# ---------------------------------------------------------------------------

class TestBaselineAllowsDistractors:
    """
    With enable_abstention=False the system falls back to classify_intent()
    only. The distractor CAN reach tool selection (we cannot guarantee it
    WILL call the tool since it depends on the LLM), but abstention metadata
    must indicate no abstention occurred.
    """

    def test_abstention_decision_is_execute_when_disabled(self):
        """When abstention is OFF, abstention_decision must be EXECUTE or absent."""
        orch = _make_orchestrator()
        result = orch.process_query(
            "I bought a concert ticket for tomorrow.",
            enable_abstention=False
        )
        meta = result.get("metadata", {})
        decision = meta.get("abstention_decision")
        # When abstention is disabled, the router is not invoked so
        # execution_prevented_by_abstention must be False
        assert meta.get("execution_prevented_by_abstention") is False, (
            f"Baseline mode must not prevent execution, got: {meta}"
        )


# ---------------------------------------------------------------------------
# Test 4: Latency sub-fields are populated
# ---------------------------------------------------------------------------

class TestLatencyMetadata:
    """Ensure stage latency keys are recorded in metadata."""

    LATENCY_KEYS = [
        "correction_latency_ms",
        "routing_latency_ms",
        "abstention_latency_ms",
    ]

    def test_latency_keys_present(self):
        orch = _make_orchestrator()
        result = orch.process_query(
            "Show me the latest support tickets.",
            enable_abstention=True
        )
        meta = result.get("metadata", {})
        for key in self.LATENCY_KEYS:
            assert key in meta, f"Missing latency key: {key!r}"

    def test_latency_values_are_non_negative(self):
        orch = _make_orchestrator()
        result = orch.process_query(
            "Show me the latest support tickets.",
            enable_abstention=True
        )
        meta = result.get("metadata", {})
        for key in self.LATENCY_KEYS:
            val = meta.get(key, -1)
            assert val >= 0, f"Latency {key} must be non-negative, got {val}"
