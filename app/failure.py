"""
app/failure.py - Central failure taxonomy for the voice pipeline.
"""
from enum import Enum
from typing import Optional


class FailureType(str, Enum):
    INVALID_AUDIO = "invalid_audio"
    AUDIO_TOO_LARGE = "audio_too_large"
    AUDIO_TOO_SHORT = "audio_too_short"
    AUDIO_DECODE_FAILED = "audio_decode_failed"
    AUDIO_DURATION_EXCEEDED = "audio_duration_exceeded"
    OBFUSCATION_FAILED = "obfuscation_failed"
    STT_FAILED = "stt_failed"
    STT_LOW_CONFIDENCE = "stt_low_confidence"
    CORRECTION_FAILED = "correction_failed"
    CORRECTION_REJECTED = "correction_rejected"
    ROUTING_FAILED = "routing_failed"
    TOOL_SELECTION_FAILED = "tool_selection_failed"
    INVALID_TOOL_ARGUMENTS = "invalid_tool_arguments"
    CONNECTOR_FAILED = "connector_failed"
    DATA_UNAVAILABLE = "data_unavailable"
    LLM_FAILED = "llm_failed"
    TTS_FAILED = "tts_failed"
    TIMEOUT = "timeout"
    CONFIGURATION_ERROR = "configuration_error"


class PipelineError(Exception):
    """Structured pipeline failure convertible to HTTP error without leaking internals."""

    def __init__(
        self,
        failure_type: FailureType,
        message: str,
        status_code: int = 500,
        detail: Optional[str] = None,
    ) -> None:
        self.failure_type = failure_type
        self.message = message
        self.status_code = status_code
        self.detail = detail or message
        super().__init__(message)

    def to_response_dict(self) -> dict:
        return {"error": self.failure_type.value, "message": self.message}

    def to_http(self):
        from fastapi import HTTPException
        return HTTPException(
            status_code=self.status_code,
            detail=self.to_response_dict(),
        )
