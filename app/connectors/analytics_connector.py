import json
from pathlib import Path
from .base import BaseConnector


class AnalyticsConnector(BaseConnector):
    def fetch(self, metric: str = None, days: int = None, **kwargs):
        with open(Path("data/analytics.json")) as f:
            data = json.load(f)
        if metric:
            data = [d for d in data if d.get("metric") == metric]
        if days:
            data = data[:days]
        return data
