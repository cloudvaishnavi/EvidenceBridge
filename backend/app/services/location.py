"""
Location Extraction and Normalization Service for EvidenceBridge.
Identifies city/state/region mentions in clinical notes, hospital bills, and patient reports,
normalizing them into canonical keys (e.g., 'atlanta_ga', 'chicago_il') for hyperlocal aggregation.
"""

from __future__ import annotations

import logging
import re
from typing import Optional

from app.models.schemas import LocationInfo

logger = logging.getLogger(__name__)

# Standard US 50 States + DC Mapping (lowercase full name -> 2-letter uppercase postal code)
US_STATES: dict[str, str] = {
    "alabama": "AL",
    "alaska": "AK",
    "arizona": "AZ",
    "arkansas": "AR",
    "california": "CA",
    "colorado": "CO",
    "connecticut": "CT",
    "delaware": "DE",
    "florida": "FL",
    "georgia": "GA",
    "hawaii": "HI",
    "idaho": "ID",
    "illinois": "IL",
    "indiana": "IN",
    "iowa": "IA",
    "kansas": "KS",
    "kentucky": "KY",
    "louisiana": "LA",
    "maine": "ME",
    "maryland": "MD",
    "massachusetts": "MA",
    "michigan": "MI",
    "minnesota": "MN",
    "mississippi": "MS",
    "missouri": "MO",
    "montana": "MT",
    "nebraska": "NE",
    "nevada": "NV",
    "new hampshire": "NH",
    "new jersey": "NJ",
    "new mexico": "NM",
    "new york": "NY",
    "north carolina": "NC",
    "north dakota": "ND",
    "ohio": "OH",
    "oklahoma": "OK",
    "oregon": "OR",
    "pennsylvania": "PA",
    "rhode island": "RI",
    "south carolina": "SC",
    "south dakota": "SD",
    "tennessee": "TN",
    "texas": "TX",
    "utah": "UT",
    "vermont": "VT",
    "virginia": "VA",
    "washington": "WA",
    "west virginia": "WV",
    "wisconsin": "WI",
    "wyoming": "WY",
    "district of columbia": "DC",
}

# Reverse lookup set of valid 2-letter postal abbreviations
US_STATE_CODES = set(US_STATES.values())

# Prominent Indian States & Union Territories
INDIAN_STATES: dict[str, str] = {
    "karnataka": "KA",
    "maharashtra": "MH",
    "tamil nadu": "TN",
    "telangana": "TG",
    "andhra pradesh": "AP",
    "kerala": "KL",
    "delhi": "DL",
    "gujarat": "GJ",
    "rajasthan": "RJ",
    "west bengal": "WB",
    "uttar pradesh": "UP",
    "goa": "GA",
    "punjab": "PB",
    "haryana": "HR",
    "bihar": "BR",
    "madhya pradesh": "MP",
    "odisha": "OD",
}
INDIAN_STATE_CODES = set(INDIAN_STATES.values())

# Prominent Indian Metros & Karnataka Hubs
PROMINENT_INDIAN_CITIES: dict[str, str] = {
    "bengaluru": "KA",
    "bangalore": "KA",
    "ballari": "KA",
    "bellary": "KA",
    "mysuru": "KA",
    "mysore": "KA",
    "davangere": "KA",
    "davanagere": "KA",
    "hubballi": "KA",
    "hubli": "KA",
    "dharwad": "KA",
    "hubli_dharwad": "KA",
    "hubballi_dharwad": "KA",
    "hubli-dharwad": "KA",
    "hubballi-dharwad": "KA",
    "mangaluru": "KA",
    "mangalore": "KA",
    "belagavi": "KA",
    "belgaum": "KA",
    "kalaburagi": "KA",
    "gulbarga": "KA",
    "shivamogga": "KA",
    "shimoga": "KA",
    "tumakuru": "KA",
    "tumkur": "KA",
    "mumbai": "MH",
    "pune": "MH",
    "chennai": "TN",
    "hyderabad": "TG",
    "delhi": "DL",
    "new delhi": "DL",
    "kolkata": "WB",
}

# Prominent US Metros / Cities with default states when only city is mentioned
PROMINENT_CITIES: dict[str, str] = {
    "atlanta": "GA",
    "austin": "TX",
    "boston": "MA",
    "charlotte": "NC",
    "chicago": "IL",
    "cleveland": "OH",
    "dallas": "TX",
    "denver": "CO",
    "detroit": "MI",
    "houston": "TX",
    "los angeles": "CA",
    "miami": "FL",
    "minneapolis": "MN",
    "nashville": "TN",
    "new york": "NY",
    "new york city": "NY",
    "philadelphia": "PA",
    "phoenix": "AZ",
    "pittsburgh": "PA",
    "portland": "OR",
    "sacramento": "CA",
    "san antonio": "TX",
    "san diego": "CA",
    "san francisco": "CA",
    "seattle": "WA",
    "st. louis": "MO",
    "st louis": "MO",
    "tampa": "FL",
}


