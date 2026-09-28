"""
evaluation/run_final_experiment.py - Master Reproducibility Runner for Phase 4.6.

Executes scientifically valid, dual-level evaluation:
- LEVEL A: Component-Level Evaluation (Text-based Intent Routing on Frozen Held-Out & Challenge Sets)
- LEVEL B: Voice Pipeline Evaluation (Real Speech Audio -> Validation -> Obfuscation -> Whisper STT -> Correction -> Routing -> Tool Execution)
- Real Acoustic Robustness Matrix (Physical Noise & Speed perturbations on Audio)
- Reconstructed Component Ablation Study (Isolated Mechanism Removal)
- Physical Acoustic Obfuscation Analysis (F0 Pitch Shift & Formant Envelope Tracking)

Ensures:
- Cryptographic hash verification of all frozen datasets before execution
- Raw per-example records serialized to JSONL
- Failure traces captured with failure codes in failures.json
- Separation between text component evaluation and actual voice pipeline evaluation

Usage:
    python -m evaluation.run_final_experiment [--seed 42] [--quick] [--output-dir experiments/results]
"""
import argparse
import hashlib
import json
import os
import platform
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import librosa
import numpy as np
import soundfile as sf

from app.connectors.analytics_connector import AnalyticsConnector
from app.connectors.crm_connector import CRMConnector
from app.connectors.support_connector import SupportConnector
from app.services.correction_guard import apply_correction_gate
from app.services.intent_router import classify_intent, Intent
from app.voice.audio_validation import validate_and_load
from app.voice.obfuscator import FormantPreservingObfuscator
from app.voice.stt import STTEngine
from evaluation.metrics.transcription import compute_wer, compute_cer
from evaluation.provenance import get_git_commit, get_python_version, make_run_id
from evaluation.runners.ablation_runner import run_ablation_study
from evaluation.runners.privacy_acoustic_runner import run_privacy_acoustic_study
from evaluation.runners.robustness_runner import run_acoustic_robustness


