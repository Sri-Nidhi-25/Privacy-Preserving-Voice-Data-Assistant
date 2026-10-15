"""
tests/test_tool_validation.py - Tests for tool argument validation and safety invariant.
"""
from unittest.mock import MagicMock
from app.services.llm_orchestrator import (
    _validate_args,
    _coerce_args,
    _normalize_no_priority,
    LLMOrchestrator,
)


# ── Existing validation tests ─────────────────────────────────────────────────

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


# ── Tests for _normalize_no_priority ─────────────────────────────────────────

def test_normalize_no_priority_maps_to_low():
    """'no priority' phrase must map to 'low' as per domain rules."""
    args = {"status": "closed", "priority": "no priority"}
    result = _normalize_no_priority(args)
    assert result.get("priority") == "low"
    assert result.get("status") == "closed"


def test_normalize_no_priority_synonyms():
    """All recognised synonyms must map to 'low'."""
    for phrase in ["none", "no", "n/a", "na", "no priority", "NO PRIORITY", "without priority", "None"]:
        args = {"priority": phrase}
        result = _normalize_no_priority(args)
        assert result.get("priority") == "low", f"Phrase '{phrase}' was NOT normalised to 'low'"


def test_normalize_no_priority_keeps_valid_priority():
    """Valid priority values must be left untouched."""
    for valid in ["low", "medium", "high"]:
        args = {"priority": valid}
        result = _normalize_no_priority(args)
        assert result.get("priority") == valid, f"Valid priority '{valid}' was wrongly changed"


def test_normalize_no_priority_no_key():
    """Args without a priority key must be returned unchanged."""
    args = {"status": "open", "limit": 10}
    result = _normalize_no_priority(args)
    assert result == {"status": "open", "limit": 10}


def test_no_priority_passes_full_validation():
    """'no priority' must not cause a validation error when normalised first."""
    args = {"status": "closed", "priority": "no priority", "month": "march"}
    args = _normalize_no_priority(args)
    valid, err = _validate_args("get_support_tickets", args)
    assert valid is True, f"Unexpected validation error: {err}"
    assert args.get("priority") == "low"


def test_limit_coercion_non_numeric_strings_dropped():
    """Non-numeric strings like 'count', 'all', 'how many' must drop limit so query retrieves all."""
    for val in ["count", "all", "how many", "none", "total", "n/a", "", "unlimited"]:
        coerced = _coerce_args("get_crm_data", {"status": "inactive", "limit": val})
        assert "limit" not in coerced or isinstance(coerced["limit"], int)
        valid, err = _validate_args("get_crm_data", coerced)
        assert valid is True, f"Failed on limit={val}: {err}"


def test_limit_coercion_embedded_number():
    """Strings containing numbers like 'top 10' or '15 records' should coerce to integer."""
    coerced = _coerce_args("get_crm_data", {"limit": "top 15 records"})
    assert coerced["limit"] == 15
    valid, err = _validate_args("get_crm_data", coerced)
    assert valid is True
