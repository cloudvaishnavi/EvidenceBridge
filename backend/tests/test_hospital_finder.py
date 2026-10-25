"""
Unit & Integration Tests for EvidenceBridge Hospital Finder.
Validates Haversine straight-line distance calculations, emergency red-flag triggers,
non-diagnostic symptom guidance, verifiable price benchmark attachment,
attributable quality accreditation reporting, and API endpoints.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.hospital_finder import (
    HospitalFinderService,
    haversine_distance,
    hospital_finder_service,
)


@pytest.fixture
def client():
    return TestClient(app)


def test_haversine_distance_calculation():
    """Verify great-circle straight-line distance accurately calculates km and miles."""
    # Emory University Hospital (33.7925, -84.3218) to Grady Memorial Hospital (33.7533, -84.3828)
    km, miles = haversine_distance(33.7925, -84.3218, 33.7533, -84.3828)
    assert km > 5.0 and km < 8.0  # Approx 7.2 km straight-line
    assert miles > 3.0 and miles < 5.5
    assert round(km * 0.621371, 2) == miles

    # Zero distance between identical coordinates
    zero_km, zero_miles = haversine_distance(41.8781, -87.6298, 41.8781, -87.6298)
    assert zero_km == 0.0
    assert zero_miles == 0.0


def test_emergency_symptom_red_flag_alert():
    """Verify emergency red-flag symptoms trigger immediate urgent care alert."""
    service = HospitalFinderService()

    # Acute symptoms that must trigger emergency alert
    alert_chest = service.check_emergency_symptoms("I have severe chest pain and pressure")
    assert alert_chest is not None
    assert alert_chest.is_emergency is True
    assert "112 / 108" in alert_chest.emergency_phone or "911" in alert_chest.emergency_phone
    assert "Emergency Department" in alert_chest.action_advice

    alert_breath = service.check_emergency_symptoms("Sudden shortness of breath")
    assert alert_breath is not None
    assert alert_breath.is_emergency is True

    alert_bleed = service.check_emergency_symptoms("Severe bleeding from wound")
    assert alert_bleed is not None
    assert alert_bleed.is_emergency is True

    # Non-emergency routine symptom should not trigger alert
    alert_mild = service.check_emergency_symptoms("Mild headache after working")
    assert alert_mild is None


def test_non_diagnostic_symptom_guidance_and_specialty_matching():
    """Verify symptom search provides facility-finding guidance without medical diagnosing."""
    res = hospital_finder_service.search_hospitals(
        city_or_area="Atlanta",
        symptom="fever and body ache",
        max_distance_km=40.0,
    )

    assert res.symptom_filter == "fever and body ache"
    assert res.symptom_guidance is not None
    assert "informational facility-finding aid only" in res.symptom_guidance.lower()
    assert "not a clinical diagnosis" in res.symptom_guidance.lower()
    assert res.emergency_alert is None  # Fever alone is not a critical emergency alert


def test_search_hospitals_in_atlanta():
    """Verify search returns real Atlanta hospitals with coordinates, verified services, and prices."""
    res = hospital_finder_service.search_hospitals(
        city_or_area="Atlanta, GA",
        max_distance_km=30.0,
    )

    assert res.total_results >= 2
    hospital_names = [h.name for h in res.hospitals]
    assert "Emory University Hospital" in hospital_names
    assert "Grady Memorial Hospital" in hospital_names

    emory = next(h for h in res.hospitals if h.name == "Emory University Hospital")
    assert emory.city == "Atlanta"
    assert emory.state_or_region == "GA"
    assert emory.lat == 33.7925
    assert emory.lon == -84.3218
    assert emory.distance_label == "Straight-line distance"
    assert emory.distance_km is not None and emory.distance_km >= 0.0

    # Pricing integrity: verified published consultation fee and procedure benchmarks
    assert emory.price_available is True
    assert emory.consultation_fee == 185.00
    assert emory.consultation_fee_currency == "USD"
    assert emory.consultation_fee_source is not None
    assert len(emory.procedure_prices) >= 2

    # Attributable trust & accreditation
    assert "The Joint Commission (JCI Accredited)" in emory.accreditations
    assert emory.trust_score is not None and emory.trust_score > 0.8
    assert emory.trust_score_explanation is not None
    assert emory.public_rating == 4.5
    assert emory.review_count == 1840


def test_search_hospitals_in_bengaluru():
    """Verify search returns real Bengaluru hospitals with NABH/JCI accreditations and INR tariffs."""
    res = hospital_finder_service.search_hospitals(
        city_or_area="Bengaluru",
        max_distance_km=50.0,
    )

    assert res.total_results >= 2
    hospital_names = [h.name for h in res.hospitals]
    assert any("Manipal" in name for name in hospital_names)
    assert any("Narayana" in name or "Fortis" in name for name in hospital_names)

    manipal = next(h for h in res.hospitals if "Old Airport Road" in h.name or h.consultation_fee == 1000.0)
    assert manipal.consultation_fee_currency == "INR"
    assert manipal.consultation_fee == 1000.00
    assert any("NABH" in acc for acc in manipal.accreditations)
    assert manipal.phone is not None
    assert manipal.website is not None


def test_sorting_by_cost_distance_and_rating():
    """Verify sorting behaves deterministically for cost, distance, and rating."""
    # 1. Sort by cost (lowest consultation fee first)
    res_cost = hospital_finder_service.search_hospitals(city_or_area="Atlanta", sort_by="cost")
    fees = [h.consultation_fee for h in res_cost.hospitals if h.consultation_fee is not None]
    assert fees == sorted(fees)

    # 2. Sort by distance (nearest first)
    res_dist = hospital_finder_service.search_hospitals(
        lat=33.7533, lon=-84.3828, sort_by="distance"
    )
    dists = [h.distance_km for h in res_dist.hospitals if h.distance_km is not None]
    assert dists == sorted(dists)

    # 3. Sort by rating (highest trust score first)
    res_rating = hospital_finder_service.search_hospitals(city_or_area="Atlanta", sort_by="rating")
    ratings = [h.trust_score or 0.0 for h in res_rating.hospitals]
    assert ratings == sorted(ratings, reverse=True)


def test_api_search_hospitals_endpoint(client):
    """Integration test verifying GET /hospitals/search endpoint."""
    response = client.get("/hospitals/search", params={"city_or_area": "Chicago", "sort_by": "distance"})
    assert response.status_code == 200
    data = response.json()
    assert "hospitals" in data
    assert "query_city" in data
    assert data["total_results"] >= 2
    assert "disclaimer" in data
    assert any("Northwestern" in h["name"] for h in data["hospitals"])


def test_api_emergency_symptom_response(client):
    """Integration test verifying immediate red-flag response for emergency symptoms via API."""
    response = client.get(
        "/hospitals/search",
        params={"city_or_area": "Houston", "symptom": "heart attack and chest pain"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["emergency_alert"] is not None
    assert data["emergency_alert"]["is_emergency"] is True
    assert "112 / 108" in data["emergency_alert"]["emergency_phone"] or "911" in data["emergency_alert"]["emergency_phone"]


def test_ballari_search_never_returns_atlanta_hospitals(client):
    """CRITICAL TEST: Searching for Ballari must NEVER return US/Atlanta hospitals or 14,000 km distances."""
    response = client.get(
        "/hospitals/search",
        params={"city_or_area": "Ballari, Karnataka", "max_distance_km": 35.0},
    )
    assert response.status_code == 200
    data = response.json()
    assert "Ballari" in data["query_city"]
    
    # If facilities are found, every single one must be strictly within 35 km and INR currency
    for h in data["hospitals"]:
        assert h["distance_km"] <= 35.0
        assert "Atlanta" not in h["name"]
        assert "Piedmont" not in h["name"]
        assert "Emory" not in h["name"]
        assert h["consultation_fee_currency"] == "INR"


def test_invalid_location_returns_honest_empty_state(client):
    """Verify unknown location returns 0 results with helpful notice and NO fallback to Atlanta."""
    response = client.get(
        "/hospitals/search",
        params={"city_or_area": "zz_completely_unknown_fake_city_12345"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_results"] == 0
    assert len(data["hospitals"]) == 0
    assert "Unable to locate" in data["disclaimer"]

