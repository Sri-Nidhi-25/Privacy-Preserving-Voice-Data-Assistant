"""
tests/test_obfuscation.py - Tests for voice obfuscation.
"""
from pathlib import Path
import soundfile as sf
from app.voice.obfuscator import FormantPreservingObfuscator, VoiceObfuscator


def test_formant_preserving_obfuscator(valid_wav_file: Path, tmp_path: Path):
    out_wav = tmp_path / "obf_output.wav"
    obf = FormantPreservingObfuscator(semitone_shift=2.0, randomize=False)
    obf.obfuscate(valid_wav_file, out_wav)

    assert out_wav.exists()
    assert out_wav.stat().st_size > 0

    # Ensure decodable
    data, sr = sf.read(str(out_wav))
    assert sr == 16000
    assert len(data) > 0


def test_voice_obfuscator(valid_wav_file: Path, tmp_path: Path):
    out_wav = tmp_path / "voice_obf_output.wav"
    obf = VoiceObfuscator(strength="mild")
    obf.obfuscate(valid_wav_file, out_wav)

    assert out_wav.exists()
    assert out_wav.stat().st_size > 0
    data, sr = sf.read(str(out_wav))
    assert sr == 16000
