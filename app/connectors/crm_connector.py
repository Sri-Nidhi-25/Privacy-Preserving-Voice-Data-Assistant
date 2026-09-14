import json
from pathlib import Path
from .base import BaseConnector
from typing import Optional

class CRMConnector(BaseConnector):
    def __init__(self, data_path: Optional[Path] = None):
        self.data_path = data_path or Path("data/customers.json")

    def fetch(self, status: Optional[str] = None, limit: Optional[int] = None, **kwargs):
        try:
            with open(self.data_path) as f:
                data = json.load(f)
        except FileNotFoundError:
            return []   # Gracefully return empty list if file missing

        if status:
            data = [c for c in data if c.get("status") == status]
        if limit is not None:   # Use `is not None` so limit=0 works
            data = data[:int(limit)]
        return data
    
