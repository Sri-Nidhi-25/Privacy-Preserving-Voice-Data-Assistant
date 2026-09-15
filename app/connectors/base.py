from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional


@dataclass
class ConnectorResult:
    data: List[Dict[str, Any]]
    retrieved_at: str
    source_last_updated: Optional[str] = None
    data_age_seconds: Optional[float] = None
    freshness_status: str = "unknown"  # "fresh" | "stale_usable" | "too_stale" | "unknown" | "future_timestamp"
    freshness_warning: Optional[str] = None
    success: bool = True
    error: Optional[str] = None
    connector_name: str = ""

    @property
    def is_empty(self) -> bool:
        return self.success and len(self.data) == 0


def evaluate_freshness(
    data_age_seconds: Optional[float],
    source_last_updated: Optional[str] = None,
    max_fresh_seconds: float = 86400.0,
    max_usable_seconds: float = 604800.0,
) -> tuple[str, Optional[str]]:
    """
    Phase 3 Data Freshness Policy:
      - fresh: age <= 1 day
      - stale_usable: 1 day < age <= 7 days
      - too_stale: age > 7 days
      - future_timestamp: age < 0
      - unknown: no timestamp available
    """
    if source_last_updated is None or data_age_seconds is None:
        return "unknown", "Data source update time is unknown."
    if data_age_seconds < 0:
        return "future_timestamp", "Source timestamp is in the future (clock skew detected)."
    if data_age_seconds <= max_fresh_seconds:
        return "fresh", None
    if data_age_seconds <= max_usable_seconds:
        days = int(data_age_seconds // 86400)
        return "stale_usable", f"Data may be stale (source last updated {days} day(s) ago)."
    return "too_stale", "Data exceeds maximum freshness window (>7 days old)."


class BaseConnector(ABC):
    @abstractmethod
    def fetch(self, **kwargs) -> List[Dict[str, Any]]:
        """Backwards-compatible query method returning raw list of records."""
        pass

    def fetch_result(self, **kwargs) -> ConnectorResult:
        """Structured query method returning ConnectorResult with freshness and status metadata."""
        now = datetime.now(timezone.utc)
        retrieved_at = now.isoformat()
        try:
            data = self.fetch(**kwargs)
            source_last_updated = None
            data_age = None
            if hasattr(self, "data_path") and isinstance(self.data_path, Path) and self.data_path.exists():
                mtime = self.data_path.stat().st_mtime
                dt_mtime = datetime.fromtimestamp(mtime, tz=timezone.utc)
                source_last_updated = dt_mtime.isoformat()
                data_age = (now - dt_mtime).total_seconds()

            status, warning = evaluate_freshness(data_age, source_last_updated)

            return ConnectorResult(
                data=data,
                retrieved_at=retrieved_at,
                source_last_updated=source_last_updated,
                data_age_seconds=data_age,
                freshness_status=status,
                freshness_warning=warning,
                success=True,
                connector_name=self.__class__.__name__,
            )
        except Exception as exc:
            return ConnectorResult(
                data=[],
                retrieved_at=retrieved_at,
                source_last_updated=None,
                data_age_seconds=None,
                freshness_status="unknown",
                freshness_warning=None,
                success=False,
                error=str(exc),
                connector_name=self.__class__.__name__,
            )

