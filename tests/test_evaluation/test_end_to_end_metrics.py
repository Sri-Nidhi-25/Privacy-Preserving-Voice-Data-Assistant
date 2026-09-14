"""Tests for evaluation/metrics/end_to_end.py"""
import pytest
from evaluation.metrics.end_to_end import (
    compute_e2e_success,
    classify_failure_stage,
    end_to_end_metrics,
)


def _make_record(**kwargs):
    base = {
        "case_id": "test_case",
        "category": "data_query",
        "expected_route": "tool",
        "expected_tool": "get_crm_data",
        "expected_args": {"status": "active"},
        "actual_route": "tool",
        "routing_correct": True,
        "actual_tool": "get_crm_data",
        "tool_selection_correct": True,
        "actual_args": {"status": "active"},
        "args_semantic_match": True,
        "args_field_accuracy": 1.0,
        "connector_success": True,
        "answer_text": "You have 5 active customers.",
        "result_count": 5,
        "end_to_end_success": None,
        "failure_stage": None,
        "stt_low_confidence_decision": False,
    }
    base.update(kwargs)
    return base


class TestComputeE2ESuccess:
    def test_full_tool_success(self):
        r = _make_record()
        assert compute_e2e_success(r) is True

    def test_direct_success(self):
        r = _make_record(expected_route="direct", actual_route="direct",
                         routing_correct=True, expected_tool=None,
                         tool_selection_correct=None, args_semantic_match=None,
                         expected_args={}, connector_success=None,
                         answer_text="Paris is the capital of France.")
        assert compute_e2e_success(r) is True

    def test_routing_failure_causes_e2e_fail(self):
        r = _make_record(routing_correct=False)
        assert compute_e2e_success(r) is False

    def test_wrong_tool_causes_e2e_fail(self):
        r = _make_record(tool_selection_correct=False, actual_tool="get_analytics")
        assert compute_e2e_success(r) is False

    def test_bad_args_causes_e2e_fail(self):
        r = _make_record(args_semantic_match=False, actual_args={"status": "inactive"})
        assert compute_e2e_success(r) is False

    def test_no_answer_causes_e2e_fail(self):
        r = _make_record(answer_text="")
        assert compute_e2e_success(r) is False

    def test_empty_expected_args_always_pass(self):
        r = _make_record(expected_args={}, args_semantic_match=False)
        assert compute_e2e_success(r) is True  # empty args => no arg check needed


class TestClassifyFailureStage:
    def test_success_returns_none(self):
        r = _make_record(end_to_end_success=True)
        assert classify_failure_stage(r) is None

    def test_routing_failure(self):
        r = _make_record(end_to_end_success=False, routing_correct=False)
        assert classify_failure_stage(r) == "routing"

    def test_tool_selection_failure(self):
        r = _make_record(end_to_end_success=False, routing_correct=True,
                         tool_selection_correct=False)
        assert classify_failure_stage(r) == "tool_selection"

    def test_arg_failure(self):
        r = _make_record(end_to_end_success=False, routing_correct=True,
                         tool_selection_correct=True, args_semantic_match=False)
        assert classify_failure_stage(r) == "tool_arguments"

    def test_stt_abstention(self):
        r = _make_record(end_to_end_success=False, stt_low_confidence_decision=True)
        assert classify_failure_stage(r) == "stt_abstention"


class TestEndToEndMetrics:
    def test_all_success(self):
        records = [_make_record(end_to_end_success=True) for _ in range(5)]
        m = end_to_end_metrics(records)
        assert m["task_success_rate"] == 1.0

    def test_all_fail(self):
        records = [_make_record(end_to_end_success=False, routing_correct=False,
                                failure_stage="routing") for _ in range(3)]
        m = end_to_end_metrics(records)
        assert m["task_success_rate"] == 0.0
        assert m["failure_stage_breakdown"].get("routing") == 3

    def test_empty(self):
        m = end_to_end_metrics([])
        assert m["n"] == 0
