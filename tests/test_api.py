"""
tests/test_api.py - Integration and failure path tests for FastAPI endpoints.
"""
from pathlib import Path
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from app.config import settings
from app.routers import voice


def test_api_unauthorized(client: TestClient, valid_wav_file: Path):
    with open(valid_wav_file, "rb") as f:
        res = client.post(
            "/voice/query",
            files={"audio_file": ("test.wav", f, "audio/wav")},
            headers={"api-key": "wrong-key"},
        )
    assert res.status_code == 401


def test_api_unsupported_content_type(client: TestClient, valid_wav_file: Path):
    with open(valid_wav_file, "rb") as f:
        res = client.post(
            "/voice/query",
            files={"audio_file": ("test.wav", f, "text/plain")},
            headers={"api-key": settings.API_KEY},
        )
    assert res.status_code == 400


def test_api_undecodable_audio(client: TestClient, corrupt_audio_file: Path):
    with open(corrupt_audio_file, "rb") as f:
        res = client.post(
            "/voice/query",
            files={"audio_file": ("corrupt.wav", f, "audio/wav")},
            headers={"api-key": settings.API_KEY},
        )
    assert res.status_code == 400
    assert "decode" in res.json()["detail"]["error"]


def test_api_successful_end_to_end_mocked(client: TestClient, valid_wav_file: Path, monkeypatch):
    # Mock STT and TTS to keep test fast and isolated
    mock_stt = MagicMock()
    mock_stt.transcribe_with_confidence.return_value = (
        "how many active customers",
        {"avg_logprob": -0.2, "no_speech_prob": 0.01, "compression_ratio": 1.0, "low_confidence": False},
    )
    monkeypatch.setattr(voice, "stt", mock_stt)

    # Mock synthesize to avoid remote network dependency in test
    async def mock_synth(text, path):
        path.write_bytes(b"MOCK_MP3_DATA")
    monkeypatch.setattr(voice, "_synthesize_and_verify", mock_synth)

    with open(valid_wav_file, "rb") as f:
        res = client.post(
            "/voice/query",
            files={"audio_file": ("query.wav", f, "audio/wav")},
            headers={"api-key": settings.API_KEY},
        )

    assert res.status_code == 200
    data = res.json()
    assert "transcript" in data
    assert "answer_text" in data
    assert "metadata" in data

    meta = data["metadata"]
    assert "request_id" in meta
    assert "latency_ms" in meta
    assert "validation" in meta["latency_ms"]
    assert "total" in meta["latency_ms"]


def test_api_temp_file_cleanup(client: TestClient, valid_wav_file: Path, monkeypatch):
    """Ensure raw uploads and intermediate input WAV files are cleaned from temp_audio."""
    temp_dir = Path("temp_audio")
    initial_files = set(temp_dir.glob("*.input.wav"))

    mock_stt = MagicMock()
    mock_stt.transcribe_with_confidence.return_value = (
        "hello",
        {"avg_logprob": -0.2, "no_speech_prob": 0.01, "compression_ratio": 1.0, "low_confidence": False},
    )
    monkeypatch.setattr(voice, "stt", mock_stt)

    async def mock_synth(text, path):
        path.write_bytes(b"MOCK")
    monkeypatch.setattr(voice, "_synthesize_and_verify", mock_synth)

    with open(valid_wav_file, "rb") as f:
        client.post(
            "/voice/query",
            files={"audio_file": ("query.wav", f, "audio/wav")},
            headers={"api-key": settings.API_KEY},
        )

    # All intermediate .input.wav files must be cleaned up in finally block
    current_input_files = set(temp_dir.glob("*.input.wav"))
    assert current_input_files == initial_files
