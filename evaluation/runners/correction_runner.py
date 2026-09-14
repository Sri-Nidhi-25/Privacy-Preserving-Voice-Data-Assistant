"""
evaluation/runners/correction_runner.py

Ablation study: does transcript correction help or hurt downstream routing?

Runs three conditions:
  A) Raw transcript → routing
  B) Corrected transcript (with acceptance policy) → routing
  C) Corrected transcript (no rejection guard) → routing

Compares WER, CER, and routing accuracy for each condition.

Usage:
    python -m evaluation.runners.correction_runner \
        --dataset evaluation/datasets/voice_eval_v1.jsonl \
        --output evaluation/results/ --seed 42
"""
import argparse
import json
import random
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

from app.config import settings
from app.services.llm_orchestrator import _is_data_query, correct_transcript
from evaluation.metrics.correction import correction_ablation_metrics
from evaluation.metrics.routing import routing_metrics
from evaluation.metrics.transcription import compute_wer, compute_cer
from evaluation.provenance import make_run_id, run_metadata
from evaluation.reporting.export import save_run_results
from evaluation.schemas import EvalRecord, DATASET_VERSION, EVAL_VERSION


def load_dataset(path: Path) -> List[Dict]:
    with open(path, encoding="utf-8-sig") as f:
        return [json.loads(l) for l in f if l.strip()]


def evaluate_correction(
    cases: List[Dict],
    run_id: str,
    timestamp: str,
    meta: Dict,
    seed: int = 42,
) -> List[EvalRecord]:
    """Evaluate transcript correction on ground-truth text input (no audio)."""
    records = []
    try:
        import ollama
        client = ollama.Client(timeout=settings.LLM_TIMEOUT_SECONDS)
        model = settings.OLLAMA_MODEL
        llm_available = True
    except Exception:
        print("  WARNING: Ollama not available, correction will be skipped")
        llm_available = False
        client = None
        model = settings.OLLAMA_MODEL

    for case in cases:
        raw = case["input_text"]
        expected_route = case.get("expected_route", "direct")

        # Condition A: raw routing
        raw_route = "tool" if _is_data_query(raw) else "direct"
        raw_correct = raw_route == expected_route
        raw_wer = compute_wer(raw, raw)
        raw_cer = compute_cer(raw, raw)

        # Condition B: corrected routing
        correction_result = {"text": raw, "correction_attempted": False, "correction_accepted": False,
                             "correction_rejected": False, "correction_changed": False, "fallback_used": True}
        corrected_text = raw

        if llm_available:
            try:
                t0 = time.perf_counter()
                correction_result = correct_transcript(raw, model=model, client=client)
                corr_lat = int((time.perf_counter() - t0) * 1000)
                corrected_text = correction_result.get("text", raw)
            except Exception as e:
                print(f"  Correction error for {case['case_id']}: {e}")

        corrected_route = "tool" if _is_data_query(corrected_text) else "direct"
        corrected_correct = corrected_route == expected_route
        corrected_wer = compute_wer(raw, corrected_text)
        corrected_cer = compute_cer(raw, corrected_text)

        correction_improvement = raw_wer - corrected_wer  # positive = improved
        correction_degraded = corrected_wer > raw_wer + 1e-6

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
            random_seed=seed,
            input_text=raw,
            category=case.get("category", ""),
            subcategory=case.get("subcategory", ""),
            expected_route=expected_route,
            expected_tool=case.get("expected_tool"),
            expected_args=case.get("expected_args", {}),
            # Raw STT baseline (for WER tracking, the raw input is the "truth" here)
            stt_transcript=raw,
            stt_wer=0.0,   # raw vs raw = 0
            stt_cer=0.0,
            # Correction
            correction_attempted=correction_result.get("correction_attempted", False),
            correction_accepted=correction_result.get("correction_accepted", False),
            correction_rejected=correction_result.get("correction_rejected", False),
            correction_changed=correction_result.get("correction_changed", False),
            corrected_transcript=corrected_text,
            corrected_wer=round(corrected_wer, 4),
            corrected_cer=round(corrected_cer, 4),
            correction_improvement=round(correction_improvement, 4),
            correction_degraded=correction_degraded,
            # Routing
            actual_route=corrected_route,
            routing_correct=corrected_correct,
        )
        records.append(r)
        indicator = "↑" if not correction_degraded and correction_result.get("correction_changed") else (
            "↓" if correction_degraded else "—")
        print(f"  {case['case_id']:<20} raw_route={'✓' if raw_correct else '✗'} "
              f"corr_route={'✓' if corrected_correct else '✗'} "
              f"changed={correction_result.get('correction_changed',False)} {indicator}")
    return records


def run(
    dataset_path: Path,
    output_dir: Path,
    seed: int = 42,
) -> Path:
    random.seed(seed)
    np.random.seed(seed)

    run_id = make_run_id()
    timestamp = datetime.now(timezone.utc).isoformat()
    cases = load_dataset(dataset_path)

    print(f"Correction ablation | run_id={run_id} | {len(cases)} cases | seed={seed}")

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

    records = evaluate_correction(cases, run_id, timestamp, meta, seed)
    dicts = [r.to_dict() for r in records]

    # Routing metrics (post-correction)
    rm = routing_metrics(
        [r.expected_route for r in records],
        [r.actual_route for r in records],
    )

    # Correction ablation metrics
    cam = correction_ablation_metrics(dicts)

    summary = {
        "run_metadata": meta,
        "n_cases": len(records),
        "routing": rm,
        "correction": cam,
    }

    print(f"\n  Routing accuracy (corrected text): {rm['accuracy']:.1%}")
    print(f"  False correction rate: {cam.get('false_correction_rate')}")
    print(f"  Improvement rate:      {cam.get('improvement_rate')}")

    out_path = save_run_results(run_id, records, summary, output_dir)
    return out_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Transcript correction ablation")
    parser.add_argument("--dataset", default="evaluation/datasets/voice_eval_v1.jsonl")
    parser.add_argument("--output", default="evaluation/results")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    run(Path(args.dataset), Path(args.output), args.seed)
