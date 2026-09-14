"""
evaluation/benchmark_obfuscation.py

Benchmark: evaluate transcription accuracy (WER) and tool routing fidelity across
obfuscation strengths, with experiment metadata for reproducibility.

Usage:
    python evaluation/benchmark_obfuscation.py [--seed 42]
"""
import argparse
import asyncio
import csv
from datetime import datetime, timezone
import random
from pathlib import Path
from statistics import mean
import subprocess
import uuid

import edge_tts
import jiwer
import librosa
import numpy as np
import soundfile as sf

from app.voice.obfuscator import FormantPreservingObfuscator, VoiceObfuscator
from app.voice.stt import STTEngine
from app.services.llm_orchestrator import _is_data_query
from app.config import settings

TEST_PHRASES = [
    "Show me all high priority open tickets",
    "How many active customers do we have",
    "What's the daily active users trend for the last seven days",
    "List closed support tickets from this week",
    "Give me the average daily active users",
    "How many customers are inactive",
    "Show me low priority closed tickets",
    "What is today's weather like",  # control: non-data query, should NOT trigger tools
]

DATASET_ID = "test_phrases_v1"
TTS_VOICE = "en-US-AriaNeural"
WORK_DIR = Path("benchmark_audio")
WORK_DIR.mkdir(exist_ok=True)


def get_git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], stderr=subprocess.DEVNULL
        ).decode().strip()
    except Exception:
        return "unknown"


def make_methods(seed: int):
    random.seed(seed)
    np.random.seed(seed)
    return {
        "none": lambda i, o: o.write_bytes(i.read_bytes()),
        "mild": lambda i, o: VoiceObfuscator(strength="mild").obfuscate(i, o),
        "medium": lambda i, o: VoiceObfuscator(strength="medium").obfuscate(i, o),
        "strong": lambda i, o: VoiceObfuscator(strength="strong").obfuscate(i, o),
        "formant_mild": lambda i, o: FormantPreservingObfuscator(semitone_shift=2.0, jitter=0.5).obfuscate(i, o),
        "formant_medium": lambda i, o: FormantPreservingObfuscator(semitone_shift=4.0, jitter=1.0).obfuscate(i, o),
        "formant_strong": lambda i, o: FormantPreservingObfuscator(semitone_shift=6.0, jitter=1.5).obfuscate(i, o),
    }


async def synthesize(text: str, out_path: Path) -> None:
    communicate = edge_tts.Communicate(text, TTS_VOICE)
    await communicate.save(str(out_path))


def run_benchmark(seed: int = 42) -> Path:
    experiment_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()
    git_commit = get_git_commit()
    stt = STTEngine(model_name=settings.STT_MODEL)
    methods = make_methods(seed)
    rows = []

    print(f"=== Starting Benchmark Experiment {experiment_id[:8]} ===")
    print(f"Timestamp   : {timestamp}")
    print(f"Git Commit  : {git_commit}")
    print(f"STT Model   : {settings.STT_MODEL}")
    print(f"Random Seed : {seed}")
    print(f"Dataset ID  : {DATASET_ID}")

    for i, phrase in enumerate(TEST_PHRASES):
        raw_mp3 = WORK_DIR / f"phrase_{i}.mp3"
        raw_wav = WORK_DIR / f"phrase_{i}.wav"

        print(f"\n[{i+1}/{len(TEST_PHRASES)}] Synthesizing: {phrase!r}")
        asyncio.run(synthesize(phrase, raw_mp3))

        y, sr = librosa.load(str(raw_mp3), sr=16000, mono=True)
        sf.write(str(raw_wav), y, sr)

        for method_name, obfuscate_fn in methods.items():
            out_path = WORK_DIR / f"phrase_{i}_{method_name}.wav"
            obfuscate_fn(raw_wav, out_path)

            transcript = stt.transcribe(out_path)
            wer = jiwer.wer(phrase.lower(), transcript.lower())
            actual_data_query = _is_data_query(transcript)
            expected_data_query = _is_data_query(phrase)
            routing_ok = actual_data_query == expected_data_query

            rows.append({
                "experiment_id": experiment_id,
                "timestamp": timestamp,
                "git_commit": git_commit,
                "stt_model": settings.STT_MODEL,
                "random_seed": seed,
                "dataset_id": DATASET_ID,
                "phrase": phrase,
                "method": method_name,
                "transcript": transcript,
                "wer": round(wer, 3),
                "expected_data_query": expected_data_query,
                "actual_data_query": actual_data_query,
                "routing_ok": routing_ok,
            })

            flag = "" if routing_ok else "  <-- ROUTING FLIPPED"
            print(f"  [{method_name:16s}] WER={wer:.3f}  routing_ok={routing_ok}{flag}")
            print(f"                   -> {transcript!r}")

    print("\n" + "=" * 80)
    print("SUMMARY (avg WER and routing failures by method)")
    print("=" * 80)
    for method_name in methods:
        method_rows = [r for r in rows if r["method"] == method_name]
        avg_wer = mean(r["wer"] for r in method_rows)
        routing_failures = sum(1 for r in method_rows if not r["routing_ok"])
        print(
            f"{method_name:16s}  avg WER={avg_wer:.3f}  "
            f"routing failures={routing_failures}/{len(method_rows)}"
        )

    csv_path = WORK_DIR / "results.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nFull results written to {csv_path}")
    return csv_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run voice obfuscation benchmark")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducible perturbation")
    args = parser.parse_args()
    run_benchmark(seed=args.seed)
