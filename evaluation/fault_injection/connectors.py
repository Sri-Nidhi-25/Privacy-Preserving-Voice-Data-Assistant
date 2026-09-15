"""
evaluation/fault_injection/connectors.py - Connector fault injection wrapper.

Enables controlled simulation of connector failure modes for evaluation:
  - timeout
  - exception / crash
  - empty results
  - malformed records
  - stale data (>7 days)
  - future timestamp (clock skew)
  - transient error (recovers on retry)
"""
import time
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from app.connectors.base import BaseConnector, ConnectorResult, evaluate_freshness


class FaultInjectingConnector(BaseConnector):
    def __init__(
        self,
        base_connector: BaseConnector,
        failure_mode: str = "none",
        fail_times: int = 1,
        latency_seconds: float = 0.0,
    ):
        """
        Args:
            base_connector: The underlying connector being wrapped.
            failure_mode: One of:
                'none': normal passthrough
                'timeout': simulates a connector timeout exception
                'exception': simulates an unexpected database/service exception
                'empty': returns empty data [] with success=True
                'malformed': returns records with missing/invalid fields
                'stale': returns data timestamped 30 days ago
                'future_timestamp': returns data timestamped 1 day in the future
                'transient_error': fails `fail_times` then succeeds
            fail_times: Number of times to fail before succeeding in 'transient_error' mode.
            latency_seconds: Artificial delay injected before responding.
        """
        self.base_connector = base_connector
        self.failure_mode = failure_mode
        self.fail_times = fail_times
        self.fail_count = 0
        self.latency_seconds = latency_seconds
        self.call_count = 0

    def fetch(self, **kwargs) -> List[Dict[str, Any]]:
        self.call_count += 1
        if self.latency_seconds > 0:
            time.sleep(self.latency_seconds)

        if self.failure_mode == "timeout":
            raise TimeoutError("Simulated connector timeout")

        if self.failure_mode == "exception":
            raise RuntimeError("Simulated connector database failure")

        if self.failure_mode == "empty":
            return []

        if self.failure_mode == "malformed":
            return [{"corrupt_field": None, "invalid_id": "????"}]

        if self.failure_mode == "transient_error":
            if self.fail_count < self.fail_times:
                self.fail_count += 1
                raise ConnectionResetError("Simulated temporary connection reset")

        return self.base_connector.fetch(**kwargs)

    def fetch_result(self, **kwargs) -> ConnectorResult:
        now = datetime.now(timezone.utc)
        retrieved_at = now.isoformat()

        if self.failure_mode == "timeout":
            return ConnectorResult(
                data=[],
                retrieved_at=retrieved_at,
                source_last_updated=None,
                data_age_seconds=None,
                freshness_status="unknown",
                success=False,
                error="Simulated connector timeout",
                connector_name=f"FaultInjecting({self.base_connector.__class__.__name__})",
            )

        if self.failure_mode == "exception":
            return ConnectorResult(
                data=[],
                retrieved_at=retrieved_at,
                source_last_updated=None,
                data_age_seconds=None,
                freshness_status="unknown",
                success=False,
                error="Simulated connector database failure",
                connector_name=f"FaultInjecting({self.base_connector.__class__.__name__})",
            )

        if self.failure_mode == "stale":
            stale_dt = now - timedelta(days=30)
            stale_iso = stale_dt.isoformat()
            age_sec = 30 * 86400.0
            status, warning = evaluate_freshness(age_sec, stale_iso)
            raw_data = self.base_connector.fetch(**kwargs)
            return ConnectorResult(
                data=raw_data,
                retrieved_at=retrieved_at,
                source_last_updated=stale_iso,
                data_age_seconds=age_sec,
                freshness_status=status,
                freshness_warning=warning,
                success=True,
                connector_name=f"FaultInjecting({self.base_connector.__class__.__name__})",
            )

        if self.failure_mode == "future_timestamp":
            future_dt = now + timedelta(days=1)
            future_iso = future_dt.isoformat()
            age_sec = -86400.0
            status, warning = evaluate_freshness(age_sec, future_iso)
            raw_data = self.base_connector.fetch(**kwargs)
            return ConnectorResult(
                data=raw_data,
                retrieved_at=retrieved_at,
                source_last_updated=future_iso,
                data_age_seconds=age_sec,
                freshness_status=status,
                freshness_warning=warning,
                success=True,
                connector_name=f"FaultInjecting({self.base_connector.__class__.__name__})",
            )

        return super().fetch_result(**kwargs)
