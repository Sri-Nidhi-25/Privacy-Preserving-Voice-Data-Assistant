"""
tests/test_stt.py - Tests for Speech-to-Text engine and confidence signals.
"""
from pathlib import Path
from unittest.mock import MagicMock
import pytest
from app.voice.stt import STTEngine


def test_stt_transcribe_confidence_signals(monkeypatch, valid_wav_file: Path):
    # Mock the internal whisper model to test decoding output logic quickly.
    # Inject via _model (the private backing attr) because .model is a lazy property.
    engine = STTEngine.__new__(STTEngine)
    mock_model = MagicMock()
    mock_model.transcribe.return_value = {
        "text": "Show me active customers",
        "segments": [
            {"avg_logprob": -0.25, "no_speech_prob": 0.01, "compression_ratio": 1.1}
        ],
    }
    engine._model = mock_model

    text, conf = engine.transcribe_with_confidence(valid_wav_file)
    assert text == "Show me active customers"
    assert conf["low_confidence"] is False
    assert conf["avg_logprob"] == -0.25
    assert conf["no_speech_prob"] == 0.01


def test_stt_low_confidence_detection(monkeypatch, valid_wav_file: Path):
    engine = STTEngine.__new__(STTEngine)
    mock_model = MagicMock()
    # Bad avg_logprob (< -1.0) indicates hallucination / unreliable speech
    mock_model.transcribe.return_value = {
        "text": "garbled noisy hallucination",
        "segments": [
            {"avg_logprob": -1.45, "no_speech_prob": 0.02, "compression_ratio": 1.2}
        ],
    }
    engine._model = mock_model

    text, conf = engine.transcribe_with_confidence(valid_wav_file)
    assert conf["low_confidence"] is True


def test_stt_empty_segments_low_confidence(valid_wav_file: Path):
    engine = STTEngine.__new__(STTEngine)
    mock_model = MagicMock()
    mock_model.transcribe.return_value = {"text": "", "segments": []}
    engine._model = mock_model

    text, conf = engine.transcribe_with_confidence(valid_wav_file)
    assert conf["low_confidence"] is True
    assert conf["no_speech_prob"] == 1.0
