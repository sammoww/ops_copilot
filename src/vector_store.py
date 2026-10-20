"""Persistent vector database module for OpsCopilot runbooks."""

import hashlib
import json
import re
import sqlite3
from pathlib import Path
from typing import Any, Iterable, Optional

import numpy as np
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.vectorstores import VectorStore
from langchain_openai import OpenAIEmbeddings

from src.config import get_settings


class OpsVectorStore(VectorStore):
    """Production-grade persistent vector store backed by SQLite and dense vector indexing.

    Stores document chunks, metadata, and normalized float32 embeddings on disk.
    Compatible with LangChain VectorStore interface.
    """

    def __init__(
        self,
        persist_dir: str | Path = "./chroma_db",
        embedding_function: Optional[Embeddings] = None,
        collection_name: str = "runbooks",
    ):
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.persist_dir / f"{collection_name}.sqlite3"
        self.collection_name = collection_name
        self.embedding_function = embedding_function or get_embedding_model()

        self._init_db()

    def _init_db(self) -> None:
        """Initialize SQLite schema for vector persistence."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    metadata TEXT NOT NULL,
                    embedding BLOB NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS store_metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )
            conn.commit()

    @property
    def embeddings(self) -> Optional[Embeddings]:
        return self.embedding_function

    def add_texts(
        self,
        texts: Iterable[str],
        metadatas: Optional[list[dict[str, Any]]] = None,
        ids: Optional[list[str]] = None,
        **kwargs: Any,
    ) -> list[str]:
        """Embed texts and insert them into the persistent database."""
        text_list = list(texts)
        if not text_list:
            return []

        meta_list = metadatas if metadatas is not None else [{} for _ in text_list]
        generated_ids = (
            ids
            if ids is not None
            else [
                hashlib.sha256(f"{t}_{i}".encode("utf-8")).hexdigest()[:16]
                for i, t in enumerate(text_list)
            ]
        )

        embeddings = self.embedding_function.embed_documents(text_list)

        with sqlite3.connect(self.db_path) as conn:
            for doc_id, text, meta, emb in zip(generated_ids, text_list, meta_list, embeddings):
                emb_array = np.array(emb, dtype=np.float32)
                # L2 normalize vector for fast cosine similarity via dot product
                norm = np.linalg.norm(emb_array)
                if norm > 0:
                    emb_array = emb_array / norm
                conn.execute(
                    "INSERT OR REPLACE INTO documents (id, content, metadata, embedding) VALUES (?, ?, ?, ?)",
                    (doc_id, text, json.dumps(meta, default=str), emb_array.tobytes()),
                )
            conn.commit()

        return generated_ids

    def count(self) -> int:
        """Return total number of persisted document chunks."""
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM documents")
            row = cur.fetchone()
            return row[0] if row else 0

    def similarity_search_with_relevance_scores(
        self, query: str, k: int = 3, **kwargs: Any
    ) -> list[tuple[Document, float]]:
        """Compute cosine similarity against persisted embeddings and return top-k matches."""
        query_emb = np.array(self.embedding_function.embed_query(query), dtype=np.float32)
        q_norm = np.linalg.norm(query_emb)
        if q_norm > 0:
            query_emb = query_emb / q_norm

        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            rows = cur.execute("SELECT id, content, metadata, embedding FROM documents").fetchall()

        if not rows:
            return []

        scored_results: list[tuple[Document, float]] = []
        for doc_id, content, meta_json, emb_bytes in rows:
            emb = np.frombuffer(emb_bytes, dtype=np.float32)
            score = float(np.dot(query_emb, emb))
            meta = json.loads(meta_json)
            meta["id"] = doc_id
            scored_results.append((Document(page_content=content, metadata=meta), score))

        scored_results.sort(key=lambda x: x[1], reverse=True)
        return scored_results[:k]

    def similarity_search(
        self, query: str, k: int = 3, **kwargs: Any
    ) -> list[Document]:
        """Perform similarity search and return matching Documents."""
        results = self.similarity_search_with_relevance_scores(query, k=k)
        return [doc for doc, _ in results]

    @classmethod
    def from_documents(
        cls,
        documents: list[Document],
        embedding: Embeddings,
        persist_dir: str | Path = "./chroma_db",
        collection_name: str = "runbooks",
        **kwargs: Any,
    ) -> "OpsVectorStore":
        """Factory method to ingest documents directly into persistent storage."""
        store = cls(
            persist_dir=persist_dir,
            embedding_function=embedding,
            collection_name=collection_name,
        )
        texts = [doc.page_content for doc in documents]
        metadatas = [doc.metadata for doc in documents]
        store.add_texts(texts=texts, metadatas=metadatas)
        return store

    @classmethod
    def from_texts(
        cls,
        texts: list[str],
        embedding: Embeddings,
        metadatas: Optional[list[dict[str, Any]]] = None,
        persist_dir: str | Path = "./chroma_db",
        collection_name: str = "runbooks",
        **kwargs: Any,
    ) -> "OpsVectorStore":
        store = cls(
            persist_dir=persist_dir,
            embedding_function=embedding,
            collection_name=collection_name,
        )
        store.add_texts(texts=texts, metadatas=metadatas)
        return store


class DeterministicEmbeddings(Embeddings):
    """Deterministic offline embeddings generator for offline test suites and local development.

    Uses bag-of-words character n-grams and hashing to produce semantically responsive
    1536-dimensional float vectors without requiring external network calls.
    """

    def __init__(self, dimension: int = 1536):
        self.dimension = dimension

    def _embed_single(self, text: str) -> list[float]:
        tokens = re.findall(r"\w+", text.lower())
        vec = np.zeros(self.dimension, dtype=np.float32)
        if not tokens:
            vec[0] = 1.0
            return vec.tolist()

        for token in tokens:
            # Deterministic bucket per token
            token_hash = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16)
            idx = token_hash % self.dimension
            sign = 1.0 if (token_hash % 2 == 0) else -1.0
            vec[idx] += sign

        norm = np.linalg.norm(vec)
        if norm > 0:
            vec /= norm
        return vec.tolist()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_single(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed_single(text)


def get_embedding_model() -> Embeddings:
    """Return configured embedding model.

    Returns OpenAIEmbeddings when a valid live key is present,
    or falls back cleanly to DeterministicEmbeddings for offline/test environments.
    """
    settings = get_settings()
    api_key = settings.openai_api_key.get_secret_value()

    if api_key and not api_key.startswith("sk-test-placeholder"):
        return OpenAIEmbeddings(
            model="text-embedding-3-small",
            openai_api_key=api_key,
        )

    return DeterministicEmbeddings(dimension=1536)
