"""
evaluation/runners/end_to_end_runner.py

Full pipeline evaluation: audio synthesis → STT → correction → routing → tool → answer.
This is the most expensive runner; it calls the real LLMOrchestrator and connectors.

Usage:
    python -m evaluation.runners.end_to_end_runner \
        --dataset evaluation/datasets/voice_eval_v1.jsonl \
        --output evaluation/results/ --seed 42 [--max-cases 10]
"""
import argparse
import asyncio
import json
import random
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import librosa
import numpy as np
import soundfile as sf

from app.config import settings
from app.services.llm_orchestrator import LLMOrchestrator, _is_data_query
from app.voice.audio_validation import validate_and_load
from app.voice.obfuscator import FormantPreservingObfuscator
from app.voice.stt import STTEngine
from evaluation.metrics.end_to_end import (
    classify_failure_stage,
    compute_e2e_success,
    end_to_end_metrics,
    generate_failure_matrix,
)
from evaluation.metrics.routing import routing_metrics
from evaluation.metrics.tool_calling import (
    argument_metrics,
    args_field_accuracy,
    args_semantic_equal,
    tool_selection_metrics,
)
from evaluation.metrics.transcription import compute_wer, compute_cer
from evaluation.provenance import make_run_id, run_metadata
from evaluation.reporting.aggregate import print_reliability_report
from evaluation.reporting.export import save_run_results
from evaluation.reporting.tables import failure_matrix_table, failure_examples_table
from evaluation.schemas import EvalRecord, DATASET_VERSION, EVAL_VERSION


async def _tts_speak(text: str, out: Path):
    import edge_tts
    await edge_tts.Communicate(text, "en-US-AriaNeural").save(str(out))


def synthesize_wav(text: str, cache_dir: Path) -> Optional[Path]:
    key = abs(hash(text)) % 1_000_000
    wav = cache_dir / f"e2e_{key}.wav"
    if wav.exists():
        return wav
    mp3 = cache_dir / f"e2e_{key}.mp3"
    asyncio.run(_tts_speak(text, mp3))
    y, sr = librosa.load(str(mp3), sr=16000, mono=True)
    sf.write(str(wav), y, sr)
    mp3.unlink(missing_ok=True)
    return wav


def load_dataset(path: Path) -> List[Dict]:
    with open(path, encoding="utf-8-sig") as f:
        return [json.loads(l) for l in f if l.strip()]


