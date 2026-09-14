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
    success: bool = True
    error: Optional[str] = None
    connector_name: str = ""

    @property
    def is_empty(self) -> bool:
        return self.success and len(self.data) == 0


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
            # Inspect file modification time if available
            source_last_updated = None
            data_age = None
            if hasattr(self, "data_path") and isinstance(self.data_path, Path) and self.data_path.exists():
                mtime = self.data_path.stat().st_mtime
                dt_mtime = datetime.fromtimestamp(mtime, tz=timezone.utc)
                source_last_updated = dt_mtime.isoformat()
                data_age = max(0.0, (now - dt_mtime).total_seconds())

            return ConnectorResult(
                data=data,
                retrieved_at=retrieved_at,
                source_last_updated=source_last_updated,
                data_age_seconds=data_age,
                success=True,
                connector_name=self.__class__.__name__,
            )
        except Exception as exc:
            return ConnectorResult(
                data=[],
                retrieved_at=retrieved_at,
                source_last_updated=None,
                data_age_seconds=None,
                success=False,
                error=str(exc),
                connector_name=self.__class__.__name__,
            )

