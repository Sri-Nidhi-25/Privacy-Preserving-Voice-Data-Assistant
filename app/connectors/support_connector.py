import json
from pathlib import Path
from typing import Optional
from .base import BaseConnector


class SupportConnector(BaseConnector):
    def __init__(self, data_path: Optional[Path] = None):
        self.data_path = data_path or Path("data/support_tickets.json")

    def fetch(self, status: Optional[str] = None, priority: Optional[str] = None, limit: Optional[int] = None, **kwargs):
        try:
            with open(self.data_path) as f:
                tickets = json.load(f)
        except FileNotFoundError:
            return [] 

        if status:
            tickets = [t for t in tickets if t.get("status") == status]
        if priority:
            tickets = [t for t in tickets if t.get("priority") == priority]
        if limit:
            tickets = tickets[:int(limit)]
        return tickets
