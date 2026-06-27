import json
from pathlib import Path
from .base import BaseConnector
from typing import Optional

class CRMConnector(BaseConnector):
    def fetch(self, status: Optional[str] = None, limit: Optional[int] = None, **kwargs):
        with open(Path("data/customers.json")) as f:
            data = json.load(f)
        if status:
            data = [c for c in data if c.get("status") == status]
        if limit:
            data = data[:int(limit)]
        return data
