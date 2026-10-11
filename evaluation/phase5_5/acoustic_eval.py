"""
evaluation/phase5_5/acoustic_eval.py

Evaluates the interaction between physical acoustic SNR perturbations,
speech-to-text accuracy (WER/CER), downstream routing, and selective abstention.
"""
from typing import Any, Dict, List
import numpy as np


def analyze_acoustic_interaction(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Groups records by acoustic condition (clean, 20db, 10db) and measures
    the degradation cascade from audio -> STT -> Routing -> Abstention -> Success.
    """
    conditions = ["clean", "20db", "10db"]
    grouped = {c: [] for c in conditions}

    for r in records:
        cond = r.get("audio", {}).get("condition", "clean")
        if cond in grouped:
            grouped[cond].append(r)

    results = {}
    for cond, group in grouped.items():
        if not group:
            continue
        wers = [r.get("stt", {}).get("wer", 0.0) for r in group if r.get("stt", {}).get("wer") is not None]
        cers = [r.get("stt", {}).get("cer", 0.0) for r in group if r.get("stt", {}).get("cer") is not None]
        avg_logprobs = [r.get("stt", {}).get("avg_logprob", 0.0) for r in group if r.get("stt", {}).get("avg_logprob") is not None]

        total = len(group)
        correct_route = 0
        safe_abstentions = 0
        unsafe_executions = 0
        correct_executions = 0

        for r in group:
            expected = r.get("expected", {})
            should_execute = expected.get("should_execute", True)
            abst = r.get("abstention", {})
            dec = abst.get("decision", "EXECUTE")
            tool = r.get("tool", {})

            if should_execute:
                if dec == "EXECUTE" and tool.get("selected") == expected.get("expected_tool"):
                    correct_executions += 1
                    correct_route += 1
            else:
                if dec in ("ABSTAIN", "DIRECT"):
                    safe_abstentions += 1
                    correct_route += 1
                else:
                    unsafe_executions += 1

        task_success = (correct_executions + safe_abstentions) / total if total > 0 else 0.0

        results[cond] = {
            "sample_size": total,
            "mean_wer": round(float(np.mean(wers)), 4) if wers else 0.0,
            "mean_cer": round(float(np.mean(cers)), 4) if cers else 0.0,
            "mean_logprob": round(float(np.mean(avg_logprobs)), 4) if avg_logprobs else 0.0,
            "routing_retention_rate": round(correct_route / total, 4) if total > 0 else 0.0,
            "unsafe_execution_rate": round(unsafe_executions / total, 4) if total > 0 else 0.0,
            "task_success_rate": round(task_success, 4),
        }

    return results
