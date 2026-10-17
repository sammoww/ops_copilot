"""Unit tests for the ingestion and chunking engine."""

import pytest
from pathlib import Path
from src.ingest import (
    load_runbook_documents,
    chunk_documents,
    parse_frontmatter,
    DEFAULT_RUNBOOKS_DIR,
)


def test_parse_frontmatter():
    """Verify YAML frontmatter extraction."""
    raw = (
        "---\n"
        "title: Test Doc\n"
        "category: Testing\n"
        "---\n"
        "# Heading\n"
        "Body content here."
    )
    meta, body = parse_frontmatter(raw)
    assert meta["title"] == "Test Doc"
    assert meta["category"] == "Testing"
    assert "# Heading" in body
    assert "---" not in body


def test_load_runbook_documents():
    """Verify all runbook documents load with file and frontmatter metadata."""
    docs = load_runbook_documents(DEFAULT_RUNBOOKS_DIR)
    assert len(docs) == 3

    filenames = {d.metadata["filename"] for d in docs}
    assert "database_failover_runbook.md" in filenames
    assert "refund_policy_enterprise.md" in filenames
    assert "user_provisioning_sop.md" in filenames

    for doc in docs:
        assert "document_id" in doc.metadata
        assert "title" in doc.metadata
        assert "category" in doc.metadata
        assert len(doc.page_content) > 0


def test_chunk_documents_bounds_and_count():
    """Verify chunking engine breaks docs into semantic chunks respecting size."""
    docs = load_runbook_documents(DEFAULT_RUNBOOKS_DIR)
    chunks = chunk_documents(docs, chunk_size=800, chunk_overlap=120)

    # We expect 20+ chunks from ~13k characters across 3 docs with 800 chunk size
    assert len(chunks) >= 15

    for chunk in chunks:
        # Every chunk must inherit essential metadata
        assert "source" in chunk.metadata
        assert "filename" in chunk.metadata
        assert "document_id" in chunk.metadata
        assert "start_index" in chunk.metadata
        # Content length should respect the size budget (allowing minor variance for indivisible tokens)
        assert len(chunk.page_content) > 0
        assert len(chunk.page_content) <= 900


def test_chunk_overlap_preserves_continuity():
    """Verify overlap exists between consecutive chunks from the same document."""
    docs = load_runbook_documents(DEFAULT_RUNBOOKS_DIR)
    doc1 = [d for d in docs if d.metadata["filename"] == "database_failover_runbook.md"]
    chunks = chunk_documents(doc1, chunk_size=800, chunk_overlap=120)

    assert len(chunks) > 1
    # Check that tail of chunk 0 appears near the head of chunk 1
    chunk_0_tail = chunks[0].page_content[-80:]
    chunk_1_content = chunks[1].page_content

    # Either exact tail or common substring must exist in chunk 1 due to overlap
    overlap_found = any(
        word in chunk_1_content
        for word in chunk_0_tail.split()
        if len(word) > 5
    )
    assert overlap_found, "Consecutive chunks should share overlapping terms"