def run(
    dataset_path: Path,
    output_dir: Path,
    seed: int = 42,
    max_cases: Optional[int] = None,
) -> Path:
    random.seed(seed)
    np.random.seed(seed)

    run_id = make_run_id()
    timestamp = datetime.now(timezone.utc).isoformat()
    cases = load_dataset(dataset_path)
    if max_cases:
        cases = cases[:max_cases]

    cache_dir = Path("benchmark_audio") / "e2e_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    print(f"End-to-end evaluation | run_id={run_id} | {len(cases)} cases | seed={seed}")

    stt = STTEngine(model_name=settings.STT_MODEL)
    obf = FormantPreservingObfuscator(semitone_shift=4.0, jitter=1.0, randomize=False)

    try:
        orch = LLMOrchestrator()
        llm_available = True
    except Exception as e:
        print(f"  WARNING: LLM unavailable: {e}")
        llm_available = False
        orch = None

    meta = run_metadata(
        run_id=run_id,
        dataset_id=dataset_path.name,
        dataset_version=DATASET_VERSION,
        stt_model=settings.STT_MODEL,
        llm_model=settings.OLLAMA_MODEL,
        obfuscation_method="formant_preserving",
        obfuscation_strength="medium",
        seed=seed,
        eval_version=EVAL_VERSION,
    )

    records = []
    for i, case in enumerate(cases):
        print(f"\n  [{i+1}/{len(cases)}] {case['case_id']}: {case['input_text'][:60]!r}")
        expected_route = case.get("expected_route", "direct")
        expected_tool = case.get("expected_tool")
        expected_args = case.get("expected_args", {})

        latency_ms = {}
        stt_transcript = None
        corrected_transcript = None
        actual_route = None
        actual_tool = None
        actual_args = None
        answer_text = None
        connector_success = None
        result_count = None
        correction_result = {}
        conf = {}
        wer = cer = corrected_wer = corrected_cer = None
        failure_reason = None

        # Synthesize speech
        wav = synthesize_wav(case["input_text"], cache_dir)
        if wav is None:
            print(f"    FAIL: TTS synthesis failed")
            failure_reason = "tts_synthesis"
            r = _make_record(run_id, case, timestamp, meta, latency_ms, stt_transcript, conf,
                             corrected_transcript, correction_result, actual_route, actual_tool,
                             actual_args, connector_success, answer_text, result_count,
                             wer, cer, corrected_wer, corrected_cer, failure_reason, seed)
            records.append(r)
            continue

        # Obfuscate
        obf_wav = cache_dir / f"e2e_obf_{abs(hash(case['input_text'])) % 1000000}.wav"
        t0 = time.perf_counter()
        try:
            obf.obfuscate(wav, obf_wav)
        except Exception as e:
            print(f"    FAIL: Obfuscation error: {e}")
            failure_reason = "obfuscation"
            obf_wav = wav
        latency_ms["obfuscation"] = int((time.perf_counter() - t0) * 1000)

        # STT
        t1 = time.perf_counter()
        try:
            stt_transcript, conf = stt.transcribe_with_confidence(obf_wav)
        except Exception as e:
            print(f"    FAIL: STT error: {e}")
            stt_transcript = ""
            conf = {"avg_logprob": None, "no_speech_prob": 1.0, "compression_ratio": None, "low_confidence": True}
            failure_reason = "stt"
        latency_ms["stt"] = int((time.perf_counter() - t1) * 1000)
        wer = compute_wer(case["input_text"], stt_transcript)
        cer = compute_cer(case["input_text"], stt_transcript)
        print(f"    STT: {stt_transcript!r}  WER={wer:.3f}")

        # Early abstain if low confidence
        if conf.get("low_confidence") and failure_reason is None:
            failure_reason = "stt_abstention"
            print(f"    ABSTAIN: low confidence STT")

        # LLM orchestration
        if llm_available and not failure_reason:
            t2 = time.perf_counter()
            try:
                response = orch.process_query(stt_transcript)
                latency_ms["orchestrator"] = int((time.perf_counter() - t2) * 1000)

                answer_text = response.get("answer", "")
                tool_calls_made = response.get("tool_calls_made", [])
                correction_result = response.get("correction", {})
                corrected_transcript = correction_result.get("text", stt_transcript)
                corrected_wer = compute_wer(case["input_text"], corrected_transcript)
                corrected_cer = compute_cer(case["input_text"], corrected_transcript)

                if tool_calls_made:
                    actual_route = "tool"
                    first_call = tool_calls_made[0]
                    actual_tool = first_call.get("tool")
                    actual_args = first_call.get("args", {})
                    connector_success = first_call.get("success", False)
                    result_count = len(first_call.get("results", [])) if first_call.get("results") else 0
                else:
                    actual_route = "direct"

                print(f"    Route: {actual_route} (expected: {expected_route})")
            except Exception as e:
                print(f"    LLM error: {e}")
                failure_reason = "answer_generation"
                latency_ms["orchestrator"] = int((time.perf_counter() - t2) * 1000)
        elif not llm_available and not failure_reason:
            # Simulate routing from text for non-LLM testing
            actual_route = "tool" if _is_data_query(stt_transcript) else "direct"
            print(f"    Route (heuristic, no LLM): {actual_route}")

        r = _make_record(run_id, case, timestamp, meta, latency_ms, stt_transcript, conf,
                         corrected_transcript, correction_result, actual_route, actual_tool,
                         actual_args, connector_success, answer_text, result_count,
                         wer, cer, corrected_wer, corrected_cer, failure_reason, seed)
        records.append(r)

    # Aggregate
    dicts = [r.to_dict() for r in records]
    rm = routing_metrics(
        [r.expected_route for r in records if r.actual_route is not None],
        [r.actual_route for r in records if r.actual_route is not None],
    )
    tsm = tool_selection_metrics(
        [r.expected_tool for r in records],
        [r.actual_tool for r in records],
    )
    am = argument_metrics(
        [r.expected_args for r in records],
        [r.actual_args or {} for r in records],
        [r.expected_tool for r in records],
        [r.actual_tool for r in records],
    )
    e2e_m = end_to_end_metrics(dicts)
    wers_all = [r.stt_wer for r in records if r.stt_wer is not None]
    cers_all = [r.stt_cer for r in records if r.stt_cer is not None]
    stt_s = {
        "mean_wer": round(sum(wers_all) / len(wers_all), 4) if wers_all else None,
        "mean_cer": round(sum(cers_all) / len(cers_all), 4) if cers_all else None,
    }

    summary = {
        "run_metadata": meta,
        "n_cases": len(records),
        "routing": rm,
        "tool_selection": tsm,
        "arguments": am,
        "end_to_end": e2e_m,
        "stt": stt_s,
        "task_success_rate": e2e_m.get("task_success_rate", 0),
    }

    print_reliability_report(summary, dicts)
    print(failure_matrix_table(generate_failure_matrix(dicts)))
    print(failure_examples_table(dicts))

    out_path = save_run_results(run_id, records, summary, output_dir)
    return out_path


