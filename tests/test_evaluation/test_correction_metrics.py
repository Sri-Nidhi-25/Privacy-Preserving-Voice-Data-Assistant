"""Tests for evaluation/metrics/correction.py"""
import pytest
from evaluation.metrics.correction import correction_classification, correction_ablation_metrics


class TestCorrectionClassification:
    def test_improved(self):
        assert correction_classification(0.5, 0.2, True) == "improved"

    def test_degraded(self):
        assert correction_classification(0.2, 0.5, True) == "degraded"

    def test_unchanged(self):
        assert correction_classification(0.3, 0.3, True) == "unchanged"

    def test_not_attempted(self):
        assert correction_classification(0.3, 0.0, False) == "not_attempted"


class TestCorrectionAblationMetrics:
    def _make_records(self, corrections):
        """corrections: list of (raw_wer, corrected_wer, attempted, accepted, changed)"""
        records = []
        for i, (raw_wer, corrected_wer, attempted, accepted, changed) in enumerate(corrections):
            records.append({
                "case_id": f"case_{i}",
                "correction_attempted": attempted,
                "correction_accepted": accepted,
                "correction_rejected": not accepted if attempted else False,
                "correction_changed": changed,
                "stt_wer": raw_wer,
                "corrected_wer": corrected_wer,
                "actual_route": "tool",
                "expected_route": "tool",
                "routing_correct": True,
            })
        return records

    def test_all_improved(self):
        recs = self._make_records([
            (0.5, 0.2, True, True, True),
            (0.4, 0.1, True, True, True),
        ])
        m = correction_ablation_metrics(recs)
        assert m["n_improved"] == 2
        assert m["n_degraded"] == 0
        assert m["false_correction_rate"] == 0.0

    def test_all_degraded(self):
        recs = self._make_records([
            (0.1, 0.5, True, True, True),
            (0.2, 0.6, True, True, True),
        ])
        m = correction_ablation_metrics(recs)
        assert m["n_degraded"] == 2
        assert m["false_correction_rate"] == 1.0

    def test_none_attempted(self):
        recs = self._make_records([
            (0.3, 0.3, False, False, False),
        ])
        m = correction_ablation_metrics(recs)
        assert m["n_correction_attempted"] == 0
        assert m["attempt_rate"] == 0.0

    def test_mixed(self):
        recs = self._make_records([
            (0.5, 0.2, True, True, True),   # improved
            (0.1, 0.4, True, True, True),   # degraded
            (0.3, 0.3, True, True, False),  # unchanged
        ])
        m = correction_ablation_metrics(recs)
        assert m["n_improved"] == 1
        assert m["n_degraded"] == 1
        assert m["n_unchanged"] == 1
        assert abs(m["false_correction_rate"] - 1/3) < 0.001
