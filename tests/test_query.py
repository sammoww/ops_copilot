"""Unit tests for Day 5 Semantic Search and Retrieval Engine."""

import pytest
from src.query import search, get_vector_store, format_search_results


def test_get_vector_store_connection():
    """Verify read-only connection to existing vector store succeeds."""
    store = get_vector_store()
    assert store.count() > 0


def test_search_returns_top_k():
    """Verify search returns exact requested k matches with valid cosine scores."""
    results = search(query="database failover replication lag", k=3)
    assert len(results) == 3

    for doc, score in results:
        assert isinstance(score, float)
        assert -1.0 <= score <= 1.0
        assert "filename" in doc.metadata
        assert "title" in doc.metadata
        assert len(doc.page_content) > 0


def test_search_relevance_ordering():
    """Verify results are sorted by descending relevance score."""
    results = search(query="PostgreSQL primary promote command", k=3)
    assert len(results) == 3
    scores = [score for _, score in results]
    assert scores == sorted(scores, reverse=True)


def test_search_score_threshold_filter():
    """Verify relevance score threshold filters out low-scoring documents."""
    high_threshold_results = search(
        query="PostgreSQL primary promote command",
        k=3,
        score_threshold=0.9999,  # Very high threshold should filter out non-identical matches
    )
    assert len(high_threshold_results) == 0


def test_format_search_results():
    """Verify result formatter produces clean human-readable output."""
    results = search(query="ERR_503_DB_TIMEOUT", k=2)
    formatted = format_search_results(results)
    assert "Match Score (Cosine Similarity):" in formatted
    assert "Source:" in formatted
    assert "Preview:" in formatted
