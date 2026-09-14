"""
tests/test_audio_validation.py - Tests for pre-processing audio validation.
"""
from pathlib import Path
import pytest
from app.failure import FailureType, PipelineError
from app.voice.audio_validation import validate_and_load


def test_valid_audio_validation(valid_wav_file: Path):
    file_size = valid_wav_file.stat().st_size
    y, sr, duration = validate_and_load(valid_wav_file, file_size)
    assert sr == 16000
    assert len(y) > 0
    assert 0.9 <= duration <= 1.1


def test_audio_too_large(valid_wav_file: Path, monkeypatch):
    # Simulate an oversized file by passing a huge byte count
    fake_large_size = 30 * 1024 * 1024  # 30MB > 25MB default
    with pytest.raises(PipelineError) as exc_info:
        validate_and_load(valid_wav_file, fake_large_size)
    assert exc_info.value.failure_type == FailureType.AUDIO_TOO_LARGE
    assert exc_info.value.status_code == 413


def test_audio_too_short(short_wav_file: Path):
    file_size = short_wav_file.stat().st_size
    with pytest.raises(PipelineError) as exc_info:
        validate_and_load(short_wav_file, file_size)
    assert exc_info.value.failure_type == FailureType.AUDIO_TOO_SHORT
    assert exc_info.value.status_code == 400


def test_audio_decode_failed(corrupt_audio_file: Path):
    file_size = corrupt_audio_file.stat().st_size
    with pytest.raises(PipelineError) as exc_info:
        validate_and_load(corrupt_audio_file, file_size)
    assert exc_info.value.failure_type == FailureType.AUDIO_DECODE_FAILED
    assert exc_info.value.status_code == 400
