"""Enterprise action tools for SRE incident diagnostics and triage."""

from datetime import datetime, timezone
import hashlib
from typing import Any, Literal
from pydantic import BaseModel, Field
from langchain_core.tools import tool


class ServiceStatusInput(BaseModel):
    """Input schema for checking microservice health and telemetry."""

    service_name: str = Field(
        description="The exact name of the microservice or database cluster (e.g. 'postgres-primary', 'pgbouncer', 'auth-service', 'payment-gateway')."
    )


class IncidentTicketInput(BaseModel):
    """Input schema for filing a live incident ticket in central monitoring."""

    title: str = Field(
        description="Brief summary of the incident or outage (e.g. 'PostgreSQL primary node failure in us-east-1')."
    )
    severity: Literal["P0", "P1", "P2", "P3"] = Field(
        default="P1",
        description="Incident severity level: 'P0' (Critical customer outage), 'P1' (Major degradation), 'P2' (Partial failure), 'P3' (Low impact).",
    )


# Simulated internal telemetry registry
MOCK_SERVICE_REGISTRY: dict[str, dict[str, Any]] = {
    "postgres-primary": {
        "status": "DOWN",
        "latency_ms": 5200.0,
        "error_rate": 99.4,
        "active_replicas": 1,
        "region": "us-east-1",
        "last_health_check": "2026-11-10T06:00:00Z",
        "diagnostic_alert": "Connection refused on port 5432. Patroni heartbeat expired.",
    },
    "pgbouncer": {
        "status": "DEGRADED",
        "latency_ms": 850.0,
        "error_rate": 32.5,
        "active_replicas": 2,
        "region": "us-east-1",
        "last_health_check": "2026-11-10T06:00:00Z",
        "diagnostic_alert": "Connection pool exhausted. Upstream primary unreachable.",
    },
    "auth-service": {
        "status": "HEALTHY",
        "latency_ms": 18.2,
        "error_rate": 0.02,
        "active_replicas": 4,
        "region": "us-east-1",
        "last_health_check": "2026-11-10T06:00:00Z",
        "diagnostic_alert": "All pods healthy. SCIM and OAuth tokens validating normally.",
    },
    "payment-gateway": {
        "status": "DOWN",
        "latency_ms": 12400.0,
        "error_rate": 100.0,
        "active_replicas": 0,
        "region": "us-east-1",
        "last_health_check": "2026-11-10T06:00:00Z",
        "diagnostic_alert": "503 Service Unavailable. Upstream payment processor timeout.",
    },
}


@tool("get_service_status", args_schema=ServiceStatusInput)
def get_service_status(service_name: str) -> dict[str, Any]:
    """Retrieve real-time health, latency, error rate, and diagnostics for an internal service or database."""
    normalized_name = service_name.strip().lower()

    if normalized_name in MOCK_SERVICE_REGISTRY:
        record = MOCK_SERVICE_REGISTRY[normalized_name]
        return {
            "service_name": normalized_name,
            "status": record["status"],
            "latency_ms": record["latency_ms"],
            "error_rate_pct": record["error_rate"],
            "active_replicas": record["active_replicas"],
            "region": record["region"],
            "diagnostic_alert": record["diagnostic_alert"],
        }

    # Fallback for unknown service
    return {
        "service_name": normalized_name,
        "status": "UNKNOWN",
        "latency_ms": 0.0,
        "error_rate_pct": 0.0,
        "active_replicas": 0,
        "region": "unknown",
        "diagnostic_alert": f"Service '{service_name}' is not registered in the telemetry catalog.",
    }


@tool("create_incident_ticket", args_schema=IncidentTicketInput)
def create_incident_ticket(title: str, severity: str = "P1") -> dict[str, Any]:
    """Create a high-priority incident ticket in the central SRE tracking system (PagerDuty / Jira / ServiceNow)."""
    clean_severity = severity.strip().upper()
    if clean_severity not in ("P0", "P1", "P2", "P3"):
        clean_severity = "P1"

    # Deterministic ticket ID generation from title and timestamp
    timestamp = datetime.now(timezone.utc).isoformat()
    raw_hash = hashlib.md5(f"{title}-{clean_severity}-{timestamp}".encode()).hexdigest()
    ticket_id = f"INC-{raw_hash[:4].upper()}"

    escalation_targets = {
        "P0": "Engineering Director, VP Infrastructure, On-Call SRE Pager",
        "P1": "Principal SRE, Database Team Lead, Primary On-Call",
        "P2": "Secondary On-Call, Service Owner Slack Channel",
        "P3": "Service Team Backlog",
    }

    return {
        "ticket_id": ticket_id,
        "title": title.strip(),
        "severity": clean_severity,
        "status": "OPEN",
        "created_at": timestamp,
        "escalated_to": escalation_targets.get(clean_severity, "On-Call SRE"),
        "confirmation": f"Incident ticket {ticket_id} ({clean_severity}) successfully dispatched.",
    }


# Export list and lookup mapping for model tool-binding
ALL_INCIDENT_TOOLS = [get_service_status, create_incident_ticket]
INCIDENT_TOOL_MAP = {t.name: t for t in ALL_INCIDENT_TOOLS}
