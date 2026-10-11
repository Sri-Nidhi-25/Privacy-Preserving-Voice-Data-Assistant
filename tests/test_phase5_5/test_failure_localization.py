"""
Phase 5.5 — Failure Localization Unit Tests

Tests for evaluation/phase5_5/failure_localization.py

Failure localization maps per-case pipeline records to a responsible stage
without inspecting final test-set outputs to write rules. These tests use
synthetic records constructed to represent specific failure patterns.

The localize_failure() function returns:
    (failure_stage: Optional[str], failure_code: Optional[str], explanation: str)
"""

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _import_localize():
    from evaluation.phase5_5.failure_localization import localize_failure
    return localize_failure


def _make_record(
    *,
    wer: float = 0.0,
    stt_transcript: str = "some query",
    correction_changed: bool = False,
    routing_intent: str = "crm_query",
    abstention_decision: str = "EXECUTE",
    should_execute: bool = True,
    expected_tool: str = "get_crm_data",
    expected_route: str = "tool",
    selected_tool: str = "get_crm_data",
    no_tool_call: bool = False,
    connector_success: bool = True,
    tts_failed: bool = False,
    audio_validation_error: bool = False,
    pipeline_exception: str = "",
    injection_type: str = "",
) -> dict:
    """Build a synthetic nested pipeline record matching localize_failure() schema."""
    return {
        "audio_validation_error": audio_validation_error,
        "pipeline_exception": pipeline_exception or None,
        "injection_type": injection_type,
        "input_text": stt_transcript,
        "tts_failed": tts_failed,
        "expected": {
            "should_execute": should_execute,
            "expected_route": expected_route,
            "expected_tool": expected_tool,
            "expected_arguments": {},
        },
        "stt": {
            "wer": wer,
            "transcript": stt_transcript,
            "low_confidence_abstain": False,
        },
        "correction": {
            "changed": correction_changed,
            "corrected_transcript": stt_transcript,
        },
        "routing": {
            "intent": routing_intent,
        },
        "abstention": {
            "decision": abstention_decision,
            "reason": f"abstention decision: {abstention_decision}",
        },
        "tool": {
            "selected": None if no_tool_call else selected_tool,
            "arguments": {},
            "validation_error": None,
        },
        "execution": {
            "connector_success": connector_success,
            "connector_error": None if connector_success else "simulated_error",
        },
    }


# ---------------------------------------------------------------------------
# Test 1: STT attribution
# ---------------------------------------------------------------------------

class TestSTTLocalization:

    def test_high_wer_attributed_to_stt(self):
        """A record with WER > 0.50 should be attributed to STT stage."""
        localize = _import_localize()
        record = _make_record(wer=0.60)
        stage, code, _ = localize(record)
        assert stage == "STT", f"Expected STT attribution, got {stage!r}"

    def test_zero_wer_not_attributed_to_stt(self):
        """Perfect STT should not be blamed for a subsequent routing failure."""
        localize = _import_localize()
        # routing sends crm but expected analytics → routing/tool failure
        record = _make_record(
            wer=0.0,
            routing_intent="crm_query",
            expected_tool="get_analytics",
            expected_route="tool",
            selected_tool="get_crm_data",
        )
        stage, code, _ = localize(record)
        assert stage != "STT", f"STT should not be blamed for downstream failure"

    def test_moderate_wer_not_attributed_to_stt(self):
        """WER at 0.30 (below 0.50 threshold) should not trigger STT attribution."""
        localize = _import_localize()
        record = _make_record(wer=0.30)
        stage, code, _ = localize(record)
        # A moderate WER should not immediately blame STT if transcript is not empty
        assert stage != "STT", (
            f"WER=0.30 is below the 0.50 threshold; STT should not be attributed. Got {stage!r}"
        )


# ---------------------------------------------------------------------------
# Test 2: Abstention attribution
# ---------------------------------------------------------------------------

class TestAbstentionLocalization:

    def test_safe_abstention_returns_none_stage(self):
        """
        If expected should_execute=False and abstention=ABSTAIN:
        safe abstention — no failure stage.
        """
        localize = _import_localize()
        record = _make_record(
            should_execute=False,
            abstention_decision="ABSTAIN",
            expected_route="direct",
        )
        stage, code, explanation = localize(record)
        assert stage is None, (
            f"Safe abstention must not produce a failure stage, got {stage!r}"
        )

    def test_execute_when_should_abstain_attributed_to_abstention(self):
        """
        If should_execute=False but abstention=EXECUTE: missed abstention.
        Localization must attribute to ABSTENTION.
        """
        localize = _import_localize()
        record = _make_record(
            should_execute=False,
            abstention_decision="EXECUTE",
            expected_route="direct",
        )
        stage, code, _ = localize(record)
        assert stage == "ABSTENTION", (
            f"Missed abstention must be attributed to ABSTENTION, got {stage!r}"
        )
        assert code == "UNSAFE_EXECUTION_ON_DISTRACTOR"

    def test_abstain_when_should_execute_attributed_to_abstention(self):
        """
        If should_execute=True but abstention=ABSTAIN: false abstention.
        Localization must attribute to ABSTENTION.
        """
        localize = _import_localize()
        record = _make_record(
            should_execute=True,
            abstention_decision="ABSTAIN",
            expected_route="tool",
        )
        stage, code, _ = localize(record)
        assert stage == "ABSTENTION", (
            f"False abstention must be attributed to ABSTENTION, got {stage!r}"
        )
        assert code == "FALSE_ABSTENTION_ON_VALID_REQUEST"


