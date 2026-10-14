import json
from pathlib import Path
from typing import Optional
from .base import BaseConnector


class SupportConnector(BaseConnector):
    def __init__(self, data_path: Optional[Path] = None):
        self.data_path = data_path or Path("data/support_tickets.json")

    def fetch(self, status: Optional[str] = None, priority: Optional[str] = None, limit: Optional[int] = None, month: Optional[str] = None, **kwargs):
        try:
            with open(self.data_path) as f:
                tickets = json.load(f)
        except FileNotFoundError:
            return [] 

        if status:
            tickets = [t for t in tickets if t.get("status") == status]
        if priority:
            tickets = [t for t in tickets if t.get("priority") == priority]
        if month:
            # Match month by name (e.g. 'march', '03') or prefix
            m_lower = str(month).strip().lower()
            month_map = {
                "january": "-01", "jan": "-01", "01": "-01", "1": "-01",
                "february": "-02", "feb": "-02", "02": "-02", "2": "-02",
                "march": "-03", "mar": "-03", "03": "-03", "3": "-03",
                "april": "-04", "apr": "-04", "04": "-04", "4": "-04",
                "may": "-05", "05": "-05", "5": "-05",
                "june": "-06", "jun": "-06", "06": "-06", "6": "-06",
                "july": "-07", "jul": "-07", "07": "-07", "7": "-07",
                "august": "-08", "aug": "-08", "08": "-08", "8": "-08",
                "september": "-09", "sep": "-09", "sept": "-09", "09": "-09", "9": "-09",
                "october": "-10", "oct": "-10", "10": "-10",
                "november": "-11", "nov": "-11", "11": "-11",
                "december": "-12", "dec": "-12", "12": "-12",
            }
            token = month_map.get(m_lower, f"-{m_lower.zfill(2)}")
            tickets = [t for t in tickets if token in t.get("created_at", "")]
        if limit is not None:
            tickets = tickets[:int(limit)]
        return tickets
