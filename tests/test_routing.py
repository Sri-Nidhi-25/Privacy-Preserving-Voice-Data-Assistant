"""
tests/test_routing.py - Tests for query classification and routing.
"""
from app.services.llm_orchestrator import _is_data_query


def test_crm_routing():
    assert _is_data_query("How many active customers do we have?") is True
    assert _is_data_query("Show me inactive customers") is True


def test_support_routing():
    assert _is_data_query("List all high priority open tickets") is True
    assert _is_data_query("Show me closed support tickets") is True


def test_analytics_routing():
    assert _is_data_query("What is the daily active users trend?") is True
    assert _is_data_query("Give me the average metric for users") is True


def test_non_data_routing():
    assert _is_data_query("What is the capital of France?") is False
    assert _is_data_query("Tell me a funny joke") is False
    assert _is_data_query("What is the weather outside today?") is False
