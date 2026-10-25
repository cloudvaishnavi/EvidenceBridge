"""
Integration tests for User Authentication, JWT Tokens, and User Data Isolation.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.auth import (
    DEMO_USER_ID,
    DEMO_USER_EMAIL,
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
)
from app.services.storage import storage_service


@pytest.fixture
def client():
    return TestClient(app)


def test_auth_crypto_helpers():
    """Verify bcrypt and JWT crypto operations."""
    pw = "SuperSecret123!"
    h = hash_password(pw)
    assert h != pw
    assert verify_password(pw, h) is True
    assert verify_password("wrong_password", h) is False

    token = create_access_token("usr_test123", "test@hospital.org", "Dr. Test")
    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == "usr_test123"
    assert payload["email"] == "test@hospital.org"
    assert payload["name"] == "Dr. Test"


def test_demo_auth_session(client):
    """Verify 1-click Demo Auditor sign in returns valid token and profile."""
    res = client.post("/auth/demo")
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["user_id"] == DEMO_USER_ID
    assert data["user"]["email"] == DEMO_USER_EMAIL
    assert "Vasavi" in data["user"]["name"]


def test_auth_signup_flow(client):
    """Verify account creation with duplicate detection."""
    email = "auditor.new@metrohospital.org"
    signup_payload = {
        "name": "Dr. Marcus Bell",
        "email": email,
        "password": "Password99!",
        "organization": "Metro Hospital",
    }

    # 1. Successful creation
    res1 = client.post("/auth/signup", json=signup_payload)
    assert res1.status_code == 201
    data1 = res1.json()
    assert "access_token" in data1
    assert data1["user"]["email"] == email
    assert data1["user"]["name"] == "Dr. Marcus Bell"
    new_user_id = data1["user"]["user_id"]

    # 2. Duplicate registration rejection
    res2 = client.post("/auth/signup", json=signup_payload)
    assert res2.status_code == 400
    assert "already registered" in res2.json()["detail"].lower()

    # 3. Successful login with created credentials
    res3 = client.post(
        "/auth/login",
        json={"email": email, "password": "Password99!"},
    )
    assert res3.status_code == 200
    data3 = res3.json()
    assert data3["user"]["user_id"] == new_user_id

    # 4. Failed login with incorrect password
    res4 = client.post(
        "/auth/login",
        json={"email": email, "password": "WrongPassword!"},
    )
    assert res4.status_code == 401
    assert "incorrect email or password" in res4.json()["detail"].lower()

    # 5. Access /auth/me with valid Bearer token
    res5 = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {data3['access_token']}"},
    )
    assert res5.status_code == 200
    assert res5.json()["user_id"] == new_user_id


def test_auth_me_unauthorized(client):
    """Verify /auth/me rejects missing or invalid tokens."""
    res = client.get("/auth/me")
    assert res.status_code == 401

    res_invalid = client.get("/auth/me", headers={"Authorization": "Bearer invalid_garbage_token"})
    assert res_invalid.status_code == 401


def test_user_data_isolation_claims(client):
    """Verify claims listing and insights filtering by user_id."""
    token_a = create_access_token("usr_isolated_a", "usera@health.org", "User A")
    token_b = create_access_token("usr_isolated_b", "userb@health.org", "User B")

    # User B should see 0 claims initially when filtered to user_b
    res_b_claims = client.get(
        "/claims",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert res_b_claims.status_code == 200
    data_b = res_b_claims.json()
    assert data_b["total"] == 0
    assert len(data_b["claims"]) == 0

    # User B insights should show zeroed profile without errors
    res_b_insights = client.get(
        "/insights/summary",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert res_b_insights.status_code == 200
    insights_b = res_b_insights.json()
    assert insights_b["total_claims"] == 0
    assert insights_b["is_baseline_fallback"] is False


def test_user_a_cannot_see_user_b_records(client):
    """Verify User A cannot view User B's claims or stories, even by specifying ID."""
    token_a = create_access_token("usr_alice", "alice@stjude.org", "Alice")
    token_b = create_access_token("usr_bob", "bob@stjude.org", "Bob")

    # 1. Bob creates a community story
    res_story = client.post(
        "/stories",
        json={
            "title": "Bob's Recovery Journey",
            "story_text": "This is Bob's private recovery story after knee surgery.",
            "consent_acknowledged": True,
        },
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert res_story.status_code == 201
    bob_story_id = res_story.json()["story_id"]

    # Alice lists stories -> Bob's story must NOT appear in Alice's list
    res_alice_stories = client.get(
        "/stories",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert res_alice_stories.status_code == 200
    alice_story_ids = [s["story_id"] for s in res_alice_stories.json()["stories"]]
    assert bob_story_id not in alice_story_ids

    # Alice tries to directly query Bob's story by ID -> Rejected with 404
    res_alice_get_bob = client.get(
        f"/stories/{bob_story_id}",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert res_alice_get_bob.status_code == 404

    # Alice tries to bypass isolation with query param ?user_id=usr_bob -> 403 Forbidden
    res_spoof = client.get(
        "/stories?user_id=usr_bob",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert res_spoof.status_code == 403
    assert "access denied" in res_spoof.json()["detail"].lower()


def test_protected_routes_reject_unauthenticated_requests(client):
    """Verify all sensitive endpoints reject unauthenticated requests with 401."""
    protected_endpoints = [
        ("GET", "/claims"),
        ("GET", "/claims/clm_any"),
        ("POST", "/extract"),
        ("POST", "/extract-and-verify"),
        ("POST", "/verify/clm_any"),
        ("GET", "/verification/clm_any"),
        ("GET", "/audit/clm_any"),
        ("GET", "/audit/verification/ver_any"),
        ("GET", "/stories"),
        ("POST", "/stories"),
        ("GET", "/stories/story_any"),
        ("GET", "/evaluate"),
        ("POST", "/evaluate"),
        ("GET", "/evaluate/eval_any"),
        ("GET", "/insights/summary"),
        ("GET", "/auth/me"),
    ]

    for method, endpoint in protected_endpoints:
        if method == "GET":
            res = client.get(endpoint)
        else:
            res = client.post(endpoint, json={"text": "test", "title": "test", "story_text": "sample text"})
        assert res.status_code == 401, f"{method} {endpoint} should return 401 Unauthorized when unauthenticated"


def test_demo_account_cannot_access_private_user_data(client):
    """Verify Demo Auditor cannot access real user's private data."""
    token_real = create_access_token("usr_real_auditor", "real@hospital.org", "Dr. Real")
    token_demo = client.post("/auth/demo").json()["access_token"]

    # Real user creates a story
    res_real_story = client.post(
        "/stories",
        json={
            "title": "Confidential Case Study",
            "story_text": "Real patient recovery confidential case study notes.",
            "consent_acknowledged": True,
        },
        headers={"Authorization": f"Bearer {token_real}"},
    )
    assert res_real_story.status_code == 201
    real_story_id = res_real_story.json()["story_id"]

    # Demo Auditor lists stories -> Real user's story must NOT be included
    res_demo_stories = client.get(
        "/stories",
        headers={"Authorization": f"Bearer {token_demo}"},
    )
    assert res_demo_stories.status_code == 200
    demo_story_ids = [s["story_id"] for s in res_demo_stories.json()["stories"]]
    assert real_story_id not in demo_story_ids

    # Demo Auditor directly requests real user's story -> 404
    res_demo_get_real = client.get(
        f"/stories/{real_story_id}",
        headers={"Authorization": f"Bearer {token_demo}"},
    )
    assert res_demo_get_real.status_code == 404


def test_jwt_secret_from_env(monkeypatch):
    """Verify JWT secret is dynamically read from environment variable."""
    import os
    from app.services.auth import get_auth_secret_key, create_access_token, decode_access_token

    custom_secret = "my_custom_super_secure_env_jwt_secret_2026_test"
    monkeypatch.setenv("AUTH_SECRET_KEY", custom_secret)

    assert get_auth_secret_key() == custom_secret

    token = create_access_token("usr_env_test", "env@test.org", "Env Tester")
    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == "usr_env_test"
