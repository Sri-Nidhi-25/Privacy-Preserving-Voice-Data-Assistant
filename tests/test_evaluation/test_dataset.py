"""Tests for the evaluation dataset - validate format and ground truth quality."""
import json
from pathlib import Path
import pytest

DATASET_PATH = Path("evaluation/datasets/voice_eval_v1.jsonl")

REQUIRED_FIELDS = {"case_id", "category", "input_text", "expected_route", "expected_args"}
VALID_CATEGORIES = {"data_query", "non_data_query", "adversarial", "ambiguous", "stt_sensitive", "boundary"}
VALID_ROUTES = {"tool", "direct"}
VALID_TOOLS = {"get_crm_data", "get_support_tickets", "get_analytics", None}


@pytest.fixture(scope="module")
def cases():
    assert DATASET_PATH.exists(), f"Dataset not found: {DATASET_PATH}"
    loaded = []
    with open(DATASET_PATH, encoding="utf-8-sig") as f:
        for i, line in enumerate(f):
            line = line.strip()
            if line:
                loaded.append((i + 1, json.loads(line)))
    return loaded


class TestDatasetStructure:
    def test_dataset_not_empty(self, cases):
        assert len(cases) >= 20, "Dataset should have at least 20 cases"

    def test_required_fields_present(self, cases):
        for lineno, case in cases:
            missing = REQUIRED_FIELDS - set(case.keys())
            assert not missing, f"Line {lineno}: missing fields {missing}"

    def test_unique_case_ids(self, cases):
        ids = [case["case_id"] for _, case in cases]
        assert len(ids) == len(set(ids)), "Duplicate case_ids found"

    def test_valid_categories(self, cases):
        for lineno, case in cases:
            assert case["category"] in VALID_CATEGORIES, (
                f"Line {lineno}: unknown category {case['category']!r}"
            )

    def test_valid_routes(self, cases):
        for lineno, case in cases:
            assert case["expected_route"] in VALID_ROUTES, (
                f"Line {lineno}: unknown route {case['expected_route']!r}"
            )

    def test_tool_consistent_with_route(self, cases):
        for lineno, case in cases:
            if case["expected_route"] == "direct":
                assert case.get("expected_tool") is None, (
                    f"Line {lineno}: direct route should have null tool"
                )
            else:
                assert case.get("expected_tool") is not None, (
                    f"Line {lineno}: tool route should have a non-null tool"
                )

    def test_expected_tool_is_valid(self, cases):
        for lineno, case in cases:
            assert case.get("expected_tool") in VALID_TOOLS, (
                f"Line {lineno}: unknown tool {case.get('expected_tool')!r}"
            )

    def test_expected_args_is_dict(self, cases):
        for lineno, case in cases:
            assert isinstance(case.get("expected_args", {}), dict), (
                f"Line {lineno}: expected_args must be a dict"
            )

    def test_dataset_has_all_categories(self, cases):
        found = {case["category"] for _, case in cases}
        for cat in ["data_query", "non_data_query", "adversarial"]:
            assert cat in found, f"Dataset missing category: {cat}"

    def test_no_empty_input_text(self, cases):
        for lineno, case in cases:
            assert case["input_text"].strip(), f"Line {lineno}: empty input_text"