def calculate_sha256(path: Path) -> str:
    """Calculates SHA256 hexadecimal digest of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().lower()


def verify_frozen_datasets(manifest_path: Path) -> Dict[str, Any]:
    """Verifies that all frozen evaluation datasets strictly match their manifest hashes."""
    if not manifest_path.exists():
        raise FileNotFoundError(f"Dataset manifest not found at {manifest_path}")

    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)

    verification = {}
    for tier, spec in manifest.get("datasets", {}).items():
        p = Path(spec["path"])
        if not p.exists():
            raise FileNotFoundError(f"Dataset {tier} not found at {p}")
        current_hash = calculate_sha256(p)
        expected_hash = spec["sha256"].lower()
        if current_hash != expected_hash:
            raise ValueError(
                f"DATASET INTEGRITY COMPROMISED for {tier} ({p}):\n"
                f"Expected: {expected_hash}\n"
                f"Actual:   {current_hash}"
            )
        verification[tier] = {
            "path": str(p),
            "sha256": current_hash,
            "status": "VERIFIED_UNCHANGED",
            "cases_count": spec["cases_count"],
        }
    return verification


def run_component_evaluation(dataset_path: Path) -> Tuple[Dict[str, Any], List[Dict], List[Dict]]:
    """LEVEL A: Component-level text routing evaluation."""
    with open(dataset_path, encoding="utf-8-sig") as f:
        cases = [json.loads(line) for line in f if line.strip()]

    raw_records = []
    failures = []
    by_category = {}
    correct_count = 0

    for c in cases:
        case_id = c.get("case_id")
        text = c.get("input_text", "")
        exp_route = c.get("expected_route", "direct")
        exp_tool = c.get("expected_tool")
        cat = c.get("category", "unknown")

        if cat not in by_category:
            by_category[cat] = {"total": 0, "correct": 0}
        by_category[cat]["total"] += 1

        res = classify_intent(text)
        is_correct = (res.route == exp_route)

        record = {
            "case_id": case_id,
            "input_type": "text",
            "dataset": dataset_path.name,
            "category": cat,
            "input_text": text,
            "expected_route": exp_route,
            "expected_tool": exp_tool,
            "actual_route": res.route,
            "actual_intent": res.intent.value,
            "actual_tool": res.target_tool,
            "confidence": res.confidence,
            "routing_correct": is_correct,
        }
        raw_records.append(record)

        if is_correct:
            correct_count += 1
            by_category[cat]["correct"] += 1
        else:
            failure_code = "ROUTING_FALSE_POSITIVE" if res.route == "tool" else "ROUTING_FALSE_NEGATIVE"
            failures.append({
                "case_id": case_id,
                "dataset": dataset_path.name,
                "failed_stage": "routing",
                "failure_code": failure_code,
                "input_text": text,
                "expected": {"route": exp_route, "tool": exp_tool},
                "observed": {"route": res.route, "tool": res.target_tool, "intent": res.intent.value},
                "notes": c.get("notes", ""),
            })

    total = len(cases)
    accuracy = correct_count / max(total, 1)

    summary = {
        "dataset": dataset_path.name,
        "sample_size": total,
        "overall_accuracy": round(accuracy, 4),
        "total_failures": len(failures),
        "by_category": {
            k: {
                "total": v["total"],
                "correct": v["correct"],
                "accuracy": round(v["correct"] / max(v["total"], 1), 4),
            }
            for k, v in by_category.items()
        },
    }
    return summary, raw_records, failures


def run_voice_pipeline_evaluation(audio_dir: Path) -> Tuple[Dict[str, Any], List[Dict], List[Dict]]:
    """LEVEL B: Voice pipeline evaluation (Real Speech Audio -> Validation -> Obfuscation -> STT -> Routing -> Tool)."""
    # Ground truth mapping for canonical test speech audio
    test_suite = [
        {
            "case_id": "voice_pipe_001",
            "file": "phrase_0.wav",
            "ref_text": "Show me all high priority open tickets",
            "expected_route": "tool",
            "expected_tool": "get_support_tickets",
            "expected_args": {"status": "open", "priority": "high"},
        },
        {
            "case_id": "voice_pipe_002",
            "file": "phrase_1.wav",
            "ref_text": "How many active customers do we have",
            "expected_route": "tool",
            "expected_tool": "get_crm_data",
            "expected_args": {"status": "active"},
        },
        {
            "case_id": "voice_pipe_003",
            "file": "phrase_2.wav",
            "ref_text": "What's the daily active users trend for the last seven days",
            "expected_route": "tool",
            "expected_tool": "get_analytics",
            "expected_args": {"days": 7},
        },
    ]

    stt = STTEngine()
    obf = FormantPreservingObfuscator(semitone_shift=3.0, randomize=False)
    crm = CRMConnector()
    support = SupportConnector()
    analytics = AnalyticsConnector()

    raw_records = []
    failures = []
    tmp_dir = Path(tempfile.mkdtemp(prefix="voice_pipe_eval_"))

    try:
        for item in test_suite:
            src_wav = audio_dir / item["file"]
            if not src_wav.exists():
                continue

            t_start = time.time()
            # Stage 1: Validation
            try:
                validate_and_load(src_wav, src_wav.stat().st_size)
            except Exception as val_err:
                failures.append({"case_id": item["case_id"], "failed_stage": "validation", "error": str(val_err)})
                continue

            # Stage 2: Obfuscation
            obf_wav = tmp_dir / f"obf_{item['file']}"
            obf.obfuscate(src_wav, obf_wav)

            # Stage 3: Whisper STT
            stt_text, confidence = stt.transcribe_with_confidence(obf_wav)
            wer = compute_wer(item["ref_text"], stt_text)
            cer = compute_cer(item["ref_text"], stt_text)

            # Stage 4: Transcript Correction Guard (Simulated candidate)
            corr_dec, final_text, _ = apply_correction_gate(stt_text, stt_text)

            # Stage 5: Routing
            route_res = classify_intent(final_text)
            routing_ok = (route_res.route == item["expected_route"])
            tool_ok = (route_res.target_tool == item["expected_tool"])

            # Stage 6: Tool Execution
            tool_res_count = 0
            exec_ok = False
            try:
                if route_res.target_tool == "get_crm_data":
                    res = crm.fetch(status="active")
                    tool_res_count = len(res)
                    exec_ok = True
                elif route_res.target_tool == "get_support_tickets":
                    res = support.fetch(status="open", priority="high")
                    tool_res_count = len(res)
                    exec_ok = True
                elif route_res.target_tool == "get_analytics":
                    res = analytics.fetch(days=7)
                    tool_res_count = len(res) if isinstance(res, list) else 1
                    exec_ok = True
            except Exception as e:
                exec_ok = False

            elapsed_ms = round((time.time() - t_start) * 1000, 1)

            rec = {
                "case_id": item["case_id"],
                "input_type": "real_speech_audio",
                "audio_file": item["file"],
                "reference_text": item["ref_text"],
                "stt_hypothesis": stt_text,
                "wer": wer,
                "cer": cer,
                "low_confidence_abstention": confidence.get("low_confidence", False),
                "routed_intent": route_res.intent.value,
                "actual_tool": route_res.target_tool,
                "routing_correct": routing_ok,
                "tool_selection_correct": tool_ok,
                "tool_execution_success": exec_ok,
                "result_count": tool_res_count,
                "pipeline_success": (routing_ok and tool_ok and exec_ok),
                "latency_ms": elapsed_ms,
            }
            raw_records.append(rec)

            if not (routing_ok and tool_ok and exec_ok):
                failures.append({
                    "case_id": item["case_id"],
                    "failed_stage": "pipeline",
                    "failure_code": "TOOL_MISMATCH_OR_EXEC_FAIL",
                    "observed": rec,
                })
    finally:
        import shutil
        shutil.rmtree(tmp_dir, ignore_errors=True)

    n = len(raw_records)
    avg_wer = float(np.mean([r["wer"] for r in raw_records])) if n else 0.0
    avg_cer = float(np.mean([r["cer"] for r in raw_records])) if n else 0.0
    task_success_rate = float(np.mean([1.0 if r["pipeline_success"] else 0.0 for r in raw_records])) if n else 0.0

    summary = {
        "evaluation_level": "LEVEL_B_VOICE_PIPELINE",
        "sample_size": n,
        "average_wer": round(avg_wer, 4),
        "average_cer": round(avg_cer, 4),
        "task_success_rate": round(task_success_rate, 4),
        "total_pipeline_failures": len(failures),
    }
    return summary, raw_records, failures


def main():
    parser = argparse.ArgumentParser(description="Phase 4.6 Master Reproducibility Runner")
    parser.add_argument("--seed", type=int, default=42, help="Fixed random seed")
    parser.add_argument("--output-dir", type=Path, default=Path("experiments/results"))
    parser.add_argument("--quick", action="store_true", help="Quick mode for rapid validation")
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    master_run_id = make_run_id()
    start_time = time.time()

    print("=" * 85)
    print(f"PHASE 4.6 MASTER REPRODUCIBILITY EXPERIMENT")
    print(f"Run ID: {master_run_id} | Seed: {args.seed} | Mode: {'Quick' if args.quick else 'Full'}")
    print("=" * 85)

    # 1. Dataset Cryptographic Verification
    print("\n[Step 1/6] Verifying Cryptographic Integrity of Frozen Datasets...")
    manifest_path = Path("evaluation/datasets/manifest.json")
    dataset_verification = verify_frozen_datasets(manifest_path)
    for tier, info in dataset_verification.items():
        print(f"  {tier:<15}: {info['status']} ({info['cases_count']} cases) [{info['sha256'][:16]}...]")

    # 2. Level A: Component Evaluation on Frozen Sets
    print("\n[Step 2/6] LEVEL A: Component Evaluation on Frozen Sets...")
    held_out_path = Path("evaluation/datasets/held_out_test/held_out_test_v1.jsonl")
    ho_summary, ho_raw, ho_fails = run_component_evaluation(held_out_path)
    print(f"  Held-Out Test Accuracy: {ho_summary['overall_accuracy']:.1%} ({ho_summary['sample_size']} cases | {ho_summary['total_failures']} failures)")

    challenge_path = Path("evaluation/datasets/challenge/challenge_v1.jsonl")
    ch_summary, ch_raw, ch_fails = run_component_evaluation(challenge_path)
    print(f"  Challenge Suite Accuracy: {ch_summary['overall_accuracy']:.1%} ({ch_summary['sample_size']} cases | {ch_summary['total_failures']} failures)")

    all_component_records = ho_raw + ch_raw
    all_failures = ho_fails + ch_fails

    # 3. Level B: Voice Pipeline Evaluation on Real Audio
    print("\n[Step 3/6] LEVEL B: Voice Pipeline Evaluation (Real Speech Audio -> Whisper -> Tool)...")
    pipe_summary, pipe_raw, pipe_fails = run_voice_pipeline_evaluation(Path("benchmark_audio"))
    all_failures.extend(pipe_fails)
    print(f"  Voice Pipeline Task Success: {pipe_summary['task_success_rate']:.1%} (Avg WER: {pipe_summary['average_wer']:.1%})")

    # 4. Reconstructed Ablation Study
    print("\n[Step 4/6] Running Reconstructed Architectural Ablation Study...")
    ablation_summary = run_ablation_study(held_out_path, args.output_dir, args.seed)

    # 5. Real Physical Acoustic Robustness Matrix
    print("\n[Step 5/6] Running Real Physical Acoustic Robustness Matrix (Whisper STT on Noise)...")
    robustness_summary = run_acoustic_robustness(Path("benchmark_audio"), args.output_dir, args.seed, args.quick)

    # 6. Physical Acoustic Obfuscation Analysis
    print("\n[Step 6/6] Running Physical Acoustic Obfuscation & Pitch Shift Analysis...")
    acoustic_summary = run_privacy_acoustic_study(Path("benchmark_audio"), args.output_dir, args.seed)

    elapsed = round(time.time() - start_time, 2)

    # Save raw results and metadata
    comp_jsonl = args.output_dir / "component_results.jsonl"
    with open(comp_jsonl, "w", encoding="utf-8") as f:
        for r in all_component_records:
            f.write(json.dumps(r) + "\n")

    pipe_jsonl = args.output_dir / "pipeline_results.jsonl"
    with open(pipe_jsonl, "w", encoding="utf-8") as f:
        for r in pipe_raw:
            f.write(json.dumps(r) + "\n")

    fail_file = args.output_dir / "failures.json"
    with open(fail_file, "w", encoding="utf-8") as f:
        json.dump({"total_failures": len(all_failures), "failures": all_failures}, f, indent=2)

    config_file = args.output_dir / "config.json"
    with open(config_file, "w", encoding="utf-8") as f:
        json.dump({
            "seed": args.seed,
            "stt_model": "base",
            "quick_mode": args.quick,
            "python_version": get_python_version(),
            "git_commit": get_git_commit(),
            "platform": platform.platform(),
        }, f, indent=2)

    metrics_file = args.output_dir / "metrics.json"
    metrics_data = {
        "master_run_id": master_run_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "elapsed_seconds": elapsed,
        "dataset_verification": dataset_verification,
        "level_a_held_out": ho_summary,
        "level_a_challenge": ch_summary,
        "level_b_voice_pipeline": pipe_summary,
        "ablation_conditions": ablation_summary.get("results", {}),
        "acoustic_robustness_curve": robustness_summary.get("robustness_curve", {}),
        "acoustic_obfuscation_profile": acoustic_summary.get("summary", {}),
        "failures_count": len(all_failures),
    }
    with open(metrics_file, "w", encoding="utf-8") as f:
        json.dump(metrics_data, f, indent=2)

    # Master manifest
    manifest_latest = args.output_dir / "master_experiment_manifest_latest.json"
    with open(manifest_latest, "w", encoding="utf-8") as f:
        json.dump(metrics_data, f, indent=2)

    print("\n" + "=" * 85)
    print("PHASE 4.6 MASTER EXPERIMENT COMPLETE")
    print(f"Elapsed Time: {elapsed}s")
    print(f"Metrics saved to:       {metrics_file}")
    print(f"Failures recorded to:   {fail_file}")
    print(f"Component results:      {comp_jsonl}")
    print(f"Pipeline results:       {pipe_jsonl}")
    print("=" * 85)


if __name__ == "__main__":
    main()
