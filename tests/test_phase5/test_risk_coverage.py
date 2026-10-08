"""Unit tests for Risk-Coverage metrics and calibration logic."""

import pytest
from evaluation.phase5.risk_coverage import evaluate_selective_metrics, compute_risk_coverage_curve


def test_perfect_predictions():
    evals = [
        {"confidence": 0.9, "decision": "EXECUTE", "expected_route": "tool", "expected_tool": "get_crm_data", "actual_tool": "get_crm_data"},
        {"confidence": 0.8, "decision": "EXECUTE", "expected_route": "tool", "expected_tool": "get_crm_data", "actual_tool": "get_crm_data"},
    ]
    # At tau = 0.5, both executed correctly
    m_50 = evaluate_selective_metrics(evals, threshold=0.5)
    assert m_50["coverage"] == 1.0
    assert m_50["risk"] == 0.0
    assert m_50["selective_accuracy"] == 1.0

    # At tau = 0.85, only 1 executed
    m_85 = evaluate_selective_metrics(evals, threshold=0.85)
    assert m_85["coverage"] == 0.5
    assert m_85["risk"] == 0.0

    # At tau = 0.95, none executed
    m_95 = evaluate_selective_metrics(evals, threshold=0.95)
    assert m_95["coverage"] == 0.0
    assert m_95["risk"] == 0.0


def test_coverage_monotonicity():
    """Higher threshold must never increase coverage."""
    evals = [
        {"confidence": 0.2, "decision": "EXECUTE", "expected_route": "direct", "expected_tool": None, "actual_tool": "get_crm_data"},
        {"confidence": 0.5, "decision": "EXECUTE", "expected_route": "tool", "expected_tool": "get_crm_data", "actual_tool": "get_crm_data"},
        {"confidence": 0.7, "decision": "EXECUTE", "expected_route": "tool", "expected_tool": "get_crm_data", "actual_tool": "get_crm_data"},
        {"confidence": 0.9, "decision": "EXECUTE", "expected_route": "tool", "expected_tool": "get_crm_data", "actual_tool": "get_crm_data"},
    ]
    thresholds = [0.1, 0.3, 0.5, 0.6, 0.8, 0.95]
    curve = compute_risk_coverage_curve(evals, thresholds)

    prev_cov = 1.0
    for p in curve["points"]:
        assert p["coverage"] <= prev_cov, f"Coverage increased at tau={p['threshold']}"
        prev_cov = p["coverage"]


def test_aurc_calculation():
    evals = [
        {"confidence": 0.8, "decision": "EXECUTE", "expected_route": "tool", "expected_tool": "get_crm_data", "actual_tool": "get_crm_data"},
        {"confidence": 0.6, "decision": "EXECUTE", "expected_route": "direct", "expected_tool": None, "actual_tool": "get_crm_data"},
    ]
    curve = compute_risk_coverage_curve(evals)
    assert curve["aurc"] >= 0.0
    assert len(curve["points"]) == 9
