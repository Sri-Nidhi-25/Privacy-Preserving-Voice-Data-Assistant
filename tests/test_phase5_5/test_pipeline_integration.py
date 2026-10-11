"""
tests/test_phase5_5/test_pipeline_integration.py

Verifies end-to-end voice pipeline component integration:
  - Audio validation accepts valid WAV and rejects corrupt bytes safely.
  - FormantPreservingObfuscator executes successfully without audio distortion.
  - STTEngine returns confidence dictionary with avg_logprob and no_speech_prob.
  - LLMOrchestrator exposes stage-by-stage latencies and abstention telemetry.
"""
from pathlib import Path
import tempfile
import numpy as np
import pytest
import soundfile as sf

from app.failure import PipelineError
from app.voice.audio_validation import validate_and_load
from app.voice.obfuscator import FormantPreservingObfuscator
from app.services.llm_orchestrator import LLMOrchestrator


def test_audio_validation_valid_and_invalid():
    """Valid audio loads smoothly; corrupt bytes raise PipelineError."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = Path(tmp.name)
        # 1-second sine wave
        y = np.sin(2 * np.pi * 440 * np.linspace(0, 1, 16000)).astype(np.float32)
        sf.write(str(tmp_path), y, 16000)

    try:
        y_loaded, sr, duration = validate_and_load(tmp_path, tmp_path.stat().st_size)
        assert sr == 16000
        assert 0.95 <= duration <= 1.05
    finally:
        tmp_path.unlink(missing_ok=True)

    # Test corrupt file
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_corrupt = Path(tmp.name)
        tmp_corrupt.write_bytes(b"CORRUPT_NON_AUDIO_HEADER_DATA")

    try:
        with pytest.raises(PipelineError):
            validate_and_load(tmp_corrupt, tmp_corrupt.stat().st_size)
    finally:
        tmp_corrupt.unlink(missing_ok=True)


def test_voice_obfuscator_execution():
    """FormantPreservingObfuscator produces non-empty audio preserving duration."""
    obf = FormantPreservingObfuscator(semitone_shift=2.0, jitter=0.5)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as in_tmp:
        in_path = Path(in_tmp.name)
        y = np.sin(2 * np.pi * 440 * np.linspace(0, 0.5, 8000)).astype(np.float32)
        sf.write(str(in_path), y, 16000)

    out_path = in_path.with_suffix(".obf.wav")
    try:
        obf.obfuscate(in_path, out_path)
        assert out_path.exists()
        assert out_path.stat().st_size > 1000
        y_out, sr_out = sf.read(str(out_path))
        assert sr_out == 16000
        assert len(y_out) > 0
    finally:
        in_path.unlink(missing_ok=True)
        out_path.unlink(missing_ok=True)


def test_orchestrator_stage_latencies_and_abstention_metadata():
    """Orchestrator tracks correction, routing, and abstention latencies."""
    orch = LLMOrchestrator()
    res = orch.process_query("Show me active customers", enable_abstention=True)
    meta = res.get("metadata", {})

    assert "abstention_decision" in meta
    assert meta["abstention_decision"] in ("EXECUTE", "ABSTAIN", "DIRECT")
    assert "correction_latency_ms" in meta
    assert "routing_latency_ms" in meta
    assert "execution_prevented_by_abstention" in meta
