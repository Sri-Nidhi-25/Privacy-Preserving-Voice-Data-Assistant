"""Tests for evaluation/schemas.py"""
import json
import pytest
from evaluation.schemas import EvalRecord


def _minimal_record(**kwargs):
    base = dict(
        run_id="abc12345",
        case_id="crm_001",
        dataset_id="voice_eval_v1.jsonl",
        dataset_version="v1",
        timestamp="2024-01-01T00:00:00Z",
        git_commit="abc1234",
        python_version="3.11.0",
    )
    base.update(kwargs)
    return EvalRecord(**base)


class TestEvalRecord:
    def test_creation(self):
        r = _minimal_record()
        assert r.case_id == "crm_001"
        assert r.privacy_metric == "not_yet_measured"

    def test_to_dict(self):
        r = _minimal_record()
        d = r.to_dict()
        assert isinstance(d, dict)
        assert d["case_id"] == "crm_001"

    def test_to_json(self):
        r = _minimal_record()
        s = r.to_json()
        parsed = json.loads(s)
        assert parsed["case_id"] == "crm_001"

    def test_default_fields(self):
        r = _minimal_record()
        assert r.expected_args == {}
        assert r.latency_ms == {}
        assert r.end_to_end_success is None
        assert r.failure_stage is None

    def test_privacy_placeholder(self):
        r = _minimal_record()
        assert r.privacy_metric == "not_yet_measured"
