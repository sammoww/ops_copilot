"""Unit tests for Day 15: Error Handling & Rate Limiting Guardrails."""

from unittest.mock import MagicMock
import pytest
from fastapi.testclient import TestClient

from src.agent import AgentResponse, OpsCopilotAgent
from src.api.exceptions import RateLimitException, UpstreamServiceException
from src.main import app, get_agent

client = TestClient(app)


def test_rate_limit_exception_returns_429():
    """Verify RateLimitException yields HTTP 429 with Retry-After header and structured error payload."""
    mock_agent = MagicMock(spec=OpsCopilotAgent)
    mock_agent.run.side_effect = RateLimitException("Simulated quota exhaustion", retry_after=5)

    app.dependency_overrides[get_agent] = lambda: mock_agent
    try:
        response = client.post("/chat", json={"message": "Any operational question"})
        assert response.status_code == 429
        data = response.json()
        assert data["error_code"] == "RATE_LIMIT_EXCEEDED"
        assert "quota exhaustion" in data["message"].lower() or "rate limit" in data["message"].lower()
        assert data["retry_after"] == 5
        assert response.headers.get("retry-after") == "5"
        assert "timestamp" in data
    finally:
        app.dependency_overrides.clear()


def test_upstream_service_timeout_returns_503():
    """Verify UpstreamServiceException yields HTTP 503 with Retry-After header."""
    mock_agent = MagicMock(spec=OpsCopilotAgent)
    mock_agent.run.side_effect = UpstreamServiceException("OpenAI connection timed out", retry_after=10)

    app.dependency_overrides[get_agent] = lambda: mock_agent
    try:
        response = client.post("/chat", json={"message": "Failover query"})
        assert response.status_code == 503
        data = response.json()
        assert data["error_code"] == "UPSTREAM_SERVICE_UNAVAILABLE"
        assert "timed out" in data["message"].lower() or "unavailable" in data["message"].lower()
        assert data["retry_after"] == 10
        assert response.headers.get("retry-after") == "10"
    finally:
        app.dependency_overrides.clear()


def test_agent_error_message_translates_to_rate_limit():
    """Verify agent returning rate limit error message triggers 429 translation."""
    mock_agent = MagicMock(spec=OpsCopilotAgent)
    mock_agent.run.return_value = AgentResponse(
        query="Check status",
        answer="Failed",
        success=False,
        error_message="OpenAI error 429: rate limit exceeded for tokens",
    )

    app.dependency_overrides[get_agent] = lambda: mock_agent
    try:
        response = client.post("/chat", json={"message": "Check status"})
        assert response.status_code == 429
        data = response.json()
        assert data["error_code"] == "RATE_LIMIT_EXCEEDED"
    finally:
        app.dependency_overrides.clear()


def test_agent_error_message_translates_to_timeout():
    """Verify agent returning timeout error message triggers 503 translation."""
    mock_agent = MagicMock(spec=OpsCopilotAgent)
    mock_agent.run.return_value = AgentResponse(
        query="Check status",
        answer="Failed",
        success=False,
        error_message="Connection timed out waiting for OpenAI socket",
    )

    app.dependency_overrides[get_agent] = lambda: mock_agent
    try:
        response = client.post("/chat", json={"message": "Check status"})
        assert response.status_code == 503
        data = response.json()
        assert data["error_code"] == "UPSTREAM_SERVICE_UNAVAILABLE"
    finally:
        app.dependency_overrides.clear()


def test_generic_unhandled_exception_returns_clean_500():
    """Verify unexpected Python crashes return clean 500 without leaking file paths or traces."""
    mock_agent = MagicMock(spec=OpsCopilotAgent)
    mock_agent.run.side_effect = RuntimeError("Sensitive internal database password leak: secret_db_pw")

    app.dependency_overrides[get_agent] = lambda: mock_agent
    try:
        response = client.post("/chat", json={"message": "Exploit attempt"})
        assert response.status_code == 500
        data = response.json()
        # Ensure sensitive details from the stack trace were stripped from client response
        assert "secret_db_pw" not in str(data)
        assert "unexpected internal error" in str(data).lower()
    finally:
        app.dependency_overrides.clear()
