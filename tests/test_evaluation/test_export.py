"""Tests for evaluation/reporting/export.py"""
import json
import csv
from pathlib import Path
import tempfile
import pytest

from evaluation.reporting.export import save_run_results
from evaluation.schemas import EvalRecord


def _make_record(case_id="test_001"):
    return EvalRecord(
        run_id="run123",
        case_id=case_id,
        dataset_id="voice_eval_v1.jsonl",
        dataset_version="v1",
        timestamp="2024-01-01T00:00:00Z",
        git_commit="abc1234",
        python_version="3.11.0",
        input_text="Show me active customers",
        expected_route="tool",
        expected_tool="get_crm_data",
        expected_args={"status": "active"},
        actual_route="tool",
        routing_correct=True,
        end_to_end_success=True,
    )


class TestSaveRunResults:
    def test_creates_output_files(self, tmp_path):
        records = [_make_record("a"), _make_record("b")]
        summary = {
            "run_metadata": {"run_id": "run123", "timestamp": "2024-01-01T00:00:00Z"},
            "n_cases": 2,
        }
        out_dir = save_run_results("run123", records, summary, tmp_path)
        assert (out_dir / "metadata.json").exists()
        assert (out_dir / "cases.jsonl").exists()
        assert (out_dir / "summary.json").exists()
        assert (out_dir / "results.csv").exists()

    def test_cases_jsonl_valid(self, tmp_path):
        records = [_make_record("x")]
        summary = {"run_metadata": {"run_id": "runX"}, "n_cases": 1}
        out_dir = save_run_results("runX", records, summary, tmp_path)
        lines = (out_dir / "cases.jsonl").read_text(encoding="utf-8").splitlines()
        assert len(lines) == 1
        case = json.loads(lines[0])
        assert case["case_id"] == "x"

    def test_csv_has_headers(self, tmp_path):
        records = [_make_record("y")]
        summary = {"run_metadata": {"run_id": "runY"}, "n_cases": 1}
        out_dir = save_run_results("runY", records, summary, tmp_path)
        with open(out_dir / "results.csv", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        assert len(rows) == 1
        assert "case_id" in rows[0]

    def test_unique_run_dirs(self, tmp_path):
        records = [_make_record("z")]
        summary = {"run_metadata": {"run_id": "runZ1"}, "n_cases": 1}
        d1 = save_run_results("runZ1", records, summary, tmp_path)
        d2 = save_run_results("runZ2", records, summary, tmp_path)
        assert d1 != d2
