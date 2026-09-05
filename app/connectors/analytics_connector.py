import json
from pathlib import Path
from .base import BaseConnector


class AnalyticsConnector(BaseConnector):
    def fetch(self, metric: str | None = None, days: int | None = None, **kwargs):
        try:
            with open(Path("data/analytics.json")) as f:
                data = json.load(f)
        except FileNotFoundError:
            return [] 
        
        if metric:
            data = [d for d in data if d.get("metric") == metric]
        if days:
            data = data[:days]
        return data
