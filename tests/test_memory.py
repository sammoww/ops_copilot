"""Unit tests for Day 9: Chat Memory & History-Aware Retrieval."""

import pytest
from langchain_core.messages import AIMessage, HumanMessage
from src.prompts import REFUSAL_PHRASE
from src.rag_chain import answer_question, build_rag_chain


def test_history_aware_retriever_build():
    """Verify build_rag_chain returns a history-aware retriever and LCEL pipeline."""
    retriever, chain = build_rag_chain(k=2)
    assert retriever is not None
    assert chain is not None


def test_single_turn_without_history():
    """Verify single turn queries work seamlessly when chat_history is None or empty."""
    result = answer_question("What is the command to promote the PostgreSQL replica?")
    assert "answer" in result
    assert "pg_ctl promote" in result["answer"]
    assert "database_failover_runbook.md" in result["answer"]
    assert result["chat_history"] == []


def test_multi_turn_followup_with_pronoun():
    """Verify follow-up query with pronoun ('it', 'second step') resolves using chat history."""
    # Turn 1: User asks about PostgreSQL replica promotion
    turn1_history = [
        HumanMessage(content="How do I execute a PostgreSQL database failover to the replica?"),
        AIMessage(
            content="1. Isolate primary. 2. Promote replica: `/usr/lib/postgresql/16/bin/pg_ctl promote` [Source: database_failover_runbook.md]."
        ),
    ]

    # Turn 2: User asks follow-up using pronoun 'it' without mentioning PostgreSQL
    result = answer_question("What was the second step of it again?", chat_history=turn1_history)

    answer = result["answer"]
    docs = result["source_documents"]

    # History-aware retriever must have retrieved database failover runbook
    retrieved_files = [d.metadata.get("filename") for d in docs]
    assert "database_failover_runbook.md" in retrieved_files

    # Answer must contain the PostgreSQL command and citation
    assert "pg_ctl promote" in answer
    assert "database_failover_runbook.md" in answer
    assert REFUSAL_PHRASE not in answer


def test_multi_turn_topic_switching():
    """Verify conversation smoothly switches topics from database failover to SLA refund credit."""
    history = [
        HumanMessage(content="How do I promote the PostgreSQL replica?"),
        AIMessage(content="Run pg_ctl promote [Source: database_failover_runbook.md]."),
    ]

    # Switch topic to SLA credit
    result = answer_question(
        "What refund percentage applies for 99.2% monthly uptime?",
        chat_history=history,
    )

    answer = result["answer"]
    docs = result["source_documents"]

    retrieved_files = [d.metadata.get("filename") for d in docs]
    assert "refund_policy_enterprise.md" in retrieved_files
    assert "50% credit" in answer
    assert "refund_policy_enterprise.md" in answer


def test_multi_turn_refusal_preserved():
    """Verify conversational history does not allow out-of-domain questions to bypass refusal guardrails."""
    history = [
        HumanMessage(content="How do I promote the PostgreSQL replica?"),
        AIMessage(content="Run pg_ctl promote [Source: database_failover_runbook.md]."),
    ]

    # Out-of-domain follow-up
    result = answer_question(
        "Can you also give me a recipe to bake chocolate cake with it?",
        chat_history=history,
    )

    assert REFUSAL_PHRASE in result["answer"]
