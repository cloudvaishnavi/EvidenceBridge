"""
Unit and integration tests for Community Stories (Recovery Stories) endpoints.
Verifies listing, creating, retrieving, and validation of voluntary community stories.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.auth import (
    create_access_token,
    DEMO_USER_ID,
    DEMO_USER_EMAIL,
    DEMO_USER_NAME,
)

client = TestClient(app)
demo_token = create_access_token(DEMO_USER_ID, DEMO_USER_EMAIL, DEMO_USER_NAME)
client.headers["Authorization"] = f"Bearer {demo_token}"


def test_list_community_stories():
    """Verify GET /stories returns list and total count."""
    resp = client.get("/stories")
    assert resp.status_code == 200
    data = resp.json()
    assert "stories" in data
    assert "total" in data
    assert "count" in data
    assert data["total"] >= 1
    assert len(data["stories"]) >= 1

    first = data["stories"][0]
    assert "story_id" in first
    assert "story_text" in first
    assert "author_name" in first


def test_create_and_get_community_story():
    """Verify POST /stories creates a new story and GET /stories/{id} retrieves it."""
    payload = {
        "title": "My Path to Living Well with Asthma",
        "story_text": "After several ER visits in my twenties, I learned how to track triggers and communicate clearly with my care team. Peak flow monitoring gave me my confidence back.",
        "author_name": "Marcus L.",
        "condition_or_topic": "Adult Asthma",
        "contact_email": "marcus.recovery@community.org",
        "contact_instagram": "@marcus_breathes",
        "consent_acknowledged": True,
    }

    create_resp = client.post("/stories", json=payload)
    assert create_resp.status_code == 201
    created = create_resp.json()
    assert created["story_id"].startswith("story_")
    assert created["title"] == payload["title"]
    assert created["author_name"] == payload["author_name"]
    assert created["contact_instagram"] == "marcus_breathes"  # stripped @
    assert created["contact_email"] == payload["contact_email"]

    story_id = created["story_id"]

    # Retrieve single story
    get_resp = client.get(f"/stories/{story_id}")
    assert get_resp.status_code == 200
    retrieved = get_resp.json()
    assert retrieved["story_id"] == story_id
    assert retrieved["story_text"] == payload["story_text"]


def test_create_story_validation_error():
    """Verify that posting a story with empty text returns 422."""
    payload = {
        "title": "Short invalid",
        "story_text": "too short",  # less than 10 characters
    }
    resp = client.post("/stories", json=payload)
    assert resp.status_code == 422


def test_get_nonexistent_story():
    """Verify GET /stories/{nonexistent} returns 404."""
    resp = client.get("/stories/story_nonexistent_999999")
    assert resp.status_code == 404
