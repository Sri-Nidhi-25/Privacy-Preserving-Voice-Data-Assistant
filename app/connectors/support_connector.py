import json
from pathlib import Path
from typing import Optional
from .base import BaseConnector

# Phrases that mean "ignore the priority filter entirely"
_NO_PRIORITY_PHRASES = {"no", "none", "no priority", "n/a", "na", "any", "all"}

_MONTH_MAP = {
    "january": "-01-", "jan": "-01-", "01": "-01-", "1": "-01-",
    "february": "-02-", "feb": "-02-", "02": "-02-", "2": "-02-",
    "march": "-03-", "mar": "-03-", "03": "-03-", "3": "-03-",
    "april": "-04-", "apr": "-04-", "04": "-04-", "4": "-04-",
    "may": "-05-", "05": "-05-", "5": "-05-",
    "june": "-06-", "jun": "-06-", "06": "-06-", "6": "-06-",
    "july": "-07-", "jul": "-07-", "07": "-07-", "7": "-07-",
    "august": "-08-", "aug": "-08-", "08": "-08-", "8": "-08-",
    "september": "-09-", "sep": "-09-", "sept": "-09-", "09": "-09-", "9": "-09-",
    "october": "-10-", "oct": "-10-", "10": "-10-",
    "november": "-11-", "nov": "-11-", "11": "-11-",
    "december": "-12-", "dec": "-12-", "12": "-12-",
}


class SupportConnector(BaseConnector):
    def __init__(self, data_path: Optional[Path] = None):
        self.data_path = data_path or Path("data/support_tickets.json")

    def fetch(
        self,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        limit: Optional[int] = None,
        month: Optional[str] = None,
        **kwargs,
    ):
        """Fetch support tickets with optional filters.

        Args:
            status:   Filter by ticket status (``"open"`` or ``"closed"``).
            priority: Filter by priority (``"low"``, ``"medium"``, ``"high"``).
                      Pass ``None`` or any phrase in _NO_PRIORITY_PHRASES to
                      skip the priority filter entirely.
            limit:    Maximum number of results to return (positive integer).
            month:    Month name or number (``"march"``, ``"03"``, ``"3"`` …).
                      Returns an empty list for unrecognised values so the
                      caller always gets a clean result rather than an error.
        """
        try:
            with open(self.data_path) as f:
                tickets = json.load(f)
        except FileNotFoundError:
            return []

        # ── Status filter ────────────────────────────────────────────────────
        if status:
            tickets = [t for t in tickets if t.get("status") == status]

        # ── Priority filter ──────────────────────────────────────────────────
        # Fuzzy priority mapping: "no priority" means "low" as per domain rules
        if priority:
            p_lower = str(priority).strip().lower()
            if p_lower in {"any", "all", "all priorities", "any priority"}:
                pass  # no filter
            elif any(w in p_lower for w in ["no", "none", "know", "without", "unassigned", "unspecified", "zero", "minimal", "low", "na", "n/a"]):
                tickets = [t for t in tickets if t.get("priority") == "low"]
            elif any(w in p_lower for w in ["med", "mid", "normal", "moderate"]):
                tickets = [t for t in tickets if t.get("priority") == "medium"]
            elif any(w in p_lower for w in ["high", "urgent", "critical", "max"]):
                tickets = [t for t in tickets if t.get("priority") == "high"]
            else:
                tickets = [t for t in tickets if t.get("priority") == priority]

        # ── Month filter ─────────────────────────────────────────────────────
        if month:
            m_lower = str(month).strip().lower()
            token = _MONTH_MAP.get(m_lower)
            if not token:
                # Accept bare numeric month strings not already in the map
                if m_lower.isdigit() and 1 <= int(m_lower) <= 12:
                    token = f"-{int(m_lower):02d}-"
                else:
                    # Unrecognised month → return empty result (no crash)
                    return []
            tickets = [t for t in tickets if token in t.get("created_at", "")]

        # ── Limit ────────────────────────────────────────────────────────────
        if limit is not None:
            try:
                lim = int(limit)
                if lim > 0:
                    tickets = tickets[:lim]
            except (ValueError, TypeError):
                pass  # ignore malformed limit, return all matching

        return tickets
