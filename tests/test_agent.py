"""Unit tests for Day 12: Tool Routing & ReAct Execution Loop."""

import pytest
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from src.agent import OpsCopilotAgent, run_agent


def test_agent_status_routing_healthy_service():
    """Verify agent routes status query to get_service_status and formats output."""
    agent = OpsCopilotAgent()
    response = agent.run("What is the status of the auth-service?")

    assert response.success is True
    assert "get_service_status" in response.tools_called
    assert len(response.intermediate_steps) == 1
    assert response.intermediate_steps[0].tool_name == "get_service_status"
    assert response.intermediate_steps[0].is_error is False

    # Assert answer formatting
    assert "auth-service" in response.answer
    assert "HEALTHY" in response.answer
    assert "18.2" in response.answer or "latency" in response.answer.lower()


def test_agent_status_routing_down_database():
    """Verify agent detects down status and includes diagnostic alert in answer."""
    agent = OpsCopilotAgent()
    response = agent.run("Check health and status of postgres-primary")

    assert response.success is True
    assert "get_service_status" in response.tools_called
    assert "postgres-primary" in response.answer
    assert "DOWN" in response.answer
    assert "Connection refused" in response.answer or "Patroni" in response.answer


def test_agent_incident_ticket_creation():
    """Verify agent routes outage alert to create_incident_ticket and synthesizes ticket confirmation."""
    agent = OpsCopilotAgent()
    response = agent.run("Payment gateway is down, file an urgent incident ticket")

    assert response.success is True
    assert "create_incident_ticket" in response.tools_called
    assert len(response.intermediate_steps) == 1
    assert "INC-" in response.answer
    assert "successfully opened" in response.answer or "dispatched" in response.answer


def test_agent_runbook_search_routing():
    """Verify agent routes procedural troubleshooting query to search_runbooks tool."""
    agent = OpsCopilotAgent()
    response = agent.run("What are the procedure steps to fail over PostgreSQL to replica?")

    assert response.success is True
    assert "search_runbooks" in response.tools_called
    assert "Isolate the degraded primary" in response.answer
    assert "pg_ctl promote" in response.answer
    assert "database_failover_runbook.md" in response.answer


def test_agent_direct_conversation_without_tools():
    """Verify conversational queries do not trigger tool calls and reply directly."""
    agent = OpsCopilotAgent()
    response = agent.run("Hello, who are you and what do you do?")

    assert response.success is True
    assert len(response.tools_called) == 0
    assert len(response.intermediate_steps) == 0
    assert response.iterations == 1
    assert "OpsCopilot" in response.answer


def test_agent_empty_query_guard():
    """Verify empty or blank queries return immediately without invoking tools."""
    agent = OpsCopilotAgent()
    response = agent.run("   ")

    assert response.success is True
    assert len(response.tools_called) == 0
    assert response.iterations == 0
    assert "No query provided" in response.answer


class InfiniteLoopMockModel(BaseChatModel):
    """Mock model that always issues a tool call, never returning a final answer."""

    def _generate(self, messages: list[BaseMessage], **kwargs):
        # Always issue a status tool call
        return ChatResult(
            generations=[
                ChatGeneration(
                    message=AIMessage(
                        content="",
                        tool_calls=[
                            {
                                "name": "get_service_status",
                                "args": {"service_name": "auth-service"},
                                "id": "call_loop_test",
                                "type": "tool_call",
                            }
                        ],
                    )
                )
            ]
        )

    def bind_tools(self, tools, **kwargs):
        return self

    @property
    def _llm_type(self) -> str:
        return "infinite-loop-mock"


def test_agent_infinite_loop_prevention():
    """Verify agent loop aborts when max_iterations ceiling is hit."""
    mock_model = InfiniteLoopMockModel()
    agent = OpsCopilotAgent(model=mock_model, max_iterations=3)
    response = agent.run("Check service status")

    assert response.success is False
    assert response.iterations == 3
    assert "Maximum agent iterations exceeded" in response.error_message
    assert len(response.intermediate_steps) == 3


class BadArgsMockModel(BaseChatModel):
    """Mock model that issues a tool call with invalid arguments to trigger ValidationError."""

    def _generate(self, messages: list[BaseMessage], **kwargs):
        # If tool returned error feedback, provide final apology
        if any(getattr(m, "type", "") == "tool" for m in messages):
            return ChatResult(
                generations=[ChatGeneration(message=AIMessage(content="Ticket creation failed due to invalid severity."))]
            )

        # First turn: send invalid severity to create_incident_ticket
        return ChatResult(
            generations=[
                ChatGeneration(
                    message=AIMessage(
                        content="",
                        tool_calls=[
                            {
                                "name": "create_incident_ticket",
                                "args": {"title": "Outage", "severity": "INVALID_P99"},
                                "id": "call_bad_args",
                                "type": "tool_call",
                            }
                        ],
                    )
                )
            ]
        )

    def bind_tools(self, tools, **kwargs):
        return self

    @property
    def _llm_type(self) -> str:
        return "bad-args-mock"


def test_agent_catches_validation_error_and_recovers():
    """Verify agent catches ValidationError, records error step, and hands it back to model."""
    mock_model = BadArgsMockModel()
    agent = OpsCopilotAgent(model=mock_model, max_iterations=3)
    response = agent.run("Create a ticket with bad severity")

    assert response.success is True
    assert len(response.intermediate_steps) == 1
    assert response.intermediate_steps[0].is_error is True
    assert "VALIDATION_ERROR" in response.intermediate_steps[0].output
    assert "invalid severity" in response.answer.lower()
