"""Unit tests for Day 7 End-to-End RAG Chain."""

import pytest
from src.rag_chain import answer_question, format_docs, build_rag_chain
from src.prompts import REFUSAL_PHRASE
from langchain_core.documents import Document


def test_format_docs():
    """Verify document formatting preserves source metadata and body content."""
    docs = [
        Document(
            page_content="Reboot step 1",
            metadata={"filename": "test.md", "title": "Test Runbook", "document_id": "RB-01"},
        )
    ]
    formatted = format_docs(docs)
    assert "Source: test.md" in formatted
    assert "Title: Test Runbook" in formatted
    assert "ID: RB-01" in formatted
    assert "Reboot step 1" in formatted


def test_build_rag_chain_returns_retriever_and_pipeline():
    """Verify build_rag_chain constructs runnable LCEL components."""
    retriever, chain = build_rag_chain(k=2)
    assert retriever is not None
    assert chain is not None


def test_answer_question_returns_grounded_citations():
    """Verify end-to-end pipeline returns answer with bracketed citations and source documents."""
    result = answer_question("How do I promote the PostgreSQL replica?", k=3)

    assert "answer" in result
    assert "source_documents" in result
    assert len(result["source_documents"]) == 3

    answer = result["answer"]
    assert "[Source:" in answer
    assert "Section:" in answer


def test_answer_question_out_of_domain_refusal():
    """Verify end-to-end pipeline returns exact refusal phrase for unrelated questions."""
    result = answer_question("What is the recipe for baking chocolate brownies?", k=3)
    assert REFUSAL_PHRASE in result["answer"]
