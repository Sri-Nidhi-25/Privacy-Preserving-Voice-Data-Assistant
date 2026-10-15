"""
tests/test_connectors.py - Tests for CRM, Support, and Analytics connectors.
"""
from pathlib import Path
from app.connectors.crm_connector import CRMConnector
from app.connectors.support_connector import SupportConnector
from app.connectors.analytics_connector import AnalyticsConnector


def test_crm_connector_fetch():
    crm = CRMConnector()
    results = crm.fetch(status="active", limit=3)
    assert isinstance(results, list)
    assert len(results) <= 3
    for r in results:
        assert r.get("status") == "active"


def test_support_connector_fetch():
    support = SupportConnector()
    results = support.fetch(status="open", priority="high")
    assert isinstance(results, list)
    for r in results:
        assert r.get("status") == "open"
        assert r.get("priority") == "high"


def test_analytics_connector_fetch():
    analytics = AnalyticsConnector()
    results = analytics.fetch(metric="daily_active_users", days=2)
    assert isinstance(results, list)
    assert len(results) <= 2


def test_connector_result_abstraction():
    crm = CRMConnector()
    res = crm.fetch_result(status="active", limit=2)
    assert res.success is True
    assert res.error is None
    assert isinstance(res.data, list)
    assert res.retrieved_at != ""
    assert res.connector_name == "CRMConnector"


def test_connector_missing_data_file(tmp_path: Path):
    non_existent = tmp_path / "missing.json"
    crm = CRMConnector(data_path=non_existent)
    data = crm.fetch()
    assert data == []

    res = crm.fetch_result()
    assert res.success is True
    assert res.is_empty is True


# ── New tests for month filter, no-priority, and zero-result behaviour ────────

def test_support_month_filter_march():
    """All returned tickets must have a March created_at."""
    support = SupportConnector()
    results = support.fetch(month="march")
    assert isinstance(results, list)
    assert len(results) > 0, "Expected March tickets in the dataset"
    for t in results:
        assert "-03-" in t["created_at"], f"Unexpected date: {t['created_at']}"


def test_support_month_filter_numeric():
    """Numeric month '3' should behave identically to 'march'."""
    support = SupportConnector()
    by_name = support.fetch(month="march")
    by_num = support.fetch(month="3")
    assert by_name == by_num


def test_support_month_filter_zero_results():
    """A month with no tickets returns an empty list, not an error."""
    support = SupportConnector()
    results = support.fetch(month="june")  # dataset has no June tickets
    assert results == []


def test_support_month_filter_invalid_returns_empty():
    """An unrecognised month token returns [] instead of raising."""
    support = SupportConnector()
    results = support.fetch(month="notamonth")
    assert results == []


def test_support_month_and_status_combined():
    """Combining month + status filter must respect both constraints."""
    support = SupportConnector()
    results = support.fetch(month="march", status="closed")
    assert isinstance(results, list)
    for t in results:
        assert "-03-" in t["created_at"]
        assert t["status"] == "closed"


def test_support_month_and_priority_combined():
    """Combining month + priority filter must respect both constraints."""
    support = SupportConnector()
    results = support.fetch(month="march", priority="low")
    assert isinstance(results, list)
    for t in results:
        assert "-03-" in t["created_at"]
        assert t["priority"] == "low"


def test_support_no_priority_phrase_means_low():
    """Passing 'no priority' (acoustic confusion for 'low priority') maps to low priority."""
    support = SupportConnector()
    low_tickets = support.fetch(status="closed", priority="low")
    no_prio_tickets = support.fetch(status="closed", priority="no priority")
    assert no_prio_tickets == low_tickets


def test_support_no_priority_variants():
    """Recognised 'no priority' synonyms map to low priority, while 'any' drops filter."""
    support = SupportConnector()
    reference_low = support.fetch(priority="low")
    for phrase in ["none", "no", "n/a", "na", "no priority", "without priority", "low priority"]:
        result = support.fetch(priority=phrase)
        assert result == reference_low, f"Phrase '{phrase}' did not map to low priority"
    
    # "any" drops the filter
    all_tickets = support.fetch()
    assert support.fetch(priority="any") == all_tickets


def test_support_limit_applied():
    """limit=3 must return at most 3 records."""
    support = SupportConnector()
    results = support.fetch(limit=3)
    assert len(results) <= 3


def test_support_limit_zero_ignored():
    """limit=0 is treated as 'no limit' and returns all tickets."""
    support = SupportConnector()
    all_tickets = support.fetch()
    limited = support.fetch(limit=0)
    assert limited == all_tickets


def test_support_missing_file_returns_empty(tmp_path: Path):
    """Missing data file returns [] instead of raising."""
    support = SupportConnector(data_path=tmp_path / "nonexistent.json")
    assert support.fetch() == []

