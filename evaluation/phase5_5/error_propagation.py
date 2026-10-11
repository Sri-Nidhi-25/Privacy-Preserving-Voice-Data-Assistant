"""
evaluation/phase5_5/error_propagation.py

Error Propagation and Containment Analysis.
Traces errors entering, created, contained, and resulting in unsafe execution
across each stage of the voice pipeline:
  - STT
  - Correction
  - Routing
  - Abstention
  - Tool Selection
  - Argument Validation
  - Connector
"""
from typing import Any, Dict, List


ORDERED_STAGES = [
    "STT",
    "Correction",
    "Routing",
    "Abstention",
    "Tool Selection",
    "Arguments",
    "Connector",
]


def analyze_error_propagation(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Computes stage-by-stage error entry, generation, containment, and unsafe execution.
    """
    stats = {
        stage: {
            "errors_entering": 0,
            "errors_created": 0,
            "errors_contained": 0,
            "unsafe_outcomes": 0,
        }
        for stage in ORDERED_STAGES
    }

    for r in records:
        expected = r.get("expected", {})
        should_execute = expected.get("should_execute", True)
        stt = r.get("stt", {})
        corr = r.get("correction", {})
        routing = r.get("routing", {})
        abst = r.get("abstention", {})
        tool = r.get("tool", {})
        exec_info = r.get("execution", {})

        # Stage 1: STT
        has_stt_error = False
        wer = stt.get("wer", 0.0)
        if (wer is not None and wer > 0.35) or stt.get("low_confidence_abstain") and should_execute:
            has_stt_error = True
            stats["STT"]["errors_created"] += 1

        # STT containment: If low-confidence STT catches non-speech/garbage
        if not should_execute and stt.get("low_confidence_abstain"):
            stats["STT"]["errors_contained"] += 1

        # Stage 2: Correction
        has_corr_error = False
        entering_corr = has_stt_error
        if entering_corr:
            stats["Correction"]["errors_entering"] += 1

        # Did correction fix the STT error?
        if has_stt_error and corr.get("changed") and corr.get("correction_accepted"):
            stats["Correction"]["errors_contained"] += 1
            has_stt_error = False

        # Did correction create a new error?
        if not has_stt_error and corr.get("correction_rejected") and corr.get("changed"):
            has_corr_error = True
            stats["Correction"]["errors_created"] += 1

        # Stage 3: Routing
        curr_error = has_stt_error or has_corr_error
        if curr_error:
            stats["Routing"]["errors_entering"] += 1

        # Routing error created on distractors/domain nouns
        routing_misclassified = False
        expected_route = expected.get("expected_route", "tool" if should_execute else "direct")
        actual_route = routing.get("route", "direct")
        if not should_execute and actual_route == "tool":
            routing_misclassified = True
            stats["Routing"]["errors_created"] += 1
        elif should_execute and actual_route != "tool":
            routing_misclassified = True
            stats["Routing"]["errors_created"] += 1

        # Stage 4: Abstention
        entering_abst = curr_error or routing_misclassified
        if entering_abst:
            stats["Abstention"]["errors_entering"] += 1

        abst_decision = abst.get("decision", "EXECUTE")
        is_unsafe_tool_call = False

        if not should_execute:
            if abst_decision in ("ABSTAIN", "DIRECT"):
                # Abstention contained the routing false-positive!
                stats["Abstention"]["errors_contained"] += 1
            else:
                # Failed to abstain on distractor
                stats["Abstention"]["errors_created"] += 1
                is_unsafe_tool_call = True
                stats["Abstention"]["unsafe_outcomes"] += 1
        else:
            if abst_decision == "ABSTAIN":
                # False negative: prevented valid execution
                stats["Abstention"]["errors_created"] += 1

        # Stage 5: Tool Selection
        if is_unsafe_tool_call:
            stats["Tool Selection"]["errors_entering"] += 1
            stats["Tool Selection"]["unsafe_outcomes"] += 1

        expected_tool = expected.get("expected_tool")
        actual_tool = tool.get("selected")
        if should_execute and abst_decision == "EXECUTE":
            if actual_tool != expected_tool:
                stats["Tool Selection"]["errors_created"] += 1
                stats["Tool Selection"]["unsafe_outcomes"] += 1

        # Stage 6: Arguments
        if should_execute and abst_decision == "EXECUTE" and actual_tool == expected_tool:
            if tool.get("validation_error"):
                stats["Arguments"]["errors_created"] += 1
                # Was it caught by schema validation?
                stats["Arguments"]["errors_contained"] += 1

        # Stage 7: Connector
        if should_execute and abst_decision == "EXECUTE" and actual_tool == expected_tool:
            if not exec_info.get("connector_success", True):
                stats["Connector"]["errors_created"] += 1
                if exec_info.get("retry_succeeded"):
                    stats["Connector"]["errors_contained"] += 1
                else:
                    stats["Connector"]["unsafe_outcomes"] += 1

    return {
        "ordered_stages": ORDERED_STAGES,
        "table": stats,
    }
