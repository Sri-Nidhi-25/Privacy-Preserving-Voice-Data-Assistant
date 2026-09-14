"""Tests for evaluation/metrics/routing.py"""
import pytest
from evaluation.metrics.routing import routing_metrics


class TestRoutingMetrics:
    def test_perfect_accuracy(self):
        exp = ["tool", "tool", "direct", "direct"]
        act = ["tool", "tool", "direct", "direct"]
        m = routing_metrics(exp, act)
        assert m["accuracy"] == 1.0
        assert m["f1"] == 1.0
        assert m["false_positive_rate"] == 0.0
        assert m["false_negative_rate"] == 0.0

    def test_all_wrong(self):
        exp = ["tool", "direct"]
        act = ["direct", "tool"]
        m = routing_metrics(exp, act)
        assert m["accuracy"] == 0.0
        assert m["tp"] == 0 and m["tn"] == 0

    def test_false_positive(self):
        exp = ["direct"]
        act = ["tool"]
        m = routing_metrics(exp, act)
        assert m["fp"] == 1
        assert m["false_positive_rate"] == 1.0
        assert m["precision"] == 0.0

    def test_false_negative(self):
        exp = ["tool"]
        act = ["direct"]
        m = routing_metrics(exp, act)
        assert m["fn"] == 1
        assert m["false_negative_rate"] == 1.0
        assert m["recall"] == 0.0

    def test_mixed(self):
        # 2 TP, 1 FP, 1 TN, 1 FN  (5 total)
        exp = ["tool", "tool", "direct", "direct", "tool"]
        act = ["tool", "direct", "tool", "direct", "tool"]
        # TP=2 (0 and 4), FN=1 (1), FP=1 (2), TN=1 (3)
        m = routing_metrics(exp, act)
        assert m["tp"] == 2
        assert m["fn"] == 1
        assert m["fp"] == 1
        assert m["tn"] == 1
        assert m["accuracy"] == pytest.approx(3 / 5, abs=0.001)

    def test_mismatched_lengths_raises(self):
        with pytest.raises(AssertionError):
            routing_metrics(["tool"], ["tool", "direct"])
