"""Tests for evaluation/calibration.py"""
import pytest
from evaluation.calibration import (
    compute_stt_reliability_score,
    evaluate_decision,
    threshold_sweep,
)


class TestSTTReliabilityScore:
    def test_high_confidence_high_score(self):
        score = compute_stt_reliability_score(avg_logprob=-0.2, no_speech_prob=0.01, compression_ratio=1.1)
        assert 0.8 <= score <= 1.0

    def test_low_confidence_low_score(self):
        score = compute_stt_reliability_score(avg_logprob=-2.0, no_speech_prob=0.75, compression_ratio=2.8)
        assert 0.0 <= score <= 0.2

    def test_monotonic_drop_with_logprob(self):
        score_high = compute_stt_reliability_score(avg_logprob=-0.3, no_speech_prob=0.05, compression_ratio=1.2)
        score_mid = compute_stt_reliability_score(avg_logprob=-1.0, no_speech_prob=0.05, compression_ratio=1.2)
        score_low = compute_stt_reliability_score(avg_logprob=-2.0, no_speech_prob=0.05, compression_ratio=1.2)
        assert score_high > score_mid > score_low

    def test_none_logprob_returns_zero(self):
        assert compute_stt_reliability_score(None, 0.5, 1.5) == 0.0


class TestDecisionMatrix:
    def test_correct_continuation(self):
        res = evaluate_decision(wer=0.05, avg_logprob=-0.3, no_speech_prob=0.02, compression_ratio=1.1)
        assert res["outcome"] == "correct_continuation"
        assert res["is_bad_stt"] is False
        assert res["system_abstained"] is False

    def test_correct_abstention(self):
        res = evaluate_decision(wer=0.75, avg_logprob=-1.5, no_speech_prob=0.8, compression_ratio=2.6)
        assert res["outcome"] == "correct_abstention"
        assert res["is_bad_stt"] is True
        assert res["system_abstained"] is True

    def test_dangerous_continuation(self):
        # High WER but good confidence signals (e.g. hallucination)
        res = evaluate_decision(wer=0.85, avg_logprob=-0.2, no_speech_prob=0.01, compression_ratio=1.1)
        assert res["outcome"] == "dangerous_continuation"
        assert res["is_bad_stt"] is True
        assert res["system_abstained"] is False

    def test_false_abstention(self):
        # Low WER (good) but breached threshold
        res = evaluate_decision(wer=0.05, avg_logprob=-1.5, no_speech_prob=0.02, compression_ratio=1.1)
        assert res["outcome"] == "false_abstention"
        assert res["is_bad_stt"] is False
        assert res["system_abstained"] is True


class TestThresholdSweep:
    def test_sweep_returns_grid(self):
        samples = [
            {"wer": 0.05, "avg_logprob": -0.2, "no_speech_prob": 0.01, "compression_ratio": 1.1},
            {"wer": 0.85, "avg_logprob": -1.8, "no_speech_prob": 0.75, "compression_ratio": 2.7},
            {"wer": 0.00, "avg_logprob": -0.4, "no_speech_prob": 0.02, "compression_ratio": 1.2},
            {"wer": 0.65, "avg_logprob": -1.2, "no_speech_prob": 0.40, "compression_ratio": 2.1},
        ]
        results = threshold_sweep(
            samples,
            logprob_thresholds=[-1.5, -1.0],
            no_speech_thresholds=[0.6],
            compression_thresholds=[2.4],
        )
        assert len(results) == 2
        for r in results:
            assert "precision" in r
            assert "recall" in r
            assert "dangerous_continuation_rate" in r
            assert "brier_score" in r
