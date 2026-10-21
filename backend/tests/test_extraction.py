"""
Unit tests for Extraction Service parsing and validation.
"""

from app.models.schemas import SentimentType
from app.services.extraction import ExtractionService


def test_parse_valid_json():
    service = ExtractionService()
    raw_llm_json = """
    {
      "entity": "Metformin 1,000 mg",
      "effect_or_outcome": "Reduction in HbA1c from 8.9% down to 7.1%",
      "cost_range": null,
      "location_city": null,
      "sentiment": "positive",
      "confidence": 0.95,
      "reasoning": "Clear clinical outcome with HbA1c metric."
    }
    """
    input_text = "Patient started Metformin 1000mg with HbA1c drop."
    fields, confidence = service._parse_and_validate_json(raw_llm_json, input_text)

    assert fields.entity == "Metformin 1,000 mg"
    assert fields.effect_or_outcome == "Reduction in HbA1c from 8.9% down to 7.1%"
    assert fields.cost_range is None
    assert fields.sentiment == SentimentType.POSITIVE
    assert confidence == 0.95


def test_parse_markdown_wrapped_json():
    service = ExtractionService()
    raw_llm_markdown = """```json
    {
      "entity": "CPT 99285 Emergency Room Visit",
      "effect_or_outcome": null,
      "cost_range": "$4,850.00",
      "location_city": "Atlanta, GA",
      "sentiment": "negative",
      "confidence": 0.88,
      "reasoning": "High-cost emergency room bill item."
    }
    ```"""
    input_text = "ER bill 99285 $4850 Atlanta GA"
    fields, confidence = service._parse_and_validate_json(raw_llm_markdown, input_text)

    assert fields.entity == "CPT 99285 Emergency Room Visit"
    assert fields.cost_range == "$4,850.00"
    assert fields.location_city == "Atlanta, GA"
    assert fields.sentiment == SentimentType.NEGATIVE
    assert confidence == 0.88


def test_heuristic_fallback_on_corrupt_json():
    service = ExtractionService()
    corrupt_output = "I couldn't generate json but the cost was $1,450 for the knee MRI procedure."
    input_text = "Knee MRI CPT 73721 billed at $1,450.00 in Chicago, IL"

    fields, confidence = service._parse_and_validate_json(corrupt_output, input_text)

    # Fallback extracts first line as entity and finds the currency pattern
    assert fields.entity is not None
    assert fields.cost_range is not None
    assert "$1,450.00" in fields.cost_range or "$1,450" in fields.cost_range
    assert confidence < 0.6  # lower confidence on fallback
