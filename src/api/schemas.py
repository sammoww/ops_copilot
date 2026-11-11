"""Strict Pydantic request and response schemas for OpsCopilot REST API."""

from typing import Optional
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Schema for incoming conversational requests from clients or Slack bots."""

    message: str = Field(
        ...,
        min_length=1,
        description="The operational query, incident description, or diagnostic question.",
        json_schema_extra={"example": "What is the status of the auth-service?"},
    )
    conversation_id: Optional[str] = Field(
        default=None,
        description="Optional session or thread identifier for multi-turn conversational context.",
        json_schema_extra={"example": "conv_user_4821"},
    )


class ChatResponse(BaseModel):
    """Schema for structured responses returned by OpsCopilot."""

    answer: str = Field(
        ...,
        description="The final synthesized answer, runbook resolution, or tool confirmation.",
    )
    sources: list[str] = Field(
        default_factory=list,
        description="List of verified runbook filenames and sections cited in the answer.",
        json_schema_extra={"example": ["database_failover_runbook.md (Section: 4.2 Promote Synchronous Replica)"]},
    )
    tools_called: list[str] = Field(
        default_factory=list,
        description="List of backend operational tools invoked during query execution.",
        json_schema_extra={"example": ["get_service_status"]},
    )
    success: bool = Field(
        default=True,
        description="Whether the query was processed successfully without errors.",
    )


class HealthResponse(BaseModel):
    """Schema for service health check response."""

    status: str = Field(default="ok", description="Operational readiness status.")
    version: str = Field(default="0.1.0", description="API semantic version.")
