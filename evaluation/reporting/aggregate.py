"""
evaluation/reporting/aggregate.py - Latency statistics and failure aggregation.
"""
import json
from pathlib import Path
from typing import Dict, List, Optional
import statistics


def percentiles(values: List[float], label: str = "") -> Dict:
    if not values:
        return {}
    sv = sorted(values)
    n = len(sv)
    def pct(p): return sv[min(int(p / 100 * n), n - 1)]
    return {
        "n": n,
        "mean": round(statistics.mean(sv), 1),
        "p50": round(pct(50), 1),
        "p90": round(pct(90), 1),
        "p95": round(pct(95), 1),
        "p99": round(pct(99), 1),
        "max": round(sv[-1], 1),
    }


def aggregate_latency(records: List[Dict]) -> Dict:
    stages = ["validation", "obfuscation", "stt", "orchestrator", "tts", "total"]
    out = {}
    for stage in stages:
        vals = [
            r["latency_ms"][stage]
            for r in records
            if isinstance(r.get("latency_ms"), dict) and stage in r["latency_ms"]
        ]
        if vals:
            out[stage] = percentiles(vals, stage)
    return out


def aggregate_stt_signals(records: List[Dict]) -> Dict:
    logprobs = [r["stt_avg_logprob"] for r in records if r.get("stt_avg_logprob") is not None]
    no_speech = [r["stt_no_speech_prob"] for r in records if r.get("stt_no_speech_prob") is not None]
    low_conf_decisions = [r for r in records if r.get("stt_low_confidence_decision") is not None]
    n_abstain = sum(1 for r in low_conf_decisions if r["stt_low_confidence_decision"])
    return {
        "avg_logprob": {"mean": round(statistics.mean(logprobs), 4) if logprobs else None},
        "no_speech_prob": {"mean": round(statistics.mean(no_speech), 4) if no_speech else None},
        "n_abstained": n_abstain,
        "abstention_rate": round(n_abstain / len(low_conf_decisions), 4) if low_conf_decisions else None,
    }


def print_reliability_report(summary: Dict, records: List[Dict] = None):
    """Print a human-readable reliability breakdown report."""
    meta = summary.get("run_metadata", {})
    rm = summary.get("routing", {})
    tsm = summary.get("tool_selection", {})
    am = summary.get("arguments", {})
    e2e = summary.get("end_to_end", {})
    corr = summary.get("correction", {})
    stt_s = summary.get("stt", {})

    print()
    print("=" * 65)
    print("  EVALUATION RELIABILITY REPORT")
    print("=" * 65)
    print(f"  Run ID       : {meta.get('run_id')}")
    print(f"  Timestamp    : {meta.get('timestamp')}")
    print(f"  Git Commit   : {meta.get('git_commit')}")
    print(f"  Dataset      : {meta.get('dataset_id')} v{meta.get('dataset_version')}")
    print(f"  STT Model    : {meta.get('stt_model')}")
    print(f"  LLM Model    : {meta.get('llm_model')}")
    print(f"  Obfuscation  : {meta.get('obfuscation_method')} / {meta.get('obfuscation_strength')}")
    print(f"  Seed         : {meta.get('seed')}")
    print(f"  Samples      : {summary.get('n_cases')}")
    print()

    if stt_s:
        print("STT")
        print(f"  WER (mean)             : {stt_s.get('mean_wer', 'n/a')}")
        print(f"  CER (mean)             : {stt_s.get('mean_cer', 'n/a')}")
        if stt_s.get("abstention_rate") is not None:
            print(f"  Low-confidence rate    : {stt_s['abstention_rate']:.1%}")
        print()

    if corr:
        print("Transcript Correction")
        print(f"  Attempt rate           : {corr.get('attempt_rate') or 'n/a'}")
        print(f"  Acceptance rate        : {corr.get('acceptance_rate') or 'n/a'}")
        print(f"  False correction rate  : {corr.get('false_correction_rate') or 'n/a'}")
        print(f"  Improvement rate       : {corr.get('improvement_rate') or 'n/a'}")
        print(f"  Degradation rate       : {corr.get('degradation_rate') or 'n/a'}")
        print()

    if rm:
        print("Routing")
        print(f"  Accuracy               : {rm.get('accuracy', 0):.1%}")
        print(f"  F1                     : {rm.get('f1', 0):.1%}")
        print(f"  False Positive Rate    : {rm.get('false_positive_rate', 0):.1%}  (unnecessary tool calls)")
        print(f"  False Negative Rate    : {rm.get('false_negative_rate', 0):.1%}  (missed tool calls)")
        print()

    if tsm and tsm.get("tool_accuracy") is not None:
        print("Tool Selection")
        print(f"  Accuracy               : {tsm.get('tool_accuracy', 0):.1%}")
        print(f"  Wrong tool rate        : {tsm.get('wrong_tool_rate', 0):.1%}")
        print()

    if am and am.get("args_semantic_match_rate") is not None:
        print("Tool Arguments")
        print(f"  Semantic match rate    : {am.get('args_semantic_match_rate', 0):.1%}")
        print(f"  Field accuracy         : {am.get('args_field_accuracy', 0):.1%}")
        print()

    if e2e:
        print("End-to-End Task Success")
        print(f"  Task success rate      : {e2e.get('task_success_rate', 0):.1%}")
        print(f"  Successes              : {e2e.get('successes')} / {e2e.get('n')}")
        fsd = e2e.get("failure_stage_breakdown", {})
        if fsd:
            print()
            print("  Failure Distribution:")
            for stage, count in sorted(fsd.items(), key=lambda x: -x[1]):
                print(f"    {stage:<25} {count}")
        print()

    lat = summary.get("latency", {})
    if lat:
        print("Stage Latency (ms)")
        for stage, stats in lat.items():
            print(f"  {stage:<12}  mean={stats.get('mean')}  p50={stats.get('p50')}  p90={stats.get('p90')}  p99={stats.get('p99')}")
        print()

    print("Privacy")
    print("  Privacy metric: not_yet_measured")
    print("  (Speaker verification evaluation planned for Phase 3)")
    print()
    print("=" * 65)
