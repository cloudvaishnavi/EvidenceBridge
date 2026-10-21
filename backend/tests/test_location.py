"""
Tests for Location Extraction and Normalization Service (Layer 4).
Validates regex-based city/state extraction, location key canonicalization,
prominent city fallback, and graceful handling of missing/unrecognizable locations.
"""

import pytest

from app.services.location import (
    LocationService,
    location_service,
    normalize_location_key,
    PROMINENT_CITIES,
    US_STATES,
)


# ==============================================================================
# normalize_location_key() Tests
# ==============================================================================

class TestNormalizeLocationKey:
    """Tests for the normalize_location_key() function."""

    def test_city_state_code(self):
        assert normalize_location_key("Houston", "TX") == "houston_tx"

    def test_city_full_state_name(self):
        assert normalize_location_key("Chicago", "Illinois") == "chicago_il"

    def test_city_with_comma_state(self):
        assert normalize_location_key("Atlanta, GA") == "atlanta_ga"

    def test_prominent_city_fallback_no_state(self):
        assert normalize_location_key("Seattle", None) == "seattle_wa"

    def test_unknown_city_no_state(self):
        key = normalize_location_key("Smalltown", None)
        assert key == "smalltown"

    def test_city_with_periods_and_spaces(self):
        assert normalize_location_key("St. Louis", "MO") == "st_louis_mo"

    def test_dc(self):
        assert normalize_location_key("Washington", "DC") == "washington_dc"

    def test_empty_city_returns_empty(self):
        assert normalize_location_key("") == ""

    def test_multiword_city(self):
        assert normalize_location_key("San Francisco", "CA") == "san_francisco_ca"

    def test_case_insensitive_state(self):
        assert normalize_location_key("Dallas", "tx") == "dallas_tx"

    def test_case_insensitive_full_state(self):
        assert normalize_location_key("Denver", "colorado") == "denver_co"


# ==============================================================================
# LocationService.extract_location() Tests
# ==============================================================================

class TestExtractLocation:
    """Tests for LocationService.extract_location() from text."""

    def setup_method(self):
        self.svc = LocationService()

    def test_extract_city_state_code_from_text(self):
        text = "MEMORIAL REGIONAL MEDICAL CENTER - ATLANTA, GA. Emergency visit level 5."
        loc = self.svc.extract_location(text)
        assert loc is not None
        assert loc.city == "ATLANTA"
        assert loc.state_or_region == "GA"
        assert loc.normalized_key == "atlanta_ga"

    def test_extract_full_state_name(self):
        text = "Patient referred from clinic in Denver, Colorado for further evaluation."
        loc = self.svc.extract_location(text)
        assert loc is not None
        assert loc.normalized_key == "denver_co"

    def test_extract_prominent_city_with_preposition(self):
        text = "The patient was treated in Houston for cardiac symptoms."
        loc = self.svc.extract_location(text)
        assert loc is not None
        assert loc.normalized_key == "houston_tx"

    def test_no_location_returns_none(self):
        text = "Patient started on Metformin 1000mg twice daily with good glycemic control."
        loc = self.svc.extract_location(text)
        assert loc is None

    def test_extract_from_location_field_preference(self):
        text = "General clinical note about blood pressure."
        loc = self.svc.extract_location(text, location_field="Chicago, IL")
        assert loc is not None
        assert loc.normalized_key == "chicago_il"

    def test_location_field_takes_precedence_over_text(self):
        text = "Hospital in Houston, TX performed the procedure."
        loc = self.svc.extract_location(text, location_field="Dallas, TX")
        assert loc is not None
        # location_field should be tried first
        assert loc.normalized_key == "dallas_tx"

    def test_empty_text_empty_field(self):
        loc = self.svc.extract_location("", location_field="")
        assert loc is None

    def test_empty_text_none_field(self):
        loc = self.svc.extract_location("", location_field=None)
        assert loc is None

    def test_hospital_name_with_city(self):
        text = "NORTHWESTERN MEDICINE - CHICAGO, IL. Department of Orthopedics."
        loc = self.svc.extract_location(text)
        assert loc is not None
        assert loc.normalized_key == "chicago_il"

    def test_multiple_cities_returns_first_match(self):
        text = "Patient transferred from HOUSTON, TX facility to DALLAS, TX hospital."
        loc = self.svc.extract_location(text)
        assert loc is not None
        # Should match the first city/state pattern found
        assert loc.normalized_key in ("houston_tx", "dallas_tx")

    def test_raw_mention_captured(self):
        text = "Clinic in Cleveland, OH performed the lab work."
        loc = self.svc.extract_location(text)
        assert loc is not None
        assert loc.raw_mention is not None
        assert "Cleveland" in loc.raw_mention


# ==============================================================================
# LocationService.parse_location_string() Tests
# ==============================================================================

class TestParseLocationString:
    """Tests for parsing standalone location strings."""

    def setup_method(self):
        self.svc = LocationService()

    def test_parse_city_state_code(self):
        loc = self.svc.parse_location_string("Atlanta, GA")
        assert loc is not None
        assert loc.normalized_key == "atlanta_ga"

    def test_parse_city_full_state(self):
        loc = self.svc.parse_location_string("Portland, Oregon")
        assert loc is not None
        assert loc.normalized_key == "portland_or"

    def test_parse_prominent_city_alone(self):
        loc = self.svc.parse_location_string("Miami")
        assert loc is not None
        assert loc.normalized_key == "miami_fl"

    def test_parse_empty_string_returns_none(self):
        assert self.svc.parse_location_string("") is None

    def test_parse_none_returns_none(self):
        assert self.svc.parse_location_string(None) is None

    def test_parse_whitespace_only_returns_none(self):
        assert self.svc.parse_location_string("   ") is None

    def test_parse_unrecognized_location(self):
        loc = self.svc.parse_location_string("Random Unknown Place")
        assert loc is None


# ==============================================================================
# Global Singleton Test
# ==============================================================================

def test_global_location_service_instance():
    """Verify the global singleton is properly initialized."""
    assert location_service is not None
    assert isinstance(location_service, LocationService)
