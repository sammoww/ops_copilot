"""Document ingestion, semantic chunking, and vector database persistence engine."""

import re
import time
from pathlib import Path
from typing import Any, Optional
import yaml
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.config import get_settings
from src.vector_store import OpsVectorStore, get_embedding_model

# Path to runbooks directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_RUNBOOKS_DIR = PROJECT_ROOT / "data" / "runbooks"


def parse_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    """Extract YAML frontmatter and body from a markdown document.

    If frontmatter is present between leading '---' lines, parses it as a dict.
    Returns (metadata_dict, body_content).
    """
    frontmatter_pattern = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
    match = frontmatter_pattern.match(content)
    if match:
        raw_yaml = match.group(1)
        body = content[match.end():]
        try:
            metadata = yaml.safe_load(raw_yaml) or {}
            if not isinstance(metadata, dict):
                metadata = {}
        except Exception:
            metadata = {}
        return metadata, body
    return {}, content


def load_runbook_documents(runbooks_dir: Path = DEFAULT_RUNBOOKS_DIR) -> list[Document]:
    """Read all markdown (.md) documents from runbooks_dir with metadata."""
    if not runbooks_dir.exists():
        raise FileNotFoundError(f"Runbooks directory not found: {runbooks_dir}")

    md_files = sorted(runbooks_dir.glob("*.md"))
    if not md_files:
        raise ValueError(f"No markdown documents found in {runbooks_dir}")

    documents: list[Document] = []
    for file_path in md_files:
        raw_content = file_path.read_text(encoding="utf-8")
        frontmatter_meta, body = parse_frontmatter(raw_content)

        # Merge frontmatter with file-system metadata
        metadata: dict[str, Any] = {
            "source": str(file_path),
            "filename": file_path.name,
            **frontmatter_meta,
        }

        # Normalize any nested list/dict metadata fields to string representation for store compatibility
        sanitized_meta = {}
        for k, v in metadata.items():
            if isinstance(v, (list, dict)):
                sanitized_meta[k] = ", ".join(str(item) for item in v) if isinstance(v, list) else str(v)
            else:
                sanitized_meta[k] = v

        documents.append(Document(page_content=body, metadata=sanitized_meta))

    return documents


def get_chunking_splitter(
    chunk_size: int = 800,
    chunk_overlap: int = 120,
) -> RecursiveCharacterTextSplitter:
    """Return a configured RecursiveCharacterTextSplitter."""
    return RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        add_start_index=True,
        separators=["\n\n", "\n", " ", ""],
    )


def chunk_documents(
    documents: list[Document],
    chunk_size: int = 800,
    chunk_overlap: int = 120,
) -> list[Document]:
    """Split raw documents into semantic chunks with token/character boundary control."""
    splitter = get_chunking_splitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    chunks = splitter.split_documents(documents)
    return chunks


def ingest_to_vector_store(
    documents: Optional[list[Document]] = None,
    persist_dir: Optional[str] = None,
    embedding_model: Optional[Embeddings] = None,
) -> tuple[OpsVectorStore, float]:
    """Ingest document chunks into persistent vector store with execution timing."""
    settings = get_settings()
    target_dir = persist_dir or settings.chroma_persist_dir
    embeddings = embedding_model or get_embedding_model()

    if documents is None:
        raw_docs = load_runbook_documents()
        documents = chunk_documents(raw_docs)

    start_time = time.perf_counter()
    vector_store = OpsVectorStore.from_documents(
        documents=documents,
        embedding=embeddings,
        persist_dir=target_dir,
    )
    duration = time.perf_counter() - start_time

    return vector_store, duration


if __name__ == "__main__":
    print("=" * 70)
    print("OPSCOPILOT DAY 4: VECTOR EMBEDDING & DATABASE PERSISTENCE")
    print("=" * 70)

    # 1. Load documents
    raw_docs = load_runbook_documents()
    print(f"\n[LOAD] Loaded {len(raw_docs)} runbook document(s):")
    for doc in raw_docs:
        title = doc.metadata.get("title", "Untitled")
        print(f"  - {doc.metadata['filename']} | '{title}' ({len(doc.page_content)} chars)")

    # 2. Chunk documents
    chunks = chunk_documents(raw_docs, chunk_size=800, chunk_overlap=120)
    print(f"\n[SPLIT] Generated {len(chunks)} total chunk(s) (chunk_size=800, chunk_overlap=120)")

    # 3. Vector Embeddings & Persistence
    settings = get_settings()
    print(f"\n[EMBED & PERSIST] Saving embeddings to '{settings.chroma_persist_dir}'...")
    store, elapsed = ingest_to_vector_store(chunks)

    print(f"  -> Successfully persisted {store.count()} chunks in {elapsed:.3f} seconds!")
    print(f"  -> Database file located at: {store.db_path.resolve()}")

    # 4. Verify disk persistence files
    db_files = list(Path(settings.chroma_persist_dir).glob("*"))
    print(f"\n[DISK VERIFICATION] Files in persistent directory:")
    for f in db_files:
        print(f"  * {f.name} ({f.stat().st_size:,} bytes)")

    print("\n" + "=" * 70)
    print("[SUCCESS] Day 4 vector embedding & database persistence complete!")
    print("=" * 70)
