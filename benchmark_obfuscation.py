"""
Benchmark: how much does voice obfuscation strength degrade transcription
accuracy, and does it still route correctly to the right data tool?

Compares your existing naive pitch/tempo obfuscation (none/mild/medium/strong)
against the formant-preserving WORLD-vocoder approach (formant_low/formant_high).

Usage:
    pip install jiwer pyworld --break-system-packages   # if not already installed
    python benchmark_obfuscation.py

Output:
    - Per-phrase, per-method WER
    - Whether the (possibly garbled) transcript still triggers _is_data_query()
    - Summary table averaged by method

Run this from your project root so the `app.*` imports resolve.
"""

import asyncio
import csv
from pathlib import Path
from statistics import mean

import edge_tts
import jiwer
import librosa
import soundfile as sf

# NOTE: import the CLASSES, not the module itself -- `obfuscator(...)` where
# `obfuscator` is the module (`from app.voice import obfuscator`) throws
# "TypeError: 'module' object is not callable". You want the classes:
from app.voice.obfuscator import FormantPreservingObfuscator, VoiceObfuscator
from app.voice.stt import STTEngine
from app.services.llm_orchestrator import _is_data_query
from app.config import settings

# ----------------------------------------------------------------------------
# Test set: phrases that exercise the actual keyword vocabulary your router
# depends on (see DATA_KEYWORDS in llm_orchestrator.py). Add more of your own
# real usage patterns here over time -- this list is a starting point, not
# a substitute for logging real queries.
# ----------------------------------------------------------------------------
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

# Each entry: (label, obfuscate_fn(input_wav, output_wav) -> None)
def make_methods():
    return {
        "none": lambda i, o: o.write_bytes(i.read_bytes()),
        "mild": lambda i, o: VoiceObfuscator(strength="mild").obfuscate(i, o),
        "medium": lambda i, o: VoiceObfuscator(strength="medium").obfuscate(i, o),
        "strong": lambda i, o: VoiceObfuscator(strength="strong").obfuscate(i, o),
        "formant_low": lambda i, o: FormantPreservingObfuscator(semitone_shift=3.0).obfuscate(i, o),
        "formant_high": lambda i, o: FormantPreservingObfuscator(semitone_shift=6.0).obfuscate(i, o),
    }

TTS_VOICE = "en-US-AriaNeural"  # a different voice than your assistant's, for variety
WORK_DIR = Path("benchmark_audio")
WORK_DIR.mkdir(exist_ok=True)


async def synthesize(text: str, out_path: Path) -> None:
    communicate = edge_tts.Communicate(text, TTS_VOICE)
    await communicate.save(str(out_path))


def main():
    stt = STTEngine(model_name=settings.STT_MODEL)
    methods = make_methods()
    rows = []

    for i, phrase in enumerate(TEST_PHRASES):
        raw_mp3 = WORK_DIR / f"phrase_{i}.mp3"
        raw_wav = WORK_DIR / f"phrase_{i}.wav"

        print(f"\n[{i+1}/{len(TEST_PHRASES)}] Synthesizing: {phrase!r}")
        asyncio.run(synthesize(phrase, raw_mp3))

        y, sr = librosa.load(raw_mp3, sr=16000)
        sf.write(raw_wav, y, sr)

        for method_name, obfuscate_fn in methods.items():
            out_path = WORK_DIR / f"phrase_{i}_{method_name}.wav"
            obfuscate_fn(raw_wav, out_path)

            transcript = stt.transcribe(out_path)
            wer = jiwer.wer(phrase.lower(), transcript.lower())
            actual_data_query = _is_data_query(transcript)
            expected_data_query = _is_data_query(phrase)
            routing_ok = actual_data_query == expected_data_query

            rows.append({
                "phrase": phrase,
                "method": method_name,
                "transcript": transcript,
                "wer": round(wer, 3),
                "expected_data_query": expected_data_query,
                "actual_data_query": actual_data_query,
                "routing_ok": routing_ok,
            })

            flag = "" if routing_ok else "  <-- ROUTING FLIPPED"
            print(f"  [{method_name:12s}] WER={wer:.3f}  routing_ok={routing_ok}{flag}")
            print(f"                 -> {transcript!r}")

    # ---- Summary ----
    print("\n" + "=" * 78)
    print("SUMMARY (avg WER and routing failures by method)")
    print("=" * 78)
    for method_name in methods:
        method_rows = [r for r in rows if r["method"] == method_name]
        avg_wer = mean(r["wer"] for r in method_rows)
        routing_failures = sum(1 for r in method_rows if not r["routing_ok"])
        print(
            f"{method_name:12s}  avg WER={avg_wer:.3f}  "
            f"routing failures={routing_failures}/{len(method_rows)}"
        )

    # ---- CSV for further inspection ----
    csv_path = WORK_DIR / "results.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nFull results written to {csv_path}")


if __name__ == "__main__":
    main()