# ---------------------------------------------------------------------------
# Test 3: Tool selection attribution
# ---------------------------------------------------------------------------

class TestToolSelectionLocalization:

    def test_wrong_tool_attributed_to_tool_selection(self):
        """
        Routing correct, abstention EXECUTE, but LLM selected wrong tool.
        """
        localize = _import_localize()
        record = _make_record(
            should_execute=True,
            abstention_decision="EXECUTE",
            routing_intent="crm_query",
            expected_tool="get_crm_data",
            selected_tool="get_analytics",  # wrong tool
        )
        stage, code, _ = localize(record)
        assert stage == "TOOL_SELECTION", (
            f"Wrong tool must be attributed to TOOL_SELECTION, got {stage!r}"
        )
        assert code == "WRONG_TOOL_SELECTED"

    def test_no_tool_call_when_required_attributed_to_tool_selection(self):
        """
        Expected EXECUTE, abstention said EXECUTE, but LLM called no tool.
        """
        localize = _import_localize()
        record = _make_record(
            should_execute=True,
            abstention_decision="EXECUTE",
            no_tool_call=True,
            expected_tool="get_crm_data",
        )
        stage, code, _ = localize(record)
        assert stage == "TOOL_SELECTION", (
            f"Missing tool call must be attributed to TOOL_SELECTION, got {stage!r}"
        )
        assert code == "NO_TOOL_INVOKED"


# ---------------------------------------------------------------------------
# Test 4: Successful case returns no failure stage
# ---------------------------------------------------------------------------

class TestSuccessfulCaseLocalization:

    def test_successful_execute_case_returns_no_failure(self):
        """A fully successful EXECUTE case must not be assigned a failure stage."""
        localize = _import_localize()
        record = _make_record(
            wer=0.0,
            should_execute=True,
            abstention_decision="EXECUTE",
            routing_intent="crm_query",
            expected_tool="get_crm_data",
            selected_tool="get_crm_data",
            connector_success=True,
        )
        stage, code, explanation = localize(record)
        assert stage is None, (
            f"Successful EXECUTE case must not have a failure stage, got {stage!r}"
        )
        assert code is None

    def test_successful_direct_route_returns_no_failure(self):
        """A successful DIRECT (ABSTAIN) routing must not produce a failure stage."""
        localize = _import_localize()
        record = _make_record(
            should_execute=False,
            abstention_decision="DIRECT",
            expected_route="direct",
        )
        stage, code, _ = localize(record)
        assert stage is None, (
            f"Safe DIRECT routing must not produce a failure stage, got {stage!r}"
        )


# ---------------------------------------------------------------------------
# Test 5: Connector error attribution
# ---------------------------------------------------------------------------

class TestConnectorLocalization:

    def test_connector_error_attributed_to_connector(self):
        """
        All prior stages succeeded but connector raised an error.
        Failure must be attributed to CONNECTOR stage.
        """
        localize = _import_localize()
        record = _make_record(
            should_execute=True,
            abstention_decision="EXECUTE",
            routing_intent="crm_query",
            expected_tool="get_crm_data",
            selected_tool="get_crm_data",
            connector_success=False,
        )
        stage, code, _ = localize(record)
        assert stage == "CONNECTOR", (
            f"Connector error must be attributed to CONNECTOR stage, got {stage!r}"
        )
        assert code == "CONNECTOR_EXECUTION_FAILED"

    def test_transient_connector_error_with_injection_returns_none(self):
        """
        If injection_type is 'transient_connector_error', the retry guard
        handled it gracefully — localization returns no failure.
        """
        localize = _import_localize()
        record = _make_record(
            should_execute=True,
            abstention_decision="EXECUTE",
            routing_intent="crm_query",
            expected_tool="get_crm_data",
            selected_tool="get_crm_data",
            connector_success=False,
            injection_type="transient_connector_error",
        )
        stage, code, _ = localize(record)
        assert stage is None, (
            f"Gracefully-handled transient connector error must return no failure stage, got {stage!r}"
        )


# ---------------------------------------------------------------------------
# Test 6: System / audio validation attribution
# ---------------------------------------------------------------------------

class TestSystemLocalization:

    def test_audio_validation_error_attributed_to_system(self):
        """An audio validation error is attributed to SYSTEM stage."""
        localize = _import_localize()
        record = _make_record(audio_validation_error=True)
        stage, code, _ = localize(record)
        assert stage == "SYSTEM", f"Expected SYSTEM, got {stage!r}"
        assert code == "AUDIO_VALIDATION_FAILED"

    def test_pipeline_crash_attributed_to_system(self):
        """An unhandled pipeline exception is attributed to SYSTEM stage."""
        localize = _import_localize()
        record = _make_record(pipeline_exception="RuntimeError: LLM timed out")
        stage, code, _ = localize(record)
        assert stage == "SYSTEM", f"Expected SYSTEM, got {stage!r}"
        assert code == "PIPELINE_CRASH"
