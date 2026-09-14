"""
tests/test_invariants.py - Explicit verification of core reliability invariants.
"""
from pathlib import Path
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from app.config import settings
from app.routers import voice
from app.services.llm_orchestrator import LLMOrchestrator, correct_transcript


def test_invariant_low_confidence_stt_abstains_from_orchestrator(client: TestClient, valid_wav_file: Path, monkeypatch):
    """
    Invariant: Low-confidence transcription must never silently trigger data queries.
    """
    mock_stt = MagicMock()
    mock_stt.transcribe_with_confidence.return_value = (
        "unreliable noise",
        {"avg_logprob": -1.8, "no_speech_prob": 0.8, "compression_ratio": 2.6, "low_confidence": True},
    )
    monkeypatch.setattr(voice, "stt", mock_stt)

    mock_orch = MagicMock()
    monkeypatch.setattr(voice, "orchestrator", mock_orch)

    async def mock_synth(text, path):
        path.write_bytes(b"MOCK")
    monkeypatch.setattr(voice, "_synthesize_and_verify", mock_synth)

    with open(valid_wav_file, "rb") as f:
        res = client.post(
            "/voice/query",
            files={"audio_file": ("query.wav", f, "audio/wav")},
            headers={"api-key": settings.API_KEY},
        )

    assert res.status_code == 200
    # Invariant: orchestrator.process_query MUST NOT be called!
    assert mock_orch.process_query.called is False
    data = res.json()
    assert data["metadata"]["low_confidence_transcription"] is True
    assert "didn't catch that clearly" in data["answer_text"]


def test_invariant_invalid_tool_args_never_reach_connector():
    """
    Invariant: An invalid tool call must never reach a connector.
    """
    orchestrator = LLMOrchestrator.__new__(LLMOrchestrator)
    mock_connector = MagicMock()
    orchestrator.connector_map = {"get_crm_data": mock_connector}

    # Invalid argument: limit is negative
    tool_calls = [
        {"function": {"name": "get_crm_data", "arguments": {"limit": -5}}}
    ]
    orchestrator._execute_tool_calls(tool_calls)

    assert mock_connector.fetch.called is False
    assert mock_connector.fetch_result.called is False


def test_invariant_correction_failure_preserves_raw_transcript():
    """
    Invariant: Failed transcript correction must not destroy the original transcript.
    """
    mock_client = MagicMock()
    mock_client.chat.side_effect = TimeoutError("Timed out contacting Ollama")

    raw = "What is the daily active users count?"
    result = correct_transcript(raw, "llama3.2:latest", client=mock_client)

    assert result["text"] == raw
    assert result["fallback_used"] is True
    assert result["correction_accepted"] is False
