"""Unit tests for Day 6 Zero-Hallucination Prompt Engineering."""

import pytest
from src.prompts import RAG_PROMPT, REFUSAL_PHRASE, get_rag_prompt_template


def test_rag_prompt_variables():
    """Verify prompt expects exact required variables: context and question."""
    prompt = get_rag_prompt_template()
    assert set(prompt.input_variables) == {"context", "question"}


def test_rag_prompt_formatting():
    """Verify prompt formats context and question accurately into System and Human messages."""
    context_text = "[Source: test.md] Emergency steps: run reboot."
    question_text = "What is the emergency step?"

    messages = RAG_PROMPT.format_messages(
        context=context_text,
        question=question_text,
    )

    assert len(messages) == 2
    system_msg, human_msg = messages[0], messages[1]

    # Verify system message contains guardrails
    assert "STRICT GROUNDING" in system_msg.content
    assert REFUSAL_PHRASE in system_msg.content
    assert "MANDATORY CITATIONS" in system_msg.content
    assert context_text in system_msg.content

    # Verify human message contains question
    assert question_text in human_msg.content


def test_refusal_phrase_embedded():
    """Verify exact refusal phrase is embedded into system instructions."""
    prompt = get_rag_prompt_template()
    formatted = prompt.format(context="empty", question="test")
    assert REFUSAL_PHRASE in formatted
