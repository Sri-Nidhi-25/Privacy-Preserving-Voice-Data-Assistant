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