def _make_record(run_id, case, timestamp, meta, latency_ms, stt_transcript, conf,
                 corrected_transcript, correction_result, actual_route, actual_tool,
                 actual_args, connector_success, answer_text, result_count,
                 wer, cer, corrected_wer, corrected_cer, failure_reason, seed):
    routing_correct = actual_route == case.get("expected_route") if actual_route else None
    expected_args = case.get("expected_args", {})
    expected_tool = case.get("expected_tool")

    tool_correct = (actual_tool == expected_tool) if expected_tool else None
    sem_match = args_semantic_equal(expected_args, actual_args or {}) if (actual_tool and tool_correct) else None
    fa = args_field_accuracy(expected_args, actual_args or {}) if (actual_tool and tool_correct) else None

    r = EvalRecord(
        run_id=run_id,
        case_id=case["case_id"],
        dataset_id=meta["dataset_id"],
        dataset_version=DATASET_VERSION,
        timestamp=timestamp,
        git_commit=meta["git_commit"],
        python_version=meta["python_version"],
        stt_model=meta["stt_model"],
        llm_model=meta["llm_model"],
        obfuscation_method=meta["obfuscation_method"],
        obfuscation_strength=meta["obfuscation_strength"],
        random_seed=seed,
        input_text=case["input_text"],
        category=case.get("category", ""),
        subcategory=case.get("subcategory", ""),
        expected_route=case.get("expected_route", ""),
        expected_tool=expected_tool,
        expected_args=expected_args,
        stt_transcript=stt_transcript,
        stt_wer=round(wer, 4) if wer is not None else None,
        stt_cer=round(cer, 4) if cer is not None else None,
        stt_avg_logprob=conf.get("avg_logprob"),
        stt_no_speech_prob=conf.get("no_speech_prob"),
        stt_compression_ratio=conf.get("compression_ratio"),
        stt_low_confidence_decision=conf.get("low_confidence"),
        correction_attempted=correction_result.get("correction_attempted"),
        correction_accepted=correction_result.get("correction_accepted"),
        correction_rejected=correction_result.get("correction_rejected"),
        correction_changed=correction_result.get("correction_changed"),
        corrected_transcript=corrected_transcript,
        corrected_wer=round(corrected_wer, 4) if corrected_wer is not None else None,
        corrected_cer=round(corrected_cer, 4) if corrected_cer is not None else None,
        correction_improvement=round((wer - corrected_wer), 4) if (wer is not None and corrected_wer is not None) else None,
        correction_degraded=(corrected_wer > wer + 1e-6) if (wer is not None and corrected_wer is not None) else None,
        actual_route=actual_route,
        routing_correct=routing_correct,
        actual_tool=actual_tool,
        tool_selection_correct=tool_correct,
        actual_args=actual_args,
        args_semantic_match=sem_match,
        args_field_accuracy=round(fa, 4) if fa is not None else None,
        connector_success=connector_success,
        answer_text=answer_text,
        result_count=result_count,
        latency_ms=latency_ms,
        privacy_metric="not_yet_measured",
    )
    # Compute e2e success
    r_dict = r.to_dict()
    if failure_reason:
        r.end_to_end_success = False
        r.failure_stage = failure_reason
    else:
        r.end_to_end_success = compute_e2e_success(r_dict)
        r.failure_stage = classify_failure_stage(r.to_dict())
    return r


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="End-to-end pipeline evaluation")
    parser.add_argument("--dataset", default="evaluation/datasets/voice_eval_v1.jsonl")
    parser.add_argument("--output", default="evaluation/results")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-cases", type=int, default=None)
    args = parser.parse_args()
    run(Path(args.dataset), Path(args.output), args.seed, args.max_cases)
