from datetime import datetime, timezone
from fastapi import APIRouter, Query
from app.connectors.crm_connector import CRMConnector
from app.connectors.support_connector import SupportConnector
from app.connectors.analytics_connector import AnalyticsConnector
from app.services.business_rules import apply_voice_limits
from app.services.voice_optimizer import summarize_if_large
from app.models.common import DataResponse, Metadata

router = APIRouter()

CONNECTORS = {
    "crm": CRMConnector(),
    "support": SupportConnector(),
    "analytics": AnalyticsConnector(),
}


@router.get("/data/{source}", response_model=DataResponse)
def get_data(source: str, limit: int = Query(10)):
    connector = CONNECTORS.get(source)
    if not connector:
        return DataResponse(
            data=[],
            metadata=Metadata(total_results=0, returned_results=0, data_freshness="unknown"),
        )

    raw_data = connector.fetch()
    optimized = summarize_if_large(apply_voice_limits(raw_data))

    metadata = Metadata(
        total_results=len(raw_data),
        returned_results=len(optimized),
        data_freshness=f"Data as of {datetime.now(timezone.utc).isoformat()}",
    )
    return DataResponse(data=optimized, metadata=metadata)
