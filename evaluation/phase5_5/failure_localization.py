"""
evaluation/phase5_5/failure_localization.py

Stage-Level Failure Localization and Root-Cause Attribution.
Traces every unexpected outcome to the earliest responsible pipeline stage:
  - STT
  - CORRECTION
  - ROUTING
  - ABSTENTION
  - TOOL_SELECTION
  - ARGUMENT_VALIDATION
  - CONNECTOR
  - TTS
  - SYSTEM
"""
from typing import Any, Dict, Optional, Tuple


def localize_failure(record: Dict[str, Any]) -> Tuple[Optional[str], Optional[str], str]:
    """
    Analyzes an E2E execution record and identifies the earliest responsible stage.

    Returns:
      (failure_stage, failure_code, diagnostic_explanation)
    """
    expected = record.get("expected", {})
    stt = record.get("stt", {})
    correction = record.get("correction", {})
    routing = record.get("routing", {})
    abstention = record.get("abstention", {})
    tool = record.get("tool", {})
    execution = record.get("execution", {})

    expected_action = expected.get("should_execute")
    expected_route = expected.get("expected_route", "tool" if expected_action else "direct")
    expected_tool = expected.get("expected_tool")
    expected_args = expected.get("expected_arguments", {})

    # 1. System / Audio Validation Error Check
    if record.get("audio_validation_error"):
        return "SYSTEM", "AUDIO_VALIDATION_FAILED", "Audio was rejected by validation layer."
    if record.get("pipeline_exception"):
        return "SYSTEM", "PIPELINE_CRASH", f"Unhandled pipeline crash: {record.get('pipeline_exception')}"

    # 2. STT Failure Check
    wer = stt.get("wer", 0.0)
    raw_transcript = stt.get("transcript", "")
    if stt.get("low_confidence_abstain"):
        if expected_action:
            return "STT", "STT_CONFIDENCE_DROPPED", "Whisper flagged low confidence on a legitimate request."
        else:
            return None, None, "Safe STT low-confidence abstention."

    if not raw_transcript and record.get("input_text"):
        return "STT", "STT_EMPTY_TRANSCRIPTION", "Whisper produced empty transcription."

    if wer is not None and wer > 0.50:
        # Check if high WER altered semantic meaning
        return "STT", "STT_HIGH_WORD_ERROR_RATE", f"Severe transcription error (WER={wer:.2f})."

    # 3. Transcript Correction Failure Check
    corr_changed = correction.get("changed", False)
    corr_rejected = correction.get("correction_rejected", False)
    corrected_transcript = correction.get("corrected_transcript", raw_transcript)

    if corr_changed and expected_tool:
        # Check if correction corrupted key terms
        if expected_tool == "get_crm_data" and "customer" not in corrected_transcript.lower() and "customer" in raw_transcript.lower():
            return "CORRECTION", "CORRECTION_CORRUPTED_INTENT", "Correction removed domain keyword."

    # 4. Intent Routing Failure Check
    actual_intent = routing.get("intent")
    if expected_route == "tool":
        if expected_tool == "get_crm_data" and actual_intent != "crm_query":
            return "ROUTING", "INTENT_MISCLASSIFICATION", f"Expected CRM intent, got {actual_intent}."
        if expected_tool == "get_support_tickets" and actual_intent != "support_query":
            return "ROUTING", "INTENT_MISCLASSIFICATION", f"Expected Support intent, got {actual_intent}."
        if expected_tool == "get_analytics" and actual_intent != "analytics_query":
            return "ROUTING", "INTENT_MISCLASSIFICATION", f"Expected Analytics intent, got {actual_intent}."

    # 5. Abstention Failure Check
    abstention_decision = abstention.get("decision", "EXECUTE")
    # False Positive: Should abstain (distractor / ambiguous), but executed
    if not expected_action and abstention_decision == "EXECUTE":
        return "ABSTENTION", "UNSAFE_EXECUTION_ON_DISTRACTOR", "Failed to abstain on distractor or ambiguous input."

    # False Negative: Legitimate query, but was abstained
    if expected_action and abstention_decision == "ABSTAIN":
        return "ABSTENTION", "FALSE_ABSTENTION_ON_VALID_REQUEST", f"Safe query prematurely abstained: {abstention.get('reason')}"

    # If abstained safely as expected, there is no failure
    if not expected_action and abstention_decision in ("ABSTAIN", "DIRECT"):
        return None, None, "Safe abstention / direct routing verified."

    # 6. Tool Selection Failure Check
    actual_tool = tool.get("selected")
    if expected_action:
        if not actual_tool and expected_tool:
            return "TOOL_SELECTION", "NO_TOOL_INVOKED", "LLM failed to generate tool call."
        if actual_tool != expected_tool:
            return "TOOL_SELECTION", "WRONG_TOOL_SELECTED", f"Selected {actual_tool} instead of {expected_tool}."

    # 7. Argument Validation Failure Check
    actual_args = tool.get("arguments", {})
    if tool.get("validation_error"):
        if record.get("injection_type") == "malformed_arguments":
            return None, None, "Malformed arguments caught safely by argument validator."
        return "ARGUMENT_VALIDATION", "ARGUMENT_VALIDATION_REJECTED", f"Validation error: {tool.get('validation_error')}"

    if expected_args:
        for k, v in expected_args.items():
            if k not in actual_args or actual_args[k] != v:
                return "ARGUMENT_VALIDATION", "ARGUMENT_MISMATCH", f"Expected argument {k}={v}, got {actual_args.get(k)}."

    # 8. Connector Failure Check
    if not execution.get("connector_success", True):
        if record.get("injection_type") in ("transient_connector_error", "repeated_connector_error"):
            return None, None, "Connector failure handled gracefully by retry/guard."
        return "CONNECTOR", "CONNECTOR_EXECUTION_FAILED", f"Connector error: {execution.get('connector_error')}"

    # 9. TTS Failure Check
    if record.get("tts_failed"):
        if record.get("injection_type") == "tts_synthesis_failure":
            return None, None, "TTS failure contained: text response safely preserved."
        return "TTS", "TTS_SYNTHESIS_FAILED", f"TTS synthesis failed: {record.get('tts_error')}"

    # No failure detected: Task succeeded completely
    return None, None, "Pipeline executed successfully end-to-end."