def normalize_location_key(city: str, state_or_region: Optional[str] = None) -> str:
    """
    Produce a canonical, lowercase snake_case location key.
    Examples:
        - normalize_location_key("Bengaluru", "Karnataka") -> "bengaluru_ka"
        - normalize_location_key("Ballari", "KA") -> "ballari_ka"
        - normalize_location_key("Davangere", None) -> "davangere_ka" (via PROMINENT_INDIAN_CITIES)
        - normalize_location_key("Houston", "TX") -> "houston_tx"
    """
    if not city:
        return ""

    # If city contains a comma like "Bengaluru, Karnataka" or "Atlanta, GA", split it
    if "," in city and not state_or_region:
        parts = city.split(",", 1)
        city = parts[0].strip()
        state_or_region = parts[1].strip()

    city_clean = re.sub(r"[^\w\s]", "", city).strip().lower()
    city_slug = re.sub(r"\s+", "_", city_clean)

    # Normalize state code
    state_code: Optional[str] = None
    if state_or_region:
        st_clean = re.sub(r"[^\w\s]", "", state_or_region).strip().lower()
        if st_clean.upper() in INDIAN_STATE_CODES:
            state_code = st_clean.lower()
        elif st_clean in INDIAN_STATES:
            state_code = INDIAN_STATES[st_clean].lower()
        elif st_clean.upper() in US_STATE_CODES:
            state_code = st_clean.lower()
        elif st_clean in US_STATES:
            state_code = US_STATES[st_clean].lower()
        else:
            state_code = re.sub(r"\s+", "_", st_clean)

    # Fallback to known Indian city mapping if state not provided
    if not state_code and city_clean in PROMINENT_INDIAN_CITIES:
        state_code = PROMINENT_INDIAN_CITIES[city_clean].lower()
    # Fallback to known US city mapping if state not provided
    elif not state_code and city_clean in PROMINENT_CITIES:
        state_code = PROMINENT_CITIES[city_clean].lower()

    if state_code:
        return f"{city_slug}_{state_code}"
    return city_slug


