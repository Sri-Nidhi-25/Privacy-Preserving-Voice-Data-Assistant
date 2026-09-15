"""
tests/test_phase3/test_phase3_invariants.py - Automated tests for Phase 3 Reliability Invariants.
"""
from unittest.mock import MagicMock
import pytest
from app.connectors.base import evaluate_freshness
from app.connectors.crm_connector import CRMConnector
from app.services.intent_router import Intent
from app.services.llm_orchestrator import LLMOrchestrator
from evaluation.fault_injection.connectors import FaultInjectingConnector


class TestPhase3Invariants:
    def test_invariant_no_fabricated_data_on_connector_failure(self):
        """
        Invariant: If a connector fails, the pipeline must report failure_type='connector_failed'
        and must never fabricate successful empty data.
        """
        orch = LLMOrchestrator()
        faulty = FaultInjectingConnector(CRMConnector(), failure_mode="timeout")
        orch.connector_map["get_crm_data"] = faulty

        tool_calls = [{"function": {"name": "get_crm_data", "arguments": {"status": "active"}}}]
        ans, meta = orch._execute_tool_calls(tool_calls, detected_intent=Intent.CRM_QUERY)

        assert "could not retrieve data" in ans.lower()
        assert meta["failure_type"] == "connector_failed"
        assert meta["result_count"] == 0
        assert meta["connector_error"] is not None

    def test_invariant_tool_selection_mismatch_blocked(self):
        """
        Invariant: An incompatible tool call for the detected intent (e.g. get_analytics for CRM)
        must be rejected immediately before any connector is executed.
        """
        orch = LLMOrchestrator()
        mock_analytics = MagicMock()
        orch.connector_map["get_analytics"] = mock_analytics

        tool_calls = [{"function": {"name": "get_analytics", "arguments": {"metric": "daily_active_users"}}}]
        ans, meta = orch._execute_tool_calls(tool_calls, detected_intent=Intent.CRM_QUERY)

        assert "incompatible" in ans.lower()
        assert meta["failure_type"] == "tool_selection_mismatch"
        mock_analytics.fetch_result.assert_not_called()

    def test_invariant_bounded_retry_for_transient_failures(self):
        """
        Invariant: Transient connector failures are retried up to MAX_RETRIES (bounded).
        If transient failure recovers on retry, retry_succeeded is True.
        """
        base_crm = CRMConnector()
        # Fails once then succeeds
        faulty = FaultInjectingConnector(base_crm, failure_mode="transient_error", fail_times=1)
        orch = LLMOrchestrator()
        orch.connector_map["get_crm_data"] = faulty

        tool_calls = [{"function": {"name": "get_crm_data", "arguments": {"status": "active"}}}]
        ans, meta = orch._execute_tool_calls(tool_calls, detected_intent=Intent.CRM_QUERY)

        assert "found" in ans.lower()
        assert meta["retry_attempted"] is True
        assert meta["retry_count"] == 1
        assert meta["retry_succeeded"] is True

    def test_invariant_no_retry_for_deterministic_argument_failure(self):
        """
        Invariant: Deterministic validation failures (e.g. invalid status enum)
        must never trigger retries.
        """
        orch = LLMOrchestrator()
        mock_crm = MagicMock()
        orch.connector_map["get_crm_data"] = mock_crm

        tool_calls = [{"function": {"name": "get_crm_data", "arguments": {"status": "unsupported_xyz"}}}]
        ans, meta = orch._execute_tool_calls(tool_calls, detected_intent=Intent.CRM_QUERY)

        assert meta["failure_type"] == "invalid_tool_arguments"
        assert meta["retry_attempted"] is False
        assert meta["retry_count"] == 0
        mock_crm.fetch_result.assert_not_called()

    def test_invariant_freshness_status_evaluations(self):
        """
        Invariant: System must accurately distinguish freshness states:
        fresh, stale_usable, too_stale, future_timestamp, unknown.
        """
        # Fresh <= 1 day
        status, warning = evaluate_freshness(3600.0, "2026-09-15T00:00:00Z")
        assert status == "fresh"
        assert warning is None

        # Stale usable (3 days)
        status, warning = evaluate_freshness(3 * 86400.0, "2026-09-12T00:00:00Z")
        assert status == "stale_usable"
        assert "3 day(s) ago" in warning

        # Too stale (14 days)
        status, warning = evaluate_freshness(14 * 86400.0, "2026-09-01T00:00:00Z")
        assert status == "too_stale"
        assert "maximum freshness window" in warning

        # Future timestamp (< 0)
        status, warning = evaluate_freshness(-500.0, "2026-09-16T00:00:00Z")
        assert status == "future_timestamp"
        assert "future" in warning

        # Unknown
        status, warning = evaluate_freshness(None, None)
        assert status == "unknown"
        assert "unknown" in warning.lower()
