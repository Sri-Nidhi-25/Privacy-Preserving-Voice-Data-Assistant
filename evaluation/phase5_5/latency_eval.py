"""
evaluation/phase5_5/latency_eval.py

Per-Stage Latency Profiling.
Computes median (p50), 90th percentile (p90), and 95th percentile (p95)
latency across every stage in the end-to-end voice pipeline:
  - Audio Validation
  - Voice Obfuscation
  - Whisper STT
  - Transcript Correction
  - Intent Routing & Selective Abstention
  - Tool Execution & Connector
  - Text-to-Speech (TTS)
  - Total Pipeline Latency
"""
from typing import Any, Dict, List
import numpy as np


LATENCY_STAGES = [
    "validation",
    "obfuscation",
    "stt",
    "correction",
    "routing",
    "abstention",
    "tool",
    "tts",
    "total",
]


def profile_latencies(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    collected = {s: [] for s in LATENCY_STAGES}

    for r in records:
        latencies = r.get("latency_ms", {})
        for s in LATENCY_STAGES:
            val = latencies.get(s)
            if val is not None and val >= 0:
                collected[s].append(val)

    summary = {}
    for s in LATENCY_STAGES:
        vals = collected[s]
        if vals:
            summary[s] = {
                "count": len(vals),
                "mean_ms": round(float(np.mean(vals)), 1),
                "p50_ms": round(float(np.percentile(vals, 50)), 1),
                "p90_ms": round(float(np.percentile(vals, 90)), 1),
                "p95_ms": round(float(np.percentile(vals, 95)), 1),
            }
        else:
            summary[s] = {"count": 0, "mean_ms": 0.0, "p50_ms": 0.0, "p90_ms": 0.0, "p95_ms": 0.0}

    return summary
