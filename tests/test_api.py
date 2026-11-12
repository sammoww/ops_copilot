"""Unit tests for Day 13: FastAPI Skeleton & REST Schemas."""

import pytest
from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


def test_root_endpoint():
    """Verify GET / returns basic service discovery info."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "OpsCopilot API"
    assert data["status"] == "online"
    assert "health" in data


def test_health_check_endpoint():
    """Verify GET /health returns standard 200 OK readiness probe."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["version"] == "0.1.0"


def test_chat_endpoint_status_query():
    """Verify POST /chat routes to tool-enabled agent and returns structured response."""
    payload = {"message": "What is the status of the auth-service?"}
    response = client.post("/chat", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert "auth-service" in data["answer"]
    assert "get_service_status" in data["tools_called"]
    assert data["success"] is True


def test_api_v1_chat_endpoint_alias():
    """Verify POST /api/v1/chat route works identically."""
    payload = {"message": "What is the status of the auth-service?"}
    response = client.post("/api/v1/chat", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert "auth-service" in data["answer"]
    assert data["success"] is True


def test_chat_endpoint_runbook_query_citations():
    """Verify POST /chat extracts verified runbook source citations."""
    payload = {"message": "What are the procedure steps to fail over PostgreSQL to replica?"}
    response = client.post("/chat", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert "pg_ctl promote" in data["answer"] or "Isolate the degraded primary" in data["answer"]
    assert len(data["sources"]) > 0
    assert any("database_failover" in s.lower() for s in data["sources"])


def test_chat_endpoint_validation_error_empty_message():
    """Verify Pydantic enforces min_length=1 on message, rejecting empty strings with 422."""
    payload = {"message": ""}
    response = client.post("/chat", json=payload)
    assert response.status_code == 422


def test_chat_endpoint_missing_message_field():
    """Verify missing required message field fails validation with 422."""
    payload = {"conversation_id": "conv_123"}
    response = client.post("/chat", json=payload)
    assert response.status_code == 422


def test_cors_headers():
    """Verify CORS middleware adds Access-Control-Allow-Origin header."""
    response = client.get("/health", headers={"Origin": "http://localhost:3000"})
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") in ("*", "http://localhost:3000")


def test_chat_stream_endpoint_returns_sse_tokens():
    """Verify POST /api/v1/chat/stream returns text/event-stream chunks with SSE framing."""
    import json

    payload = {"message": "What is the status of the auth-service?"}
    response = client.post("/api/v1/chat/stream", json=payload)

    assert response.status_code == 200
    assert "text/event-stream" in response.headers.get("content-type", "")

    # Parse SSE stream text
    lines = [line.strip() for line in response.text.split("\n") if line.strip()]
    assert len(lines) > 0

    tokens = []
    has_done_signal = False

    for line in lines:
        assert line.startswith("data: ")
        raw_data = line.replace("data: ", "", 1).strip()
        if raw_data == "[DONE]":
            has_done_signal = True
        else:
            parsed = json.loads(raw_data)
            assert "token" in parsed
            tokens.append(parsed["token"])

    assert has_done_signal is True
    full_text = "".join(tokens)
    assert "auth-service" in full_text
    assert "HEALTHY" in full_text


def test_chat_stream_runbook_tokens():
    """Verify POST /chat/stream streams runbook troubleshooting guidance."""
    import json

    payload = {"message": "What are the procedure steps to fail over PostgreSQL to replica?"}
    response = client.post("/chat/stream", json=payload)

    assert response.status_code == 200
    assert "text/event-stream" in response.headers.get("content-type", "")

    lines = [line.strip() for line in response.text.split("\n") if line.strip()]
    tokens = []
    for line in lines:
        raw_data = line.replace("data: ", "", 1).strip()
        if raw_data != "[DONE]":
            tokens.append(json.loads(raw_data)["token"])

    full_text = "".join(tokens)
    assert "Isolate the degraded primary" in full_text
    assert "pg_ctl promote" in full_text


def test_chat_stream_empty_message_rejected():
    """Verify streaming endpoint rejects empty message with 422 Unprocessable Entity."""
    payload = {"message": ""}
    response = client.post("/api/v1/chat/stream", json=payload)
    assert response.status_code == 422

