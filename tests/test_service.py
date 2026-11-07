"""Unit tests for Day 10 Encapsulated Core Application Service."""

import pytest
from langchain_core.documents import Document
from langchain_core.messages import AIMessage, HumanMessage

from src.prompts import REFUSAL_PHRASE
from src.service import OpsCopilotService, get_opscopilot_service


def test_service_initialization():
    """Verify OpsCopilotService initializes underlying retriever and LCEL chain."""
    service = OpsCopilotService(k=2)
    assert service.vector_store is not None
    assert service.llm is not None
    assert service.base_retriever is not None
    assert service.history_retriever is not None
    assert service.rag_chain is not None


def test_service_health_check_healthy():
    """Verify health_check returns True when dependencies are operational."""
    service = OpsCopilotService()
    assert service.health_check() is True


def test_service_health_check_handles_failure():
    """Verify health_check gracefully returns False when vector store raises an error."""
    from langchain_core.runnables import RunnableLambda

    class BrokenVectorStore:
        def as_retriever(self, **kwargs):
            def broken_probe(query):
                raise RuntimeError("Database connection severed!")
            return RunnableLambda(broken_probe)

    service = OpsCopilotService(vector_store=BrokenVectorStore())
    assert service.health_check() is False


def test_service_query_single_turn():
    """Verify service query executes end-to-end grounded retrieval and generation."""
    service = OpsCopilotService(k=3)
    result = service.query("How do I promote the PostgreSQL replica?")

    assert isinstance(result, dict)
    assert "question" in result
    assert "answer" in result
    assert "source_documents" in result
    assert "chat_history" in result

    assert "pg_ctl promote" in result["answer"]
    assert "database_failover_runbook.md" in result["answer"]
    assert len(result["source_documents"]) == 3


def test_service_query_multi_turn_with_messages():
    """Verify service resolves follow-up queries with pronoun using HumanMessage/AIMessage history."""
    service = OpsCopilotService()
    history = [
        HumanMessage(content="How do I execute a PostgreSQL database failover to the replica?"),
        AIMessage(content="Run pg_ctl promote [Source: database_failover_runbook.md]."),
    ]

    result = service.query("What was the second step of it again?", history=history)
    assert "pg_ctl promote" in result["answer"]
    assert "database_failover_runbook.md" in result["answer"]
    assert REFUSAL_PHRASE not in result["answer"]


def test_service_query_with_dict_history():
    """Verify service normalizes dict-style history from REST API payloads."""
    service = OpsCopilotService()
    dict_history = [
        {"role": "user", "content": "How do I execute a PostgreSQL database failover to the replica?"},
        {"role": "assistant", "content": "Run pg_ctl promote [Source: database_failover_runbook.md]."},
    ]

    result = service.query("What was the second step of it again?", history=dict_history)
    assert "pg_ctl promote" in result["answer"]
    assert "database_failover_runbook.md" in result["answer"]
    assert len(result["chat_history"]) == 2
    assert isinstance(result["chat_history"][0], HumanMessage)
    assert isinstance(result["chat_history"][1], AIMessage)


def test_service_empty_query():
    """Verify service gracefully handles empty or whitespace queries."""
    service = OpsCopilotService()
    result = service.query("   ")
    assert result["answer"] == REFUSAL_PHRASE
    assert result["source_documents"] == []


def test_service_singleton_reusability():
    """Verify get_opscopilot_service returns cached singleton without re-instantiating."""
    s1 = get_opscopilot_service()
    s2 = get_opscopilot_service()
    assert s1 is s2
