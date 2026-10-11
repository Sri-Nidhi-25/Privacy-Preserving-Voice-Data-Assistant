"""
evaluation/phase5_5/audio_generator.py

Generates and perturbs real audio for Phase 5.5 E2E evaluation.
Uses neural TTS to generate clean reference speech, and generates calibrated
acoustic variations (20dB, 10dB Gaussian noise) cached under benchmark_audio/phase5_5_cache/.
"""
import asyncio
from pathlib import Path
from typing import Dict, Optional, Tuple
import librosa
import numpy as np
import soundfile as sf
import edge_tts

CACHE_DIR = Path("benchmark_audio") / "phase5_5_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


async def _synthesize_edge_tts(text: str, output_path: Path, voice: str = "en-US-AriaNeural"):
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(str(output_path))


def get_or_synthesize_clean_audio(text: str, case_id: str) -> Path:
    """
    Returns path to a 16kHz mono WAV file for the given text.
    Uses cached audio if available, otherwise synthesizes via edge-tts.
    """
    if not text.strip():
        # Handle empty audio
        empty_wav = CACHE_DIR / f"{case_id}_empty.wav"
        if not empty_wav.exists():
            sf.write(str(empty_wav), np.zeros(16000, dtype=np.float32), 16000)
        return empty_wav

    wav_path = CACHE_DIR / f"{case_id}_clean.wav"
    if wav_path.exists() and wav_path.stat().st_size > 1000:
        return wav_path

    mp3_path = CACHE_DIR / f"{case_id}_tmp.mp3"
    try:
        asyncio.run(_synthesize_edge_tts(text, mp3_path))
        y, sr = librosa.load(str(mp3_path), sr=16000, mono=True)
        sf.write(str(wav_path), y, 16000)
    finally:
        mp3_path.unlink(missing_ok=True)

    return wav_path


def add_gaussian_noise(y: np.ndarray, snr_db: float) -> np.ndarray:
    """Adds zero-mean Gaussian white noise at specified SNR in dB."""
    if np.isinf(snr_db) or snr_db >= 100:
        return y.copy()
    signal_power = np.mean(y ** 2)
    if signal_power < 1e-12:
        return y.copy()
    noise_power = signal_power / (10 ** (snr_db / 10.0))
    noise = np.random.normal(0, np.sqrt(noise_power), len(y)).astype(y.dtype)
    return y + noise


def generate_acoustic_variants(clean_wav: Path, case_id: str) -> Dict[str, Path]:
    """
    Generates Clean (inf dB), 20 dB, and 10 dB versions of the clean audio file.
    """
    variants = {"clean": clean_wav}
    y, sr = librosa.load(str(clean_wav), sr=16000, mono=True)

    for snr in [20, 10]:
        variant_path = CACHE_DIR / f"{case_id}_{snr}db.wav"
        if not (variant_path.exists() and variant_path.stat().st_size > 1000):
            noisy = add_gaussian_noise(y, float(snr))
            sf.write(str(variant_path), noisy, sr)
        variants[f"{snr}db"] = variant_path

    return variants
