from typing import List, Dict
from app.config import settings


def summarize_if_large(data: List[Dict]) -> List[Dict]:
    if len(data) > settings.MAX_RESULTS:
        return [{"summary": f"{len(data)} records found. Showing first {settings.MAX_RESULTS}."}]
    return data
