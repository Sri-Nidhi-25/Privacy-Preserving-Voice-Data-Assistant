from typing import List, Dict
from app.config import settings


def apply_voice_limits(data: List[Dict]) -> List[Dict]:
    return data[: settings.MAX_RESULTS]
