"""Tests for evaluation/metrics/tool_calling.py"""
import pytest
from evaluation.metrics.tool_calling import (
    args_semantic_equal,
    args_field_accuracy,
    tool_selection_metrics,
    argument_metrics,
)


class TestSemanticEqual:
    def test_exact_match(self):
        assert args_semantic_equal({"status": "active"}, {"status": "active"}) is True

    def test_string_int_coercion(self):
        assert args_semantic_equal({"limit": 10}, {"limit": "10"}) is True

    def test_case_insensitive_string(self):
        assert args_semantic_equal({"status": "active"}, {"status": "ACTIVE"}) is True

    def test_missing_key(self):
        assert args_semantic_equal({"status": "active"}, {}) is False

    def test_extra_key_in_actual_is_wrong(self):
        assert args_semantic_equal({"status": "active"}, {"status": "active", "limit": 5}) is False

    def test_empty_both(self):
        assert args_semantic_equal({}, {}) is True

    def test_wrong_value(self):
        assert args_semantic_equal({"status": "active"}, {"status": "inactive"}) is False


class TestFieldAccuracy:
    def test_perfect(self):
        assert args_field_accuracy({"status": "active"}, {"status": "active"}) == 1.0

    def test_half_correct(self):
        acc = args_field_accuracy({"status": "active", "limit": 5}, {"status": "active", "limit": 10})
        assert abs(acc - 0.5) < 0.001

    def test_empty(self):
        assert args_field_accuracy({}, {}) == 1.0

    def test_extra_key(self):
        # expected={}, actual={extra: x} => 0/1 = 0.0
        acc = args_field_accuracy({}, {"extra": "x"})
        assert acc == 0.0


class TestToolSelectionMetrics:
    def test_perfect_selection(self):
        m = tool_selection_metrics(["get_crm_data", "get_support_tickets"], ["get_crm_data", "get_support_tickets"])
        assert m["tool_accuracy"] == 1.0

    def test_wrong_tool(self):
        m = tool_selection_metrics(["get_crm_data"], ["get_analytics"])
        assert m["wrong_tool_rate"] == 1.0
        assert m["tool_accuracy"] == 0.0

    def test_no_tool_cases_skipped(self):
        # None in expected means no tool expected (direct cases), skip
        m = tool_selection_metrics([None, "get_crm_data"], ["tool_x", "get_crm_data"])
        assert m["n_tool_cases"] == 1
        assert m["tool_accuracy"] == 1.0

    def test_all_none(self):
        m = tool_selection_metrics([None, None], [None, None])
        assert m["tool_accuracy"] is None


class TestArgumentMetrics:
    def test_args_evaluated_only_when_tool_correct(self):
        expected_tools = ["get_crm_data", "get_crm_data"]
        actual_tools = ["get_crm_data", "get_analytics"]  # second is wrong
        expected_args = [{"status": "active"}, {"status": "active"}]
        actual_args = [{"status": "active"}, {"status": "active"}]

        m = argument_metrics(expected_args, actual_args, expected_tools, actual_tools)
        # Only first case counts (correct tool)
        assert m["n_arg_cases"] == 1
        assert m["args_semantic_match_rate"] == 1.0
