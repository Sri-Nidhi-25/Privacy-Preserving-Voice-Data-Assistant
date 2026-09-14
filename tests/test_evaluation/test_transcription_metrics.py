"""Tests for evaluation/metrics/transcription.py"""
import pytest
from evaluation.metrics.transcription import compute_wer, compute_cer, compute_metrics


class TestNormalization:
    def test_case_insensitive(self):
        assert compute_wer("Hello World", "hello world") == 0.0

    def test_punctuation_stripped(self):
        assert compute_wer("Hello, world!", "hello world") == 0.0

    def test_extra_whitespace(self):
        assert compute_wer("hello  world", "hello world") == 0.0


class TestWER:
    def test_perfect_match(self):
        assert compute_wer("show me active customers", "show me active customers") == 0.0

    def test_one_substitution(self):
        # "show me inactive customers" vs "show me active customers" => 1 sub / 4 words
        wer = compute_wer("show me active customers", "show me inactive customers")
        assert abs(wer - 0.25) < 0.001

    def test_one_deletion(self):
        # ref = "show me active customers", hyp = "show active customers" => 1 del / 4
        wer = compute_wer("show me active customers", "show active customers")
        assert abs(wer - 0.25) < 0.001

    def test_one_insertion(self):
        # ref = "show active customers", hyp = "please show active customers" => 1 ins / 3
        wer = compute_wer("show active customers", "please show active customers")
        assert abs(wer - 1/3) < 0.001

    def test_empty_both(self):
        assert compute_wer("", "") == 0.0

    def test_empty_hypothesis(self):
        # All words deleted
        wer = compute_wer("show customers", "")
        assert wer == 1.0

    def test_high_wer(self):
        wer = compute_wer("show me active customers", "random irrelevant noise text")
        assert wer > 0.5


class TestCER:
    def test_perfect_match(self):
        assert compute_cer("hello", "hello") == 0.0

    def test_one_substitution(self):
        # "hello" vs "hxllo" => 1/5
        cer = compute_cer("hello", "hxllo")
        assert abs(cer - 0.2) < 0.001

    def test_empty_both(self):
        assert compute_cer("", "") == 0.0


class TestComputeMetrics:
    def test_returns_all_fields(self):
        m = compute_metrics("hello world", "hello world")
        assert "wer" in m
        assert "cer" in m
        assert "reference_normalized" in m
        assert "hypothesis_normalized" in m

    def test_values_match_individual(self):
        ref, hyp = "show me active customers", "show me all customers"
        m = compute_metrics(ref, hyp)
        assert m["wer"] == round(compute_wer(ref, hyp), 4)
        assert m["cer"] == round(compute_cer(ref, hyp), 4)
