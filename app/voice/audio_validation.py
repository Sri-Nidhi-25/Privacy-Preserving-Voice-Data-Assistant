"""
app/voice/audio_validation.py - Explicit pre-processing audio validation.

Validation happens BEFORE any expensive processing (obfuscation, Whisper, LLM).
Every failure has a named category from FailureType.
"""
from pathlib import Path
from typing import Tuple

import numpy as np
import librosa

from app.config import settings
from app.failure import FailureType, PipelineError


def validate_and_load(
    path: Path,
    file_size_bytes: int,
) -> Tuple[np.ndarray, int, float]:
    """
    Validate uploaded audio and load it as a 16 kHz mono float32 NumPy array.

    Returns (audio_array, sample_rate, duration_seconds).
    Raises PipelineError with an appropriate FailureType on any failure.
    """
    # 1. File size check (fast, no decoding required)
    max_bytes = settings.MAX_AUDIO_SIZE_MB * 1024 * 1024
    if file_size_bytes > max_bytes:
        raise PipelineError(
            FailureType.AUDIO_TOO_LARGE,
            f"Audio file exceeds the {settings.MAX_AUDIO_SIZE_MB} MB limit "
            f"({file_size_bytes / 1024 / 1024:.1f} MB received).",
            status_code=413,
        )

    # 2. Decode attempt
    try:
        y, sr = librosa.load(str(path), sr=16000, mono=True)
    except Exception as exc:
        raise PipelineError(
            FailureType.AUDIO_DECODE_FAILED,
            "Could not decode the uploaded audio file. "
            "Ensure it is a valid WAV, MP3, WebM, or OGG recording.",
            status_code=400,
            detail=str(exc),
        )

    duration = len(y) / sr if sr > 0 else 0.0

    # 3. Too short (likely silence / button tap, not real speech)
    if duration < 0.1:
        raise PipelineError(
            FailureType.AUDIO_TOO_SHORT,
            "Recording is too short (< 0.1 seconds). Hold the button while speaking.",
            status_code=400,
        )

    # 4. Duration cap
    if duration > settings.MAX_AUDIO_DURATION_SECONDS:
        raise PipelineError(
            FailureType.AUDIO_DURATION_EXCEEDED,
            f"Audio duration ({duration:.1f} s) exceeds the "
            f"{settings.MAX_AUDIO_DURATION_SECONDS:.0f} s limit.",
            status_code=400,
        )

    return y, sr, duration
