"""Unit tests for Day 4 Vector Embeddings and Database Persistence."""

import pytest
from pathlib import Path
from langchain_core.documents import Document

from src.vector_store import (
    OpsVectorStore,
    DeterministicEmbeddings,
    get_embedding_model,
)
from src.ingest import ingest_to_vector_store, chunk_documents, load_runbook_documents


def test_deterministic_embeddings():
    """Verify offline embeddings generator creates consistent 1536-dim normalized vectors."""
    emb_model = DeterministicEmbeddings(dimension=1536)
    vec1 = emb_model.embed_query("Postgres failover runbook")
    vec2 = emb_model.embed_query("Postgres failover runbook")
    vec3 = emb_model.embed_query("Refund SLA policy")

    assert len(vec1) == 1536
    # Exact text produces identical vector (deterministic)
    assert vec1 == vec2
    # Distinct text produces distinct vector
    assert vec1 != vec3


def test_ops_vector_store_persistence(tmp_path: Path):
    """Verify document chunks and embeddings persist to SQLite file and load back."""
    test_db_dir = tmp_path / "test_store"
    emb_model = DeterministicEmbeddings(dimension=1536)

    docs = [
        Document(
            page_content="PostgreSQL HA failover steps and Patroni commands.",
            metadata={"category": "database", "severity": "P1"},
        ),
        Document(
            page_content="Enterprise SLA breach credit calculation and refund tiers.",
            metadata={"category": "billing", "severity": "P2"},
        ),
    ]

    # Ingest documents
    store = OpsVectorStore.from_documents(
        documents=docs,
        embedding=emb_model,
        persist_dir=test_db_dir,
    )

    assert store.count() == 2
    assert store.db_path.exists()

    # Re-open the store from the same directory (persistence test)
    reopened_store = OpsVectorStore(
        persist_dir=test_db_dir,
        embedding_function=emb_model,
    )
    assert reopened_store.count() == 2

    # Verify search against persisted store
    results = reopened_store.similarity_search_with_relevance_scores("PostgreSQL failover", k=1)
    assert len(results) == 1
    match_doc, score = results[0]
    assert "PostgreSQL HA failover" in match_doc.page_content
    assert match_doc.metadata["category"] == "database"
    assert score > 0.0


def test_ingest_pipeline_with_timing(tmp_path: Path):
    """Verify end-to-end Day 4 ingestion function with timing."""
    test_dir = tmp_path / "pipeline_test"
    docs = load_runbook_documents()
    chunks = chunk_documents(docs)

    store, elapsed = ingest_to_vector_store(
        documents=chunks,
        persist_dir=str(test_dir),
        embedding_model=DeterministicEmbeddings(1536),
    )

    assert store.count() >= 20
    assert elapsed > 0.0
    assert (test_dir / "runbooks.sqlite3").exists()
