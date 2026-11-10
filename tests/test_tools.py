"""Unit tests for Day 11: Defining External Action Tools."""

import pytest
from pydantic import ValidationError
from src.rag_chain import get_tool_enabled_model
from src.tools.incident_tools import (
    ALL_INCIDENT_TOOLS,
    INCIDENT_TOOL_MAP,
    create_incident_ticket,
    get_service_status,
)


def test_tool_definitions_and_schemas():
    """Verify incident tools export valid LangChain schemas and descriptions."""
    assert len(ALL_INCIDENT_TOOLS) == 2
    assert "get_service_status" in INCIDENT_TOOL_MAP
    assert "create_incident_ticket" in INCIDENT_TOOL_MAP

    status_tool = INCIDENT_TOOL_MAP["get_service_status"]
    assert status_tool.name == "get_service_status"
    assert "health" in status_tool.description.lower()

    ticket_tool = INCIDENT_TOOL_MAP["create_incident_ticket"]
    assert ticket_tool.name == "create_incident_ticket"
    assert "incident ticket" in ticket_tool.description.lower()


def test_get_service_status_healthy():
    """Verify get_service_status returns accurate telemetry for a healthy service."""
    result = get_service_status.invoke({"service_name": "auth-service"})
    assert isinstance(result, dict)
    assert result["service_name"] == "auth-service"
    assert result["status"] == "HEALTHY"
    assert result["latency_ms"] < 50.0
    assert result["error_rate_pct"] < 1.0


def test_get_service_status_down():
    """Verify get_service_status returns accurate failure details for a down database."""
    result = get_service_status.invoke({"service_name": "postgres-primary"})
    assert isinstance(result, dict)
    assert result["service_name"] == "postgres-primary"
    assert result["status"] == "DOWN"
    assert result["error_rate_pct"] > 90.0
    assert "Connection refused" in result["diagnostic_alert"]


def test_get_service_status_unknown_service():
    """Verify get_service_status handles unregistered service names gracefully."""
    result = get_service_status.invoke({"service_name": "non-existent-cluster"})
    assert result["status"] == "UNKNOWN"
    assert "not registered" in result["diagnostic_alert"]


def test_create_incident_ticket_p0():
    """Verify create_incident_ticket dispatches a P0 critical outage ticket with escalation."""
    result = create_incident_ticket.invoke(
        {
            "title": "PostgreSQL Primary Node Down in us-east-1",
            "severity": "P0",
        }
    )
    assert isinstance(result, dict)
    assert result["ticket_id"].startswith("INC-")
    assert result["severity"] == "P0"
    assert result["status"] == "OPEN"
    assert "Engineering Director" in result["escalated_to"]
    assert "created_at" in result


def test_create_incident_ticket_omitted_severity_defaults_to_p1():
    """Verify create_incident_ticket defaults to P1 when severity is omitted."""
    result = create_incident_ticket.invoke(
        {
            "title": "Slow query alert on analytical replica",
        }
    )
    assert result["severity"] == "P1"
    assert result["ticket_id"].startswith("INC-")
    assert "Principal SRE" in result["escalated_to"]


def test_create_incident_ticket_invalid_severity_raises_validation_error():
    """Verify Pydantic enforces strict Literal validation for severity levels."""
    with pytest.raises(ValidationError):
        create_incident_ticket.invoke(
            {
                "title": "Invalid alert",
                "severity": "INVALID_TIER",
            }
        )


def test_model_tool_binding_detects_status_call():
    """Verify tool-bound model detects get_service_status call when prompted."""
    model = get_tool_enabled_model()
    response = model.invoke("Can you check the health and status of auth-service?")

    assert hasattr(response, "tool_calls")
    assert len(response.tool_calls) > 0

    call = response.tool_calls[0]
    assert call["name"] == "get_service_status"
    assert call["args"]["service_name"] == "auth-service"


def test_model_tool_binding_detects_incident_call():
    """Verify tool-bound model detects create_incident_ticket call for urgent outages."""
    model = get_tool_enabled_model()
    response = model.invoke("The payments database is down, file an urgent incident ticket.")

    assert hasattr(response, "tool_calls")
    assert len(response.tool_calls) > 0

    tool_names = [c["name"] for c in response.tool_calls]
    assert "create_incident_ticket" in tool_names
