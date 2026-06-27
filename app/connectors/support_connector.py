import json
from pathlib import Path
from typing import Optional
from .base import BaseConnector


class SupportConnector(BaseConnector):
    def fetch(self, status: Optional[str] = None, priority: Optional[str] = None, limit: Optional[int] = None, **kwargs):
        with open(Path("data/support_tickets.json")) as f:
            tickets = json.load(f)
        if status:
            tickets = [t for t in tickets if t.get("status") == status]
        if priority:
            tickets = [t for t in tickets if t.get("priority") == priority]
        if limit:
            tickets = tickets[:int(limit)]
        return tickets
