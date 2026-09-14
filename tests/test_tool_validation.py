"""
tests/test_tool_validation.py - Tests for tool argument validation and safety invariant.
"""
from unittest.mock import MagicMock
from app.services.llm_orchestrator import _validate_args, _coerce_args, LLMOrchestrator


def test_valid_crm_arguments():
    valid, err = _validate_args("get_crm_data", {"status": "active", "limit": 10})
    assert valid is True
    assert err == ""


def test_invalid_crm_enum():
    valid, err = _validate_args("get_crm_data", {"status": "pending"})
    assert valid is False
    assert "status" in err


def test_unexpected_argument():
    valid, err = _validate_args("get_crm_data", {"status": "active", "unknown_arg": 123})
    assert valid is False
    assert "Unexpected argument" in err


def test_integer_coercion():
    coerced = _coerce_args("get_crm_data", {"limit": "25"})
    assert coerced["limit"] == 25
    assert isinstance(coerced["limit"], int)


def test_tool_safety_invariant_connector_never_called_on_invalid_args():
    """
    CRITICAL INVARIANT:
    An invalid tool call must NEVER reach a connector.
    """
    orchestrator = LLMOrchestrator.__new__(LLMOrchestrator)
    mock_crm = MagicMock()
    mock_support = MagicMock()
    mock_analytics = MagicMock()

    orchestrator.connector_map = {
        "get_crm_data": mock_crm,
        "get_support_tickets": mock_support,
        "get_analytics": mock_analytics,
    }

    # Invalid tool call: status="invalid_status"
    tool_calls = [
        {
            "function": {
                "name": "get_crm_data",
                "arguments": {"status": "disallowed_status_value"},
            }
        }
    ]

    answer, metadata = orchestrator._execute_tool_calls(tool_calls)

    # Invariant assertion: Neither fetch nor fetch_result may EVER be called!
    assert mock_crm.fetch.called is False
    assert mock_crm.fetch_result.called is False
    assert "validation_error" in metadata
    assert "couldn't interpret" in answer.lower()
