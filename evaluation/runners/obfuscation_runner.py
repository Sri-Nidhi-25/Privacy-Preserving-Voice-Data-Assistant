"""
evaluation/runners/obfuscation_runner.py

Benchmarks all obfuscation methods for WER, CER, routing accuracy, and latency.
This is a full replacement for the old benchmark_obfuscation.py that adds
reproducibility metadata, CER, structured EvalRecord output, and the Pareto table.

Usage:
    python -m evaluation.runners.obfuscation_runner \
        --dataset evaluation/datasets/voice_eval_v1.jsonl \
        --output evaluation/results/ \
        --seed 42 [--max-cases 10]
"""
import argparse
import asyncio
import json
import random
import time
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Dict, List, Optional

import librosa
import numpy as np
import soundfile as sf

from app.config import settings
from app.services.llm_orchestrator import _is_data_query
from app.voice.obfuscator import FormantPreservingObfuscator, VoiceObfuscator
from app.voice.stt import STTEngine
from evaluation.metrics.transcription import compute_wer, compute_cer
from evaluation.metrics.routing import routing_metrics
from evaluation.provenance import make_run_id, run_metadata
from evaluation.reporting.export import save_run_results
from evaluation.schemas import EvalRecord, DATASET_VERSION, EVAL_VERSION


OBFUSCATION_METHODS = {
    "none":            lambda: None,
    "naive_mild":      lambda: VoiceObfuscator(strength="mild"),
    "naive_medium":    lambda: VoiceObfuscator(strength="medium"),
    "naive_strong":    lambda: VoiceObfuscator(strength="strong"),
    "formant_mild":    lambda: FormantPreservingObfuscator(semitone_shift=2.0, jitter=0.5, randomize=False),
    "formant_medium":  lambda: FormantPreservingObfuscator(semitone_shift=4.0, jitter=1.0, randomize=False),
    "formant_strong":  lambda: FormantPreservingObfuscator(semitone_shift=6.0, jitter=1.5, randomize=False),
}


async def _tts(text: str, out: Path):
    import edge_tts
    await edge_tts.Communicate(text, "en-US-AriaNeural").save(str(out))


def synthesize_wav(text: str, cache_dir: Path) -> Optional[Path]:
    key = abs(hash(text)) % 1_000_000
    wav = cache_dir / f"raw_{key}.wav"
    if wav.exists():
        return wav
    mp3 = cache_dir / f"raw_{key}.mp3"
    asyncio.run(_tts(text, mp3))
    y, sr = librosa.load(str(mp3), sr=16000, mono=True)
    sf.write(str(wav), y, sr)
    mp3.unlink(missing_ok=True)
    return wav


