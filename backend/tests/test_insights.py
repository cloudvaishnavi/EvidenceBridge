"""
Unit and integration tests for Insights and Visual Statistics Dashboard endpoints.
Verifies aggregated decision metrics, price alert distributions, and guideline support overviews.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_get_insights_summary():
    """Verify GET /insights/summary returns structured aggregations for charts."""
    resp = client.get("/insights/summary")
    assert resp.status_code == 200
    data = resp.json()

    # Core structure
    assert "total_claims" in data
    assert "total_verified" in data
    assert "decision_overview" in data
    assert "price_alerts_overview" in data
    assert "guideline_support_overview" in data
    assert "gaps_and_risks" in data
    assert "top_procedures" in data
    assert "top_locations" in data
    assert "recent_risk_claims" in data

    # Decision Overview
    dec = data["decision_overview"]
    assert "approved" in dec
    assert "flagged" in dec
    assert "held" in dec
    assert "total" in dec
    assert dec["total"] >= 0

    # Price Alerts Overview
    pa = data["price_alerts_overview"]
    assert "normal_charges" in pa
    assert "price_alerts" in pa
    assert "moderate" in pa
    assert "severe" in pa
    assert "extreme" in pa

    # Guideline Support Overview
    gso = data["guideline_support_overview"]
    assert "supported" in gso
    assert "partially_supported" in gso
    assert "contradicted" in gso
    assert "insufficient_evidence" in gso

    # Gaps & Risks
    gnr = data["gaps_and_risks"]
    assert "insufficient_evidence_claims" in gnr
    assert "extreme_price_markups" in gnr
    assert "held_by_safety_rules" in gnr
    assert "unbenchmarked_high_cost" in gnr

    # Top Procedures and Locations lists
    assert isinstance(data["top_procedures"], list)
    assert isinstance(data["top_locations"], list)
    assert isinstance(data["recent_risk_claims"], list)
