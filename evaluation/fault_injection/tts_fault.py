"""
evaluation/fault_injection/tts_fault.py - TTS fault injection synthesizer.

Simulates TTS failures (timeout, exception, missing audio) to verify that
the textual response and query metadata remain intact and are not destroyed
when audio generation fails.
"""
import asyncio
from pathlib import Path


class MockFaultyTTSSynthesizer:
    def __init__(self, failure_mode: str = "none"):
        self.failure_mode = failure_mode
        self.call_count = 0

    async def synthesize(self, text: str, output_path: Path, voice: str = "en-US-GuyNeural") -> bool:
        self.call_count += 1

        if self.failure_mode == "timeout":
            raise asyncio.TimeoutError("TTS synthesis timed out")

        if self.failure_mode == "exception":
            raise RuntimeError("Edge-TTS connection failed / network error")

        if self.failure_mode == "missing_file":
            # Finishes without creating output_path
            return False

        # Success mode: create a dummy valid small mp3/wav
        output_path.parent.mkdir(parents=True, exist_ok=True)
        # Write 100 bytes of dummy audio data
        output_path.write_bytes(b"\x00" * 100)
        return True
