"""Tests for app/services/correction_guard.py"""
import pytest
from app.services.correction_guard import (
    validate_correction,
    apply_correction_gate,
    CorrectionDecision,
    extract_numbers,
    looks_like_refusal_or_commentary,
)


class TestCorrectionValidation:
    def test_valid_phonetic_correction(self):
        raw = "Show me all ack-tive customers"
        corr = "Show me all active customers"
        valid, reason = validate_correction(raw, corr)
        assert valid is True
        assert reason is None

    def test_polar_inversion_active_to_inactive(self):
        raw = "Show me active customers"
        corr = "Show me inactive customers"
        valid, reason = validate_correction(raw, corr)
        assert valid is False
        assert "intent_inversion_active_to_inactive" in reason

    def test_polar_inversion_open_to_closed(self):
        raw = "List all open tickets"
        corr = "List all closed tickets"
        valid, reason = validate_correction(raw, corr)
        assert valid is False
        assert "intent_inversion_open_to_closed" in reason

    def test_number_tampering(self):
        raw = "Give me 1 support ticket"
        corr = "Give me 100 support tickets"
        valid, reason = validate_correction(raw, corr)
        assert valid is False
        assert reason in ("invented_numbers", "altered_numbers")

    def test_number_invention(self):
        raw = "Show me customers"
        corr = "Show me 50 customers"
        valid, reason = validate_correction(raw, corr)
        assert valid is False
        assert "invented_numbers" in reason

    def test_excessive_expansion(self):
        raw = "Show active customers"
        corr = "Sure! Here is the complete list of active customers that you requested from the company customer database."
        valid, reason = validate_correction(raw, corr)
        assert valid is False
        assert "excessive_expansion" in reason or "refusal_or_commentary" in reason

    def test_excessive_truncation(self):
        raw = "Show me all the high priority open support tickets right now"
        corr = "Tickets"
        valid, reason = validate_correction(raw, corr)
        assert valid is False
        assert "excessive_truncation" in reason

    def test_refusal_commentary(self):
        raw = "List accounts"
        corr = "I apologize, as an AI language model I cannot assist with this."
        valid, reason = validate_correction(raw, corr)
        assert valid is False
        assert "refusal_or_commentary" in reason


class TestCorrectionGate:
    def test_gate_accepts_valid_correction(self):
        raw = "Show me all ack-tive customers"
        corr = "Show me all active customers"
        decision, text, reason = apply_correction_gate(raw, corr)
        assert decision == CorrectionDecision.ACCEPT_CORRECTION
        assert text == corr
        assert reason is None

    def test_gate_rejects_and_preserves_raw(self):
        raw = "Show me all active customers"
        corr = "Show me all inactive customers"
        decision, text, reason = apply_correction_gate(raw, corr)
        assert decision == CorrectionDecision.KEEP_RAW
        assert text == raw
        assert reason is not None
