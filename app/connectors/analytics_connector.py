import json
from pathlib import Path
from .base import BaseConnector


class AnalyticsConnector(BaseConnector):
    def __init__(self, data_path: Path | None = None):
        self.data_path = data_path or Path("data/analytics.json")

    def fetch(self, metric: str | None = None, days: int | None = None, **kwargs):
        try:
            with open(self.data_path) as f:
                data = json.load(f)
        except FileNotFoundError:
            return [] 
        
        if metric:
            data = [d for d in data if d.get("metric") == metric]
        if days:
            data = data[:days]
        return data