class LocationService:
    """Service responsible for extracting and resolving LocationInfo from text & extracted fields."""

    def __init__(self) -> None:
        # Regex patterns for matching common geographic mentions in healthcare notes
        # Pattern 1: "City, ST" (e.g. "Atlanta, GA", "Houston, TX", "Los Angeles, CA")
        self._pattern_city_state_code = re.compile(
            r"\b([A-Z][a-zA-Z\.]+(?:\s+[A-Z][a-zA-Z\.]+)*),\s*([A-Z]{2})\b"
        )
        # Pattern 2: "City, StateName" (e.g. "Chicago, Illinois")
        state_names_regex = "|".join(re.escape(k) for k in US_STATES.keys())
        self._pattern_city_full_state = re.compile(
            rf"\b([A-Z][a-zA-Z\.]+(?:\s+[A-Z][a-zA-Z\.]+)*),\s*({state_names_regex})\b",
            re.IGNORECASE,
        )
        # Pattern 3: "in City" or "at Hospital in City" (e.g. "in Houston", "in Chicago")
        prominent_names_regex = "|".join(re.escape(k.title()) for k in PROMINENT_CITIES.keys())
        self._pattern_prominent_city = re.compile(
            rf"\b(?:in|at|near|hospital\s+in)\s+({prominent_names_regex})\b",
            re.IGNORECASE,
        )

    def parse_location_string(self, raw_str: str) -> Optional[LocationInfo]:
        """Parse a standalone location or hospital facility string into LocationInfo."""
        if not raw_str or not raw_str.strip():
            return None

        clean_str = raw_str.strip()

        # Check for "City, ST" pattern
        m_code = self._pattern_city_state_code.search(clean_str)
        if m_code:
            city_part = m_code.group(1).strip()
            state_part = m_code.group(2).strip().upper()
            if state_part in US_STATE_CODES:
                key = normalize_location_key(city_part, state_part)
                return LocationInfo(
                    city=city_part,
                    state_or_region=state_part,
                    country="US",
                    normalized_key=key,
                    raw_mention=clean_str,
                )

        # Check for "City, StateName" pattern
        m_full = self._pattern_city_full_state.search(clean_str)
        if m_full:
            city_part = m_full.group(1).strip()
            state_name = m_full.group(2).strip().lower()
            state_part = US_STATES.get(state_name, state_name.upper())
            key = normalize_location_key(city_part, state_part)
            return LocationInfo(
                city=city_part,
                state_or_region=state_part,
                country="US",
                normalized_key=key,
                raw_mention=clean_str,
            )

        # Check for Indian prominent city mention
        for city_name, st_code in PROMINENT_INDIAN_CITIES.items():
            if re.search(rf"\b{re.escape(city_name)}\b", clean_str, re.IGNORECASE):
                formatted_city = city_name.replace("_", " ").replace("-", " ").title()
                key = normalize_location_key(city_name, st_code)
                return LocationInfo(
                    city=formatted_city,
                    state_or_region=st_code,
                    country="IN",
                    normalized_key=key,
                    raw_mention=clean_str,
                )

        # Check for known prominent city mention
        for city_name, st_code in PROMINENT_CITIES.items():
            if re.search(rf"\b{re.escape(city_name)}\b", clean_str, re.IGNORECASE):
                key = normalize_location_key(city_name.title(), st_code)
                return LocationInfo(
                    city=city_name.title(),
                    state_or_region=st_code,
                    country="US",
                    normalized_key=key,
                    raw_mention=clean_str,
                )

        return None

    def extract_location(
        self,
        text: str,
        location_field: Optional[str] = None,
    ) -> Optional[LocationInfo]:
        """
        Extract and normalize location from text and/or pre-extracted fields.
        Returns None gracefully if no recognizable locality is found.
        """
        # Step 1: Check pre-extracted field from LLM/NER if available
        if location_field and location_field.strip():
            parsed = self.parse_location_string(location_field)
            if parsed:
                return parsed

        # Step 2: Search text for explicit "City, ST" pattern
        if not text or not text.strip():
            return None

        m_code = self._pattern_city_state_code.search(text)
        if m_code:
            city_part = m_code.group(1).strip()
            state_part = m_code.group(2).strip().upper()
            if state_part in US_STATE_CODES:
                # Discard common non-city words that match capitalized pattern
                if not any(stop in city_part.lower() for stop in ["patient", "doctor", "hospital", "clinic", "department", "unit", "floor"]):
                    key = normalize_location_key(city_part, state_part)
                    return LocationInfo(
                        city=city_part,
                        state_or_region=state_part,
                        country="US",
                        normalized_key=key,
                        raw_mention=m_code.group(0),
                    )

        # Step 3: Search text for "City, StateName" pattern
        m_full = self._pattern_city_full_state.search(text)
        if m_full:
            city_part = m_full.group(1).strip()
            state_name = m_full.group(2).strip().lower()
            state_part = US_STATES.get(state_name, state_name.upper())
            # Discard if city_part contains stop words (means regex captured a phrase, not a city name)
            stop_words = {"patient", "doctor", "hospital", "clinic", "department", "unit",
                          "floor", "from", "in", "at", "near", "referred", "treated"}
            city_words = set(city_part.lower().split())
            if city_words & stop_words:
                # Try to salvage: look for last title-cased word before the comma
                candidate = city_part.split()[-1].rstrip(".,")
                if candidate[0].isupper() and len(candidate) > 2:
                    city_part = candidate
                else:
                    city_part = None
            if city_part:
                key = normalize_location_key(city_part, state_part)
                return LocationInfo(
                    city=city_part,
                    state_or_region=state_part,
                    country="US",
                    normalized_key=key,
                    raw_mention=m_full.group(0),
                )

        # Step 4: Search text for prominent Indian cities
        for city_name, st_code in PROMINENT_INDIAN_CITIES.items():
            if re.search(rf"\b{re.escape(city_name)}\b", text, re.IGNORECASE):
                formatted_city = city_name.replace("_", " ").replace("-", " ").title()
                key = normalize_location_key(city_name, st_code)
                return LocationInfo(
                    city=formatted_city,
                    state_or_region=st_code,
                    country="IN",
                    normalized_key=key,
                    raw_mention=city_name,
                )

        # Step 5: Search text for prominent US cities preceded by prepositions
        m_prom = self._pattern_prominent_city.search(text)
        if m_prom:
            city_match = m_prom.group(1).strip().lower()
            st_code = PROMINENT_CITIES.get(city_match, "")
            key = normalize_location_key(city_match.title(), st_code)
            return LocationInfo(
                city=city_match.title(),
                state_or_region=st_code if st_code else None,
                country="US",
                normalized_key=key,
                raw_mention=m_prom.group(0),
            )

        return None


# Global singleton instance
location_service = LocationService()
