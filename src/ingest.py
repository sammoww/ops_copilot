"""Document ingestion and semantic chunking engine."""

import re
from pathlib import Path
from typing import Any
import yaml
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

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

        # Normalize any nested list/dict metadata fields to string representation for Chroma compatibility
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


if __name__ == "__main__":
    print("=" * 70)
    print("OPSCOPILOT DAY 3: INGESTION & CHUNKING ENGINE")
    print("=" * 70)

    # 1. Load documents
    raw_docs = load_runbook_documents()
    print(f"\n[LOAD] Successfully loaded {len(raw_docs)} runbook document(s):")
    for doc in raw_docs:
        title = doc.metadata.get("title", "Untitled")
        print(f"  - {doc.metadata['filename']} | Title: '{title}' ({len(doc.page_content)} chars)")

    # 2. Chunk documents
    chunks = chunk_documents(raw_docs, chunk_size=800, chunk_overlap=120)
    print(f"\n[SPLIT] Generated {len(chunks)} total chunk(s) (chunk_size=800, chunk_overlap=120)")

    # 3. Inspect sample chunks
    samples_to_inspect = min(2, len(chunks))
    for i in range(samples_to_inspect):
        sample = chunks[i]
        print("\n" + "-" * 70)
        print(f"SAMPLE CHUNK #{i + 1}")
        print("-" * 70)
        print(f"Metadata:")
        for k, v in sample.metadata.items():
            print(f"  * {k}: {v}")
        print("\nContent Preview (first 250 characters):")
        preview = sample.page_content[:250].strip().replace("\n", " ")
        print(f"  \"{preview}...\"")
        print(f"Total Chunk Character Length: {len(sample.page_content)}")

    print("\n" + "=" * 70)
    print("[SUCCESS] Ingestion & chunking engine validated cleanly!")
    print("=" * 70)
