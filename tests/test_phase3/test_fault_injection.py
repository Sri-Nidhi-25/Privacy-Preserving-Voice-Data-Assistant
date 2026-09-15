"""Tests for evaluation/fault_injection package."""
import pytest
from pathlib import Path
from app.connectors.crm_connector import CRMConnector
from evaluation.fault_injection.connectors import FaultInjectingConnector
from evaluation.fault_injection.stt_fault import MockFaultySTTEngine
from evaluation.fault_injection.llm_fault import MockFaultyLLMClient
from evaluation.fault_injection.tts_fault import MockFaultyTTSSynthesizer


class TestConnectorFaultInjection:
    def test_timeout_mode(self):
        base = CRMConnector()
        faulty = FaultInjectingConnector(base, failure_mode="timeout")
        res = faulty.fetch_result()
        assert res.success is False
        assert len(res.data) == 0
        assert "timeout" in (res.error or "").lower()

    def test_exception_mode(self):
        base = CRMConnector()
        faulty = FaultInjectingConnector(base, failure_mode="exception")
        res = faulty.fetch_result()
        assert res.success is False
        assert len(res.data) == 0
        assert "failure" in (res.error or "").lower()

    def test_stale_data_mode(self):
        base = CRMConnector()
        faulty = FaultInjectingConnector(base, failure_mode="stale")
        res = faulty.fetch_result()
        assert res.success is True
        assert res.freshness_status in ("stale_usable", "too_stale")
        assert res.freshness_warning is not None

    def test_future_timestamp_mode(self):
        base = CRMConnector()
        faulty = FaultInjectingConnector(base, failure_mode="future_timestamp")
        res = faulty.fetch_result()
        assert res.success is True
        assert res.freshness_status == "future_timestamp"

    def test_transient_error_recovery(self):
        base = CRMConnector()
        faulty = FaultInjectingConnector(base, failure_mode="transient_error", fail_times=1)
        with pytest.raises(ConnectionResetError):
            faulty.fetch()
        # Second call succeeds
        data = faulty.fetch()
        assert isinstance(data, list)


class TestSTTFaultInjection:
    def test_low_confidence_mode(self):
        engine = MockFaultySTTEngine(failure_mode="low_confidence")
        text, conf = engine.transcribe_with_confidence(Path("dummy.wav"))
        assert conf["low_confidence"] is True
        assert conf["avg_logprob"] < -1.0

    def test_timeout_mode(self):
        engine = MockFaultySTTEngine(failure_mode="timeout")
        with pytest.raises(TimeoutError):
            engine.transcribe_with_confidence(Path("dummy.wav"))

    def test_empty_mode(self):
        engine = MockFaultySTTEngine(failure_mode="empty")
        text, conf = engine.transcribe_with_confidence(Path("dummy.wav"))
        assert text == ""
        assert conf["low_confidence"] is True


class TestLLMFaultInjection:
    def test_timeout(self):
        client = MockFaultyLLMClient(failure_mode="timeout")
        with pytest.raises(TimeoutError):
            client.chat("test-model", [{"role": "user", "content": "hi"}])

    def test_invalid_args(self):
        client = MockFaultyLLMClient(failure_mode="invalid_args")
        res = client.chat("test-model", [{"role": "user", "content": "hi"}])
        calls = res["message"].get("tool_calls", [])
        assert len(calls) == 1
        assert calls[0]["function"]["arguments"]["status"] == "unsupported_status_value"


class TestTTSFaultInjection:
    @pytest.mark.asyncio
    async def test_exception(self, tmp_path):
        tts = MockFaultyTTSSynthesizer(failure_mode="exception")
        with pytest.raises(RuntimeError):
            await tts.synthesize("test", tmp_path / "test.mp3")

    @pytest.mark.asyncio
    async def test_success_creates_file(self, tmp_path):
        tts = MockFaultyTTSSynthesizer(failure_mode="none")
        out = tmp_path / "test.mp3"
        res = await tts.synthesize("test", out)
        assert res is True
        assert out.exists()
