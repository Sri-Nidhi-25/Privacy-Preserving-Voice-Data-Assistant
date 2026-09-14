"""
evaluation/metrics/end_to_end.py - End-to-end task success and failure propagation.

End-to-end success is strict:
  - For "tool" cases: routing correct AND tool selected correctly AND args semantically
    correct AND connector returned data AND answer generated.
  - For "direct" cases: routing correct AND answer generated (non-empty).

Failure is classified at the first stage that went wrong.
"""
from typing import List, Optional


FAILURE_STAGE_ORDER = [
    "audio_validation",
    "audio_decode",
    "obfuscation",
    "stt",
    "stt_abstention",
    "transcript_correction",
    "routing",
    "tool_selection",
    "tool_arguments",
    "connector",
    "data_quality",
    "answer_generation",
    "tts",
]


def classify_failure_stage(record: dict) -> Optional[str]:
    """
    Determine the first failure stage for a record that did NOT succeed end-to-end.
    Returns None if the task succeeded.
    """
    if record.get("end_to_end_success"):
        return None

    # STT abstention (system correctly refused low-confidence audio)
    if record.get("stt_low_confidence_decision"):
        return "stt_abstention"

    # Routing
    if record.get("routing_correct") is False:
        return "routing"

    # Tool selection (only if routing was correct and tool was expected)
    if record.get("expected_route") == "tool":
        if record.get("tool_selection_correct") is False:
            return "tool_selection"
        # Tool argument validation
        if record.get("args_semantic_match") is False:
            return "tool_arguments"
        # Connector
        if record.get("connector_success") is False:
            return "connector"

    # Answer generation fallback
    if not record.get("answer_text"):
        return "answer_generation"

    return "unknown"


def compute_e2e_success(record: dict) -> bool:
    """
    Strict end-to-end success:
    - Routing correct
    - For tool cases: tool selected correctly, args semantically correct,
      connector succeeded (result_count >= 0), answer present
    - For direct cases: routing correct and answer present
    """
    if not record.get("routing_correct"):
        return False

    if record.get("expected_route") == "tool":
        if not record.get("tool_selection_correct"):
            return False
        # Args check: if expected_args is non-empty, must be semantically matched
        expected_args = record.get("expected_args", {})
        if expected_args and not record.get("args_semantic_match", False):
            return False
        if not record.get("connector_success", True):
            return False

    if not record.get("answer_text"):
        return False

    return True


def end_to_end_metrics(records: List[dict]) -> dict:
    """Aggregate end-to-end results across all records."""
    n = len(records)
    if not n:
        return {"n": 0, "task_success_rate": None}

    successes = sum(1 for r in records if r.get("end_to_end_success"))
    failures = n - successes

    # Failure stage breakdown
    stage_counts = {}
    for r in records:
        stage = r.get("failure_stage")
        if stage:
            stage_counts[stage] = stage_counts.get(stage, 0) + 1

    # By category
    by_cat = {}
    for r in records:
        cat = r.get("category", "unknown")
        if cat not in by_cat:
            by_cat[cat] = {"n": 0, "success": 0}
        by_cat[cat]["n"] += 1
        if r.get("end_to_end_success"):
            by_cat[cat]["success"] += 1
    for cat in by_cat:
        d = by_cat[cat]
        d["success_rate"] = round(d["success"] / d["n"], 4) if d["n"] else 0.0

    return {
        "n": n,
        "successes": successes,
        "failures": failures,
        "task_success_rate": round(successes / n, 4),
        "failure_stage_breakdown": stage_counts,
        "by_category": by_cat,
    }


def generate_failure_matrix(records: List[dict]) -> List[dict]:
    """
    Generate a tool-calling failure matrix row per record.
    Useful for spotting propagation patterns visually.
    """
    rows = []
    for r in records:
        rows.append({
            "case_id": r.get("case_id"),
            "category": r.get("category"),
            "route_ok": "✓" if r.get("routing_correct") else "✗",
            "tool_ok": (
                "✓" if r.get("tool_selection_correct")
                else ("—" if r.get("expected_route") != "tool" else "✗")
            ),
            "args_ok": (
                "✓" if r.get("args_semantic_match")
                else ("—" if r.get("expected_route") != "tool" or not r.get("tool_selection_correct") else "✗")
            ),
            "connector_ok": (
                "✓" if r.get("connector_success", True)
                else ("—" if r.get("expected_route") != "tool" else "✗")
            ),
            "e2e": "✓" if r.get("end_to_end_success") else "✗",
            "failure_stage": r.get("failure_stage", "—"),
        })
    return rows
