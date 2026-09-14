"""
tests/conftest.py - Shared fixtures and utilities for the test suite.
"""
import io
from pathlib import Path
import numpy as np
import pytest
import soundfile as sf
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """FastAPI TestClient for route integration tests."""
    return TestClient(app)


@pytest.fixture
def valid_wav_file(tmp_path: Path) -> Path:
    """Generates a valid 1-second 16kHz mono sine-wave audio WAV file."""
    wav_path = tmp_path / "valid_sample.wav"
    sr = 16000
    t = np.linspace(0, 1.0, sr, endpoint=False)
    # 440 Hz tone
    audio = 0.5 * np.sin(2 * np.pi * 440 * t)
    sf.write(str(wav_path), audio, sr)
    return wav_path


@pytest.fixture
def short_wav_file(tmp_path: Path) -> Path:
    """Generates an audio file that is too short (< 0.1s)."""
    wav_path = tmp_path / "short_sample.wav"
    sr = 16000
    # 0.05 seconds
    audio = np.zeros(int(sr * 0.05), dtype=np.float32)
    sf.write(str(wav_path), audio, sr)
    return wav_path


@pytest.fixture
def corrupt_audio_file(tmp_path: Path) -> Path:
    """Generates a corrupt file containing invalid non-audio bytes."""
    corrupt_path = tmp_path / "corrupt.wav"
    corrupt_path.write_bytes(b"NOT_A_VALID_AUDIO_HEADER_JUNK_DATA_1234567890")
    return corrupt_path
