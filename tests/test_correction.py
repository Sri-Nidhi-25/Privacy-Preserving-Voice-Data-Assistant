"""
tests/test_correction.py - Tests for transcript post-correction and safety guardrails.
"""
from unittest.mock import MagicMock
from app.services.llm_orchestrator import correct_transcript


def test_correction_accepted():
    mock_client = MagicMock()
    mock_client.chat.return_value = {
        "message": {"content": "show me all active customers"}
    }
    raw = "show me all act of customers"
    res = correct_transcript(raw, "llama3.2:latest", client=mock_client)

    assert res["text"] == "show me all active customers"
    assert res["correction_attempted"] is True
    assert res["correction_accepted"] is True
    assert res["correction_changed"] is True
    assert res["fallback_used"] is False


def test_correction_rejected_on_guardrail_violation():
    # If the LLM generates a wild hallucination with no word overlap
    mock_client = MagicMock()
    mock_client.chat.return_value = {
        "message": {"content": "The weather today in Paris is sunny and warm."}
    }
    raw = "show me all open tickets"
    res = correct_transcript(raw, "llama3.2:latest", client=mock_client)

    # Invariant: Failed or suspicious correction MUST preserve raw transcript
    assert res["text"] == raw
    assert res["correction_rejected"] is True
    assert res["fallback_used"] is True


def test_correction_fallback_on_llm_exception():
    mock_client = MagicMock()
    mock_client.chat.side_effect = ConnectionError("Ollama service unavailable")

    raw = "how many active customers"
    res = correct_transcript(raw, "llama3.2:latest", client=mock_client)

    assert res["text"] == raw
    assert res["fallback_used"] is True
    assert res["correction_accepted"] is False


def test_correction_empty_transcript():
    res = correct_transcript("", "llama3.2:latest")
    assert res["text"] == ""
    assert res["correction_attempted"] is False
