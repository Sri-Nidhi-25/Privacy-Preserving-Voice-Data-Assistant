"""Integration tests for the routing runner (text-only, no audio, no LLM)."""
import json
import pytest
from pathlib import Path
import tempfile
import os

from evaluation.runners.routing_runner import load_dataset, evaluate_routing_component

DATASET_PATH = Path("evaluation/datasets/voice_eval_v1.jsonl")


@pytest.fixture(scope="module")
def cases():
    return load_dataset(DATASET_PATH)


class TestLoadDataset:
    def test_loads_all_cases(self, cases):
        assert len(cases) >= 20

    def test_required_fields(self, cases):
        for c in cases:
            assert "case_id" in c
            assert "input_text" in c
            assert "expected_route" in c


class TestRoutingComponent:
    def test_returns_result_for_each_case(self, cases):
        results = evaluate_routing_component(cases)
        assert len(results) == len(cases)

    def test_result_fields_present(self, cases):
        results = evaluate_routing_component(cases)
        for r in results:
            assert "case_id" in r
            assert "actual_route" in r
            assert "routing_correct" in r
            assert r["actual_route"] in ("tool", "direct")

    def test_data_queries_routed_to_tool(self):
        # Strong data keywords should always route to tool
        strong_data_cases = [
            {"case_id": "t1", "input_text": "Show me all active customers", "expected_route": "tool"},
            {"case_id": "t2", "input_text": "Get support tickets", "expected_route": "tool"},
        ]
        results = evaluate_routing_component(strong_data_cases)
        for r in results:
            assert r["actual_route"] == "tool", f"Expected tool route for {r['case_id']}"

    def test_general_questions_routed_direct(self):
        # Pure general questions should route to direct
        general_cases = [
            {"case_id": "g1", "input_text": "What is the capital of France", "expected_route": "direct"},
            {"case_id": "g2", "input_text": "Tell me a joke", "expected_route": "direct"},
        ]
        results = evaluate_routing_component(general_cases)
        for r in results:
            assert r["actual_route"] == "direct", f"Expected direct route for {r['case_id']}"

    def test_routing_accuracy_above_threshold(self, cases):
        """Routing accuracy should be at least 50% on the dataset."""
        results = evaluate_routing_component(cases)
        correct = sum(1 for r in results if r["routing_correct"])
        accuracy = correct / len(results)
        assert accuracy >= 0.5, f"Routing accuracy {accuracy:.1%} is too low"
