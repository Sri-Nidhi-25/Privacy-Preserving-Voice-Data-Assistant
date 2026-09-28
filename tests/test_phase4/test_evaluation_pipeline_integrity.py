"""
tests/test_phase4/test_evaluation_pipeline_integrity.py

Validates the evaluation framework itself against corrupted schemas,
division-by-zero edge cases, malformed records, and out-of-bounds metrics.
Ensures evaluation failures are caught and surfaced deterministically
rather than producing silent metric corruption.
"""
import pytest
import json
from dataclasses import asdict

from evaluation.schemas import EvalRecord, DATASET_VERSION, EVAL_VERSION
from evaluation.metrics.transcription import compute_wer, compute_cer
from evaluation.metrics.routing import routing_metrics
from evaluation.metrics.tool_calling import tool_selection_metrics, argument_metrics
from evaluation.metrics.correction import correction_ablation_metrics
from evaluation.calibration import compute_stt_reliability_score, evaluate_decision


class TestSchemaIntegrity:
    def test_eval_record_valid_serialization(self):
        rec = EvalRecord(
            run_id="test_run",
            case_id="case_001",
            dataset_id="voice_eval",
            dataset_version=DATASET_VERSION,
            timestamp="2026-09-28T00:00:00Z",
            git_commit="abcdef",
            python_version="3.11",
            input_text="Show active customers",
            category="data_query",
            expected_route="tool",
            expected_tool="get_crm_data",
            expected_args={"status": "active"},
        )
        d = rec.to_dict()
        assert isinstance(d, dict)
        assert d["case_id"] == "case_001"

        json_str = rec.to_json()
        assert "case_001" in json_str

        # Roundtrip
        rec_back = EvalRecord.from_dict(json.loads(json_str))
        assert rec_back.case_id == rec.case_id
        assert rec_back.expected_args == {"status": "active"}

    def test_eval_record_ignores_extra_corrupted_fields(self):
        corrupted_dict = {
            "run_id": "r1",
            "case_id": "c1",
            "dataset_id": "d1",
            "dataset_version": "v1",
            "timestamp": "now",
            "git_commit": "123",
            "python_version": "3.11",
            "non_existent_exploit_field": "dangerous_payload",
        }
        rec = EvalRecord.from_dict(corrupted_dict)
        assert rec.case_id == "c1"
        assert not hasattr(rec, "non_existent_exploit_field")

    def test_missing_mandatory_provenance_raises(self):
        with pytest.raises(TypeError):
            # Missing required non-default fields like run_id, case_id, etc.
            EvalRecord()


class TestMetricsRobustness:
    def test_wer_empty_strings(self):
        assert compute_wer("", "") == 0.0
        assert compute_wer("hello world", "") == 1.0
        # Empty reference with non-empty hypothesis
        assert compute_wer("", "hello") >= 1.0

    def test_cer_empty_strings(self):
        assert compute_cer("", "") == 0.0
        assert compute_cer("abc", "") == 1.0
        assert compute_cer("", "abc") >= 1.0

    def test_routing_metrics_empty_list(self):
        m = routing_metrics([], [])
        assert m["accuracy"] == 0.0
        assert m["n"] == 0

    def test_routing_metrics_zero_positives(self):
        # All negatives
        exp = ["direct", "direct"]
        act = ["direct", "direct"]
        m = routing_metrics(exp, act)
        assert m["accuracy"] == 1.0
        assert m["false_positive_rate"] == 0.0
        assert m["recall"] == 0.0

    def test_tool_selection_metrics_empty(self):
        m = tool_selection_metrics([], [])
        assert m["tool_accuracy"] is None
        assert m["n_tool_cases"] == 0

    def test_argument_metrics_empty(self):
        m = argument_metrics([], [], [], [])
        assert m["args_exact_match_rate"] is None
        assert m["n_arg_cases"] == 0

    def test_correction_metrics_empty(self):
        m = correction_ablation_metrics([])
        assert m["attempt_rate"] is None
        assert m["n_total"] == 0


class TestCalibrationIntegrity:
    def test_stt_reliability_clamping(self):
        # Probabilities outside normal [0, 1] or extreme compression
        score_high = compute_stt_reliability_score(avg_logprob=0.0, no_speech_prob=0.0, compression_ratio=1.0)
        assert 0.0 <= score_high <= 1.0

        score_low = compute_stt_reliability_score(avg_logprob=-10.0, no_speech_prob=0.99, compression_ratio=5.0)
        assert 0.0 <= score_low <= 1.0
        assert score_low < score_high

    def test_decision_evaluation(self):
        # Good STT and system continued
        res1 = evaluate_decision(wer=0.05, avg_logprob=-0.2, no_speech_prob=0.05, compression_ratio=1.2)
        assert res1["outcome"] == "correct_continuation"
        assert not res1["is_bad_stt"]
        assert not res1["system_abstained"]

        # Bad STT and system abstained
        res2 = evaluate_decision(wer=0.85, avg_logprob=-1.8, no_speech_prob=0.7, compression_ratio=1.5)
        assert res2["outcome"] == "correct_abstention"
        assert res2["is_bad_stt"]
        assert res2["system_abstained"]
