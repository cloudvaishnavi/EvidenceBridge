"""
Tests for Production CORS Configuration and Origin Whitelisting.
Verifies that:
1. Allowed frontend origins (e.g. http://localhost:5173, custom production domains) are granted CORS headers.
2. Unapproved origins do not receive Access-Control-Allow-Origin headers.
3. Credentialed requests (Authorization Bearer / cookies) succeed with explicit allowed origins.
4. Settings parse ALLOWED_ORIGINS correctly in development vs production modes.
"""

import os
import pytest
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.main import app


def test_cors_settings_parsing_development():
    """Verify default development configuration includes localhost and 127.0.0.1 origins."""
    s = Settings(APP_ENV="development", ALLOWED_ORIGINS="http://localhost:5173")
    origins = s.cors_allowed_origins
    assert "http://localhost:5173" in origins
    assert "http://127.0.0.1:5173" in origins
    assert "http://localhost:3000" in origins
    assert "*" not in origins


def test_cors_settings_parsing_production():
    """Verify production mode allows only explicitly configured origins and excludes wildcard."""
    s = Settings(
        APP_ENV="production",
        ALLOWED_ORIGINS="https://evidencebridge.org, https://app.evidencebridge.org/, *",
    )
    origins = s.cors_allowed_origins
    assert "https://evidencebridge.org" in origins
    assert "https://app.evidencebridge.org" in origins  # Stripped trailing slash
    assert "*" not in origins
    # Dev localhost should not be automatically injected in production
    assert "http://localhost:5173" not in origins


def test_cors_allowed_origin_preflight():
    """Verify preflight OPTIONS request from an allowed origin returns 200 with credentials header."""
    client = TestClient(app)
    res = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization, content-type",
        },
    )
    assert res.status_code == 200
    assert res.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert res.headers.get("access-control-allow-credentials") == "true"
    assert "GET" in res.headers.get("access-control-allow-methods", "")


def test_cors_unapproved_origin_preflight_rejected():
    """Verify preflight OPTIONS request from an unapproved origin is rejected without allow-origin."""
    client = TestClient(app)
    res = client.options(
        "/health",
        headers={
            "Origin": "https://malicious-external-site.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    # Starlette CORSMiddleware returns 400 for disallowed preflights and omits allow-origin
    assert res.status_code == 400
    assert res.headers.get("access-control-allow-origin") is None


def test_cors_credentialed_request_allowed_origin():
    """Verify actual request with Bearer credentials from allowed origin includes access-control headers."""
    client = TestClient(app)
    res = client.get(
        "/health",
        headers={
            "Origin": "http://127.0.0.1:5173",
            "Authorization": "Bearer demo_token",
        },
    )
    assert res.status_code == 200
    assert res.headers.get("access-control-allow-origin") == "http://127.0.0.1:5173"
    assert res.headers.get("access-control-allow-credentials") == "true"


def test_cors_unapproved_origin_actual_request_no_cors_header():
    """Verify actual request from unapproved origin executes but does not receive CORS allow-origin."""
    client = TestClient(app)
    res = client.get(
        "/health",
        headers={
            "Origin": "https://unauthorized-attacker.com",
        },
    )
    assert res.status_code == 200
    # Crucial security check: Access-Control-Allow-Origin must NOT be present
    assert res.headers.get("access-control-allow-origin") is None