def load_dataset(path: Path) -> List[Dict]:
    cases = []
    with open(path, encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if line:
                cases.append(json.loads(line))
    return cases


def run(
    dataset_path: Path,
    output_dir: Path,
    seed: int = 42,
    max_cases: Optional[int] = None,
) -> Dict:
    random.seed(seed)
    np.random.seed(seed)

    run_id = make_run_id()
    timestamp = datetime.now(timezone.utc).isoformat()
    cases = load_dataset(dataset_path)
    if max_cases:
        cases = cases[:max_cases]

    cache_dir = Path("benchmark_audio") / "obf_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    print(f"Obfuscation benchmark | run_id={run_id} | {len(cases)} cases | seed={seed}")
    print(f"  Loading Whisper: {settings.STT_MODEL}")
    stt = STTEngine(model_name=settings.STT_MODEL)

    method_summaries = {}
    all_records = []

    for method_name, make_obf in OBFUSCATION_METHODS.items():
        print(f"\n  Method: {method_name}")
        obf = make_obf()
        records = []

        for case in cases:
            ground_truth = case["input_text"]
            wav = synthesize_wav(ground_truth, cache_dir)
            if wav is None:
                continue

            # Apply obfuscation
            t0 = time.perf_counter()
            if obf is None:
                obf_wav = wav
                obf_lat = 0
            else:
                obf_wav = cache_dir / f"obf_{method_name}_{abs(hash(ground_truth)) % 1000000}.wav"
                obf.obfuscate(wav, obf_wav)
                obf_lat = int((time.perf_counter() - t0) * 1000)

            # STT
            t_stt = time.perf_counter()
            try:
                transcript, conf = stt.transcribe_with_confidence(obf_wav)
            except Exception as e:
                transcript, conf = "", {"avg_logprob": None, "no_speech_prob": 1.0, "compression_ratio": None, "low_confidence": True}
            stt_lat = int((time.perf_counter() - t_stt) * 1000)

            wer = compute_wer(ground_truth, transcript)
            cer = compute_cer(ground_truth, transcript)
            actual_route = "tool" if _is_data_query(transcript) else "direct"
            expected_route = case.get("expected_route", "direct")
            routing_ok = actual_route == expected_route

            r = EvalRecord(
                run_id=run_id,
                case_id=f"{case['case_id']}_{method_name}",
                dataset_id=dataset_path.name,
                dataset_version=DATASET_VERSION,
                timestamp=timestamp,
                git_commit=run_metadata(
                    run_id=run_id, dataset_id="", dataset_version=DATASET_VERSION,
                    stt_model=settings.STT_MODEL, llm_model=settings.OLLAMA_MODEL,
                    obfuscation_method=method_name, obfuscation_strength=method_name,
                    seed=seed, eval_version=EVAL_VERSION,
                )["git_commit"],
                python_version=run_metadata(
                    run_id=run_id, dataset_id="", dataset_version=DATASET_VERSION,
                    stt_model=settings.STT_MODEL, llm_model=settings.OLLAMA_MODEL,
                    obfuscation_method=method_name, obfuscation_strength=method_name,
                    seed=seed, eval_version=EVAL_VERSION,
                )["python_version"],
                stt_model=settings.STT_MODEL,
                llm_model=settings.OLLAMA_MODEL,
                obfuscation_method=method_name,
                random_seed=seed,
                input_text=ground_truth,
                category=case.get("category", ""),
                expected_route=expected_route,
                stt_transcript=transcript,
                stt_wer=round(wer, 4),
                stt_cer=round(cer, 4),
                stt_avg_logprob=conf.get("avg_logprob"),
                stt_no_speech_prob=conf.get("no_speech_prob"),
                stt_low_confidence_decision=conf.get("low_confidence"),
                actual_route=actual_route,
                routing_correct=routing_ok,
                privacy_metric="not_yet_measured",
                latency_ms={"obfuscation": obf_lat, "stt": stt_lat},
            )
            records.append(r)
            print(f"    {case['case_id']:<20} WER={wer:.3f} route={'✓' if routing_ok else '✗'} t={transcript[:35]!r}")

        if not records:
            continue

        wers = [r.stt_wer for r in records]
        cers = [r.stt_cer for r in records]
        routing_acc = routing_metrics(
            [r.expected_route for r in records],
            [r.actual_route for r in records],
        )["accuracy"]

        method_summaries[method_name] = {
            "method": method_name,
            "n": len(records),
            "mean_wer": round(mean(wers), 4),
            "mean_cer": round(mean(cers), 4),
            "routing_accuracy": routing_acc,
            "privacy_metric": "not_yet_measured",
        }
        all_records.extend(records)

    # Print Pareto table
    print("\n" + "=" * 70)
    print(f"  OBFUSCATION BENCHMARK — Pareto Table  (run {run_id})")
    print("=" * 70)
    print(f"  {'Method':<20} {'WER':>6}  {'CER':>6}  {'Routing':>8}  {'Privacy':>22}")
    print(f"  {'-'*20} {'-'*6}  {'-'*6}  {'-'*8}  {'-'*22}")
    for name, s in method_summaries.items():
        print(f"  {name:<20} {s['mean_wer']:>6.3f}  {s['mean_cer']:>6.3f}  {s['routing_accuracy']:>8.1%}  {'not_yet_measured':>22}")
    print()
    print("  Privacy evaluation: pending speaker verification experiment (Phase 3)")
    print("=" * 70)

    meta = run_metadata(
        run_id=run_id,
        dataset_id=dataset_path.name,
        dataset_version=DATASET_VERSION,
        stt_model=settings.STT_MODEL,
        llm_model=settings.OLLAMA_MODEL,
        obfuscation_method="all",
        obfuscation_strength="all",
        seed=seed,
        eval_version=EVAL_VERSION,
    )
    summary = {
        "run_metadata": meta,
        "n_cases": len(cases),
        "n_records": len(all_records),
        "methods": method_summaries,
    }
    save_run_results(run_id, all_records, summary, output_dir)
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Obfuscation benchmark across all methods")
    parser.add_argument("--dataset", default="evaluation/datasets/voice_eval_v1.jsonl")
    parser.add_argument("--output", default="evaluation/results")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-cases", type=int, default=None)
    args = parser.parse_args()
    run(Path(args.dataset), Path(args.output), args.seed, args.max_cases)
