"""
evaluation/runners/transcription_runner.py

Evaluates transcription quality (WER, CER) and STT confidence signal calibration
using synthetic TTS-generated speech as ground truth.

Usage:
    python -m evaluation.runners.transcription_runner \
        --dataset evaluation/datasets/voice_eval_v1.jsonl \
        --output evaluation/results/ \
        --seed 42 [--max-cases 10]
"""
import argparse
import asyncio
import json
import random
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import librosa
import numpy as np
import soundfile as sf

from app.config import settings
from app.voice.stt import STTEngine
from evaluation.metrics.transcription import compute_wer, compute_cer
from evaluation.provenance import get_git_commit, get_python_version, make_run_id, run_metadata
from evaluation.reporting.export import save_run_results
from evaluation.schemas import EvalRecord, DATASET_VERSION, EVAL_VERSION


def load_dataset(path: Path) -> List[Dict]:
    cases = []
    with open(path, encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if line:
                cases.append(json.loads(line))
    return cases


async def _tts_synthesize(text: str, out_path: Path, voice: str = "en-US-GuyNeural") -> None:
    import edge_tts
    comm = edge_tts.Communicate(text, voice)
    await comm.save(str(out_path))


def synthesize_audio(text: str, work_dir: Path, seed: int = 42) -> Optional[Path]:
    """Synthesize speech for a text using Edge-TTS. Returns WAV path or None on error."""
    mp3_path = work_dir / f"tts_{abs(hash(text)) % 100000}.mp3"
    wav_path = mp3_path.with_suffix(".wav")

    if wav_path.exists():
        return wav_path  # Cache: reuse if already synthesized

    try:
        asyncio.run(_tts_synthesize(text, mp3_path))
        y, sr = librosa.load(str(mp3_path), sr=16000, mono=True)
        sf.write(str(wav_path), y, sr)
        mp3_path.unlink(missing_ok=True)
        return wav_path
    except Exception as e:
        print(f"    TTS error for {text!r}: {e}")
        return None


def run(
    dataset_path: Path,
    output_dir: Path,
    seed: int = 42,
    max_cases: Optional[int] = None,
    work_dir: Optional[Path] = None,
) -> Path:
    random.seed(seed)
    np.random.seed(seed)

    run_id = make_run_id()
    timestamp = datetime.now(timezone.utc).isoformat()
    cases = load_dataset(dataset_path)
    if max_cases:
        cases = cases[:max_cases]

    _work_dir = work_dir or Path("benchmark_audio") / "transcription_eval"
    _work_dir.mkdir(parents=True, exist_ok=True)

    print(f"Transcription evaluation | run_id={run_id} | {len(cases)} cases | seed={seed}")
    print(f"  Loading Whisper model: {settings.STT_MODEL}")
    stt = STTEngine(model_name=settings.STT_MODEL)

    meta = run_metadata(
        run_id=run_id,
        dataset_id=dataset_path.name,
        dataset_version=DATASET_VERSION,
        stt_model=settings.STT_MODEL,
        llm_model=settings.OLLAMA_MODEL,
        obfuscation_method="none",
        obfuscation_strength="none",
        seed=seed,
        eval_version=EVAL_VERSION,
    )

    records = []
    for i, case in enumerate(cases):
        print(f"  [{i+1}/{len(cases)}] {case['case_id']}: {case['input_text'][:50]!r}")

        # Synthesize ground-truth speech
        audio_path = synthesize_audio(case["input_text"], _work_dir, seed)
        if audio_path is None:
            print(f"    SKIP: TTS failed")
            continue

        # Transcribe
        try:
            transcript, confidence = stt.transcribe_with_confidence(audio_path)
        except Exception as e:
            print(f"    STT error: {e}")
            transcript = ""
            confidence = {"avg_logprob": None, "no_speech_prob": 1.0, "compression_ratio": None, "low_confidence": True}

        wer = compute_wer(case["input_text"], transcript)
        cer = compute_cer(case["input_text"], transcript)
        print(f"    WER={wer:.3f}  CER={cer:.3f}  transcript={transcript!r}")

        r = EvalRecord(
            run_id=run_id,
            case_id=case["case_id"],
            dataset_id=dataset_path.name,
            dataset_version=DATASET_VERSION,
            timestamp=timestamp,
            git_commit=meta["git_commit"],
            python_version=meta["python_version"],
            stt_model=settings.STT_MODEL,
            llm_model=settings.OLLAMA_MODEL,
            input_text=case["input_text"],
            category=case.get("category", ""),
            subcategory=case.get("subcategory", ""),
            expected_route=case.get("expected_route", ""),
            expected_tool=case.get("expected_tool"),
            expected_args=case.get("expected_args", {}),
            stt_transcript=transcript,
            stt_wer=round(wer, 4),
            stt_cer=round(cer, 4),
            stt_avg_logprob=confidence.get("avg_logprob"),
            stt_no_speech_prob=confidence.get("no_speech_prob"),
            stt_compression_ratio=confidence.get("compression_ratio"),
            stt_low_confidence_decision=confidence.get("low_confidence"),
        )
        records.append(r)

    wers = [r.stt_wer for r in records if r.stt_wer is not None]
    cers = [r.stt_cer for r in records if r.stt_cer is not None]
    n_low_conf = sum(1 for r in records if r.stt_low_confidence_decision)

    summary = {
        "run_metadata": meta,
        "n_cases": len(records),
        "stt": {
            "mean_wer": round(sum(wers) / len(wers), 4) if wers else None,
            "mean_cer": round(sum(cers) / len(cers), 4) if cers else None,
            "n_low_confidence": n_low_conf,
            "abstention_rate": round(n_low_conf / len(records), 4) if records else None,
        },
    }

    print(f"\n  STT mean WER: {summary['stt']['mean_wer']}  mean CER: {summary['stt']['mean_cer']}")
    out_path = save_run_results(run_id, records, summary, output_dir)
    return out_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Transcription quality evaluation")
    parser.add_argument("--dataset", default="evaluation/datasets/voice_eval_v1.jsonl")
    parser.add_argument("--output", default="evaluation/results")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-cases", type=int, default=None)
    args = parser.parse_args()
    run(Path(args.dataset), Path(args.output), args.seed, args.max_cases)
