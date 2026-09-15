"""
evaluation/fault_injection/stt_fault.py - STT fault injection engine.

Simulates STT failure modes for reliability evaluation without repeatedly
invoking heavy Whisper models:
  - low_confidence: returns low confidence metadata below threshold
  - timeout: raises TimeoutError
  - exception: raises RuntimeError (e.g. CUDA / memory error)
  - empty: returns empty transcript with low confidence
  - hallucination: returns completely erroneous hallucination
  - high_quality: returns perfect transcript with high confidence
"""
from typing import Dict, Tuple, Optional
from pathlib import Path


class MockFaultySTTEngine:
    def __init__(self, failure_mode: str = "none", default_transcript: str = "Show me all active customers"):
        """
        failure_mode:
            'none': returns default_transcript with high confidence
            'low_confidence': returns low confidence signals (should trigger abstention)
            'timeout': raises TimeoutError
            'exception': raises RuntimeError
            'empty': returns empty transcript with high no_speech_prob
            'hallucination': returns spurious domain hallucination
        """
        self.failure_mode = failure_mode
        self.default_transcript = default_transcript
        self.call_count = 0

    def transcribe_with_confidence(self, audio_path: Path) -> Tuple[str, Dict]:
        self.call_count += 1

        if self.failure_mode == "timeout":
            raise TimeoutError("STT transcription timed out after 60s")

        if self.failure_mode == "exception":
            raise RuntimeError("Whisper GPU out-of-memory error")

        if self.failure_mode == "low_confidence":
            return (
                "garbled muffled noise",
                {
                    "avg_logprob": -1.85,
                    "no_speech_prob": 0.45,
                    "compression_ratio": 2.65,
                    "low_confidence": True,
                },
            )

        if self.failure_mode == "empty":
            return (
                "",
                {
                    "avg_logprob": -2.5,
                    "no_speech_prob": 0.98,
                    "compression_ratio": 1.2,
                    "low_confidence": True,
                },
            )

        if self.failure_mode == "hallucination":
            return (
                "unrelated hallucinated words about cooking recipes",
                {
                    "avg_logprob": -1.2,
                    "no_speech_prob": 0.1,
                    "compression_ratio": 1.5,
                    "low_confidence": False,
                },
            )

        # Normal high-quality STT
        return (
            self.default_transcript,
            {
                "avg_logprob": -0.25,
                "no_speech_prob": 0.01,
                "compression_ratio": 1.1,
                "low_confidence": False,
            },
        )
