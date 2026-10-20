"""Semantic search retrieval engine and CLI for OpsCopilot."""

import argparse
from pathlib import Path
from typing import Optional

from langchain_core.documents import Document

from src.config import get_settings
from src.vector_store import OpsVectorStore, get_embedding_model


def get_vector_store(persist_dir: Optional[str] = None) -> OpsVectorStore:
    """Connect to the persistent vector store in read-only mode."""
    settings = get_settings()
    target_dir = persist_dir or settings.chroma_persist_dir

    db_path = Path(target_dir) / "runbooks.sqlite3"
    if not db_path.exists():
        raise FileNotFoundError(
            f"Persistent vector store database not found at: {db_path}. "
            "Please run 'python -m src.ingest' first to index runbooks."
        )

    embedding_model = get_embedding_model()
    return OpsVectorStore(
        persist_dir=target_dir,
        embedding_function=embedding_model,
        collection_name="runbooks",
    )


def search(
    query: str,
    k: int = 3,
    score_threshold: Optional[float] = None,
    persist_dir: Optional[str] = None,
) -> list[tuple[Document, float]]:
    """Retrieve top-k documents matching the query by cosine similarity.

    Args:
        query: User incident query or troubleshooting question.
        k: Maximum number of chunks to return (default 3).
        score_threshold: Optional minimum cosine similarity score (e.g. 0.05).
        persist_dir: Optional custom database path.

    Returns:
        List of (Document, relevance_score) tuples sorted by descending relevance.
    """
    store = get_vector_store(persist_dir=persist_dir)
    results = store.similarity_search_with_relevance_scores(query=query, k=k)

    if score_threshold is not None:
        results = [res for res in results if res[1] >= score_threshold]

    return results


def format_search_results(results: list[tuple[Document, float]]) -> str:
    """Format retrieval matches into a clean CLI report."""
    if not results:
        return "No relevant runbook documents found."

    lines = []
    lines.append(f"Found {len(results)} relevant chunk(s):\n")

    for rank, (doc, score) in enumerate(results, start=1):
        filename = doc.metadata.get("filename", "Unknown file")
        title = doc.metadata.get("title", "Untitled")
        doc_id = doc.metadata.get("document_id", "N/A")
        category = doc.metadata.get("category", "General")

        lines.append(f"[{rank}] Match Score (Cosine Similarity): {score:.4f}")
        lines.append(f"    Source:   {filename} ({doc_id})")
        lines.append(f"    Title:    {title}")
        lines.append(f"    Category: {category}")

        # Clean preview without raw newlines
        clean_text = doc.page_content.strip().replace("\n", " ")
        preview = clean_text[:280] + ("..." if len(clean_text) > 280 else "")
        lines.append(f"    Preview:  \"{preview}\"")
        lines.append("-" * 65)

    return "\n".join(lines)


def main() -> None:
    """CLI entrypoint for interactive or argument-based semantic search."""
    parser = argparse.ArgumentParser(
        description="OpsCopilot Semantic Search CLI - Retrieve relevant runbook chunks."
    )
    parser.add_argument(
        "query",
        nargs="?",
        default="How do I handle a database timeout error?",
        help="Troubleshooting query to search in runbooks.",
    )
    parser.add_argument(
        "-k",
        "--top-k",
        type=int,
        default=3,
        help="Number of chunks to retrieve (default: 3).",
    )
    parser.add_argument(
        "-t",
        "--threshold",
        type=float,
        default=None,
        help="Relevance score threshold filter.",
    )

    args = parser.parse_args()

    print("=" * 70)
    print("OPSCOPILOT DAY 5: SEMANTIC SEARCH RETRIEVAL CLI")
    print("=" * 70)
    print(f"Query: '{args.query}' (k={args.top_k})\n")

    results = search(query=args.query, k=args.top_k, score_threshold=args.threshold)
    print(format_search_results(results))
    print("=" * 70)


if __name__ == "__main__":
    main()
