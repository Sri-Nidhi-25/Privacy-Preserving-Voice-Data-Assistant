import json
from pathlib import Path
from .base import BaseConnector
from typing import Optional

class CRMConnector(BaseConnector):
    def fetch(self, status: Optional[str] = None, limit: Optional[int] = None, **kwargs):
        try:
            with open(Path("data/customers.json")) as f:
                data = json.load(f)
        except FileNotFoundError:
            return []   # Gracefully return empty list if file missing

        if status:
            data = [c for c in data if c.get("status") == status]
        if limit is not None:   # Use `is not None` so limit=0 works
            data = data[:int(limit)]
        return data
    
