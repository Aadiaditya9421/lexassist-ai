"""
knowledge_base/ingest.py
─────────────────────────
Document loader, chunker, embedder and ChromaDB builder for LexAssist AI.

Two public functions for use by the rest of the system:
    build_vectorstore()  — call once to ingest all docs into ChromaDB
    get_vectorstore()    — call at runtime to load the persisted store

Usage:
    # First time (or when docs change):
    python -m knowledge_base.ingest

    # In graph/nodes.py:
    from knowledge_base.ingest import get_vectorstore
    vectorstore = get_vectorstore()
"""

import sys
import logging
import re
from pathlib import Path
from typing import Optional

import yaml

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import config

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("ingest")


# ── Constants ─────────────────────────────────────────────────────────────────
# Sections headers that should never be split mid-sentence
_SEPARATORS = [
    "\n================================================================================",
    "\n--------------------------------------------------------------------------------",
    "\n\n",
    "\n",
    ". ",
    " ",
    "",
]

# Required YAML frontmatter keys — docs missing these get a warning not a crash
_REQUIRED_META_KEYS = {"title", "category", "source", "year"}


# ─────────────────────────────────────────────────────────────────────────────
# 1. FRONTMATTER PARSER
# ─────────────────────────────────────────────────────────────────────────────

def parse_frontmatter(text: str) -> tuple[dict, str]:
    """
    Split YAML frontmatter from document body.

    Expects documents that start with:
        ---
        key: value
        ---
        body text...

    Returns:
        (metadata_dict, body_text)
        On parse failure: returns ({}, full_text) so ingestion continues.
    """
    text = text.strip()

    if not text.startswith("---"):
        return {}, text

    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text

    try:
        meta = yaml.safe_load(parts[1]) or {}
        body = parts[2].strip()
    except yaml.YAMLError as e:
        log.warning(f"  YAML parse error: {e} — using empty metadata")
        meta = {}
        body = text

    # Coerce all values to strings for ChromaDB compatibility
    # (ChromaDB metadata values must be str, int, float, or bool)
    clean_meta = {}
    for k, v in meta.items():
        if isinstance(v, (str, int, float, bool)):
            clean_meta[k] = v
        else:
            clean_meta[k] = str(v)

    # Warn about missing required keys
    missing = _REQUIRED_META_KEYS - set(clean_meta.keys())
    if missing:
        log.warning(f"  Missing metadata keys: {missing}")

    return clean_meta, body


# ─────────────────────────────────────────────────────────────────────────────
# 2. DOCUMENT LOADER
# ─────────────────────────────────────────────────────────────────────────────

def load_documents(docs_dir: Optional[str] = None) -> list[Document]:
    """
    Load all .txt files from docs_dir, parse frontmatter, return
    a list of LangChain Document objects.

    Args:
        docs_dir: path to the docs folder. Defaults to config.docs_dir.

    Returns:
        List of Document objects ready for chunking.
    """
    docs_path = Path(docs_dir or config.docs_dir)

    if not docs_path.exists():
        raise FileNotFoundError(
            f"docs_dir not found: {docs_path}\n"
            f"Run the scraper first: python knowledge_base/scraper.py"
        )

    txt_files = sorted(docs_path.glob("*.txt"))
    if not txt_files:
        raise ValueError(
            f"No .txt files found in {docs_path}.\n"
            f"Run: python knowledge_base/scraper.py"
        )

    log.info(f"Loading {len(txt_files)} document(s) from {docs_path}")

    documents: list[Document] = []
    skipped = 0

    for path in txt_files:
        try:
            raw = path.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            log.warning(f"  Cannot read {path.name}: {e} — skipping")
            skipped += 1
            continue

        if not raw.strip():
            log.warning(f"  {path.name} is empty — skipping")
            skipped += 1
            continue

        meta, body = parse_frontmatter(raw)

        # Always include filename so we can trace any chunk back to its source
        meta["source_file"] = path.name
        meta.setdefault("title", path.stem.replace("_", " ").title())
        meta.setdefault("category", "general")

        word_count = len(body.split())
        if word_count < 50:
            log.warning(
                f"  {path.name}: only {word_count} words after frontmatter strip — "
                f"still loading but may produce poor chunks"
            )

        documents.append(Document(page_content=body, metadata=meta))
        log.info(
            f"  Loaded  {path.name:<45} "
            f"{word_count:>6,} words  |  "
            f"category={meta.get('category','?')}"
        )

    log.info(
        f"\nLoad complete: {len(documents)} loaded, {skipped} skipped."
    )
    return documents


# ─────────────────────────────────────────────────────────────────────────────
# 3. CHUNKER
# ─────────────────────────────────────────────────────────────────────────────

def chunk_documents(documents: list[Document]) -> list[Document]:
    """
    Split documents into overlapping chunks suitable for RAG retrieval.

    Strategy:
    - chunk_size=800 chars  (≈ 150-200 tokens, fits 6 chunks in a 4k context)
    - chunk_overlap=120 chars  (prevents cutting mid-provision)
    - Custom separators prioritise legal section dividers (===, ---) before
      falling back to paragraphs, sentences, and words.
    - Each chunk inherits all metadata from its parent document plus:
        chunk_index  — position within the parent document (0-based)
        total_chunks — total chunks from this document
        char_start   — character offset in original body

    Args:
        documents: output of load_documents()

    Returns:
        List of chunk Documents ready for embedding.
    """
    if not documents:
        raise ValueError("No documents to chunk. Run load_documents() first.")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=config.chunk_size,
        chunk_overlap=config.chunk_overlap,
        separators=_SEPARATORS,
        length_function=len,
        is_separator_regex=False,
        add_start_index=True,       # adds 'start_index' to metadata
    )

    all_chunks: list[Document] = []
    total_docs = len(documents)

    for doc_idx, doc in enumerate(documents):
        raw_chunks = splitter.split_documents([doc])

        # Enrich each chunk with positional metadata
        for chunk_idx, chunk in enumerate(raw_chunks):
            chunk.metadata["chunk_index"] = chunk_idx
            chunk.metadata["total_chunks"] = len(raw_chunks)
            # Clean up whitespace artifacts from splitting
            chunk.page_content = _clean_chunk(chunk.page_content)

        all_chunks.extend(raw_chunks)

        log.info(
            f"  Chunked [{doc_idx+1}/{total_docs}] "
            f"{doc.metadata.get('source_file','?'):<45} "
            f"→ {len(raw_chunks):>3} chunks"
        )

    log.info(
        f"\nChunking complete: {len(all_chunks)} total chunks "
        f"from {len(documents)} documents.\n"
        f"Avg chunks/doc: {len(all_chunks)/len(documents):.1f}"
    )
    return all_chunks


def _clean_chunk(text: str) -> str:
    """Remove leading/trailing divider lines and collapse excess whitespace."""
    # Strip leading/trailing === and --- lines
    lines = text.split("\n")
    lines = [l for l in lines if not re.match(r"^[=\-]{10,}\s*$", l)]
    # Collapse 3+ blank lines to 2
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# ─────────────────────────────────────────────────────────────────────────────
# 4. EMBEDDER + VECTORSTORE BUILDER
# ─────────────────────────────────────────────────────────────────────────────

def _get_embeddings() -> HuggingFaceEmbeddings:
    """Load the embedding model (cached after first call by HuggingFace)."""
    log.info(f"Loading embedding model: {config.embed_model}")
    return HuggingFaceEmbeddings(
        model_name=config.embed_model,
        model_kwargs={"device": "cpu"},
        encode_kwargs={
            "normalize_embeddings": True,   # cosine similarity works correctly
            "batch_size": 32,
        },
    )


def build_vectorstore(
    chunks: Optional[list[Document]] = None,
    docs_dir: Optional[str] = None,
    force_rebuild: bool = False,
) -> Chroma:
    """
    Embed chunks and persist them to ChromaDB.

    If chroma_store already exists and force_rebuild=False, skips ingestion
    and returns the existing store (fast path for app startup).

    Args:
        chunks:        Pre-computed chunks (optional — will load+chunk if None).
        docs_dir:      Override docs directory (optional).
        force_rebuild: Delete existing store and rebuild from scratch.

    Returns:
        Chroma vectorstore instance.
    """
    store_path = Path(config.chroma_persist_dir)

    # ── Fast path: store already exists ──────────────────────────────────────
    if store_path.exists() and not force_rebuild:
        existing = get_vectorstore()
        count = existing._collection.count()
        if count > 0:
            log.info(
                f"ChromaDB already exists at {store_path} "
                f"({count} vectors). Use force_rebuild=True to re-ingest."
            )
            return existing
        else:
            log.warning("ChromaDB exists but is empty — rebuilding.")

    # ── Load and chunk if not provided ────────────────────────────────────────
    if chunks is None:
        documents = load_documents(docs_dir)
        chunks = chunk_documents(documents)

    if not chunks:
        raise ValueError("No chunks to embed. Check your docs directory.")

    # ── Delete existing store if rebuilding ───────────────────────────────────
    if store_path.exists() and force_rebuild:
        import shutil
        log.info(f"Deleting existing ChromaDB at {store_path}...")
        shutil.rmtree(store_path)

    # ── Embed and persist ─────────────────────────────────────────────────────
    embeddings = _get_embeddings()

    log.info(f"Embedding {len(chunks)} chunks — this may take 1-3 minutes...")

    # Batch in groups of 100 to show progress and avoid memory spikes
    batch_size = 100
    vectorstore = None

    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        batch_num = i // batch_size + 1
        total_batches = (len(chunks) + batch_size - 1) // batch_size

        log.info(f"  Batch {batch_num}/{total_batches}  ({len(batch)} chunks)...")

        if vectorstore is None:
            # First batch — create the collection
            vectorstore = Chroma.from_documents(
                documents=batch,
                embedding=embeddings,
                persist_directory=str(store_path),
                collection_name=config.collection_name,
            )
        else:
            # Subsequent batches — add to existing collection
            vectorstore.add_documents(batch)

    final_count = vectorstore._collection.count()
    log.info(
        f"\nVectorStore built successfully.\n"
        f"  Location  : {store_path}\n"
        f"  Collection: {config.collection_name}\n"
        f"  Vectors   : {final_count:,}\n"
    )

    return vectorstore


# ─────────────────────────────────────────────────────────────────────────────
# 5. RUNTIME LOADER (used by graph/nodes.py)
# ─────────────────────────────────────────────────────────────────────────────

def get_vectorstore() -> Chroma:
    """
    Load the persisted ChromaDB vectorstore for query-time retrieval.

    Call this in graph/nodes.py — it does NOT re-embed anything.
    Raises FileNotFoundError if the store doesn't exist yet.
    """
    store_path = Path(config.chroma_persist_dir)

    if not store_path.exists():
        raise FileNotFoundError(
            f"ChromaDB not found at {store_path}.\n"
            f"Run first: python -m knowledge_base.ingest"
        )

    embeddings = _get_embeddings()

    vectorstore = Chroma(
        persist_directory=str(store_path),
        embedding_function=embeddings,
        collection_name=config.collection_name,
    )

    count = vectorstore._collection.count()
    log.info(f"Loaded ChromaDB: {count:,} vectors from {store_path}")
    return vectorstore


# ─────────────────────────────────────────────────────────────────────────────
# 6. INSPECTION UTILITIES
# ─────────────────────────────────────────────────────────────────────────────

def inspect_vectorstore(vectorstore: Optional[Chroma] = None) -> None:
    """
    Print a summary of what's stored in ChromaDB.
    Useful for debugging and verifying ingestion quality.
    """
    vs = vectorstore or get_vectorstore()
    collection = vs._collection
    count = collection.count()

    log.info(f"\n{'='*60}")
    log.info(f"ChromaDB Inspection — collection: {config.collection_name}")
    log.info(f"Total vectors: {count:,}")

    if count == 0:
        log.warning("Collection is empty.")
        return

    # Fetch a sample to show metadata distribution
    sample = collection.get(limit=min(count, 500), include=["metadatas"])
    metadatas = sample.get("metadatas", [])

    # Count docs per source_file
    from collections import Counter
    file_counts = Counter(m.get("source_file", "unknown") for m in metadatas)
    cat_counts  = Counter(m.get("category",    "unknown") for m in metadatas)

    log.info(f"\nChunks per source file (sample of {len(metadatas)}):")
    for fname, cnt in sorted(file_counts.items()):
        log.info(f"  {fname:<50} {cnt:>4} chunks")

    log.info(f"\nChunks per category:")
    for cat, cnt in sorted(cat_counts.items()):
        log.info(f"  {cat:<30} {cnt:>4} chunks")

    log.info(f"\n{'='*60}")


def test_retrieval(
    query: str = "What is IPC Section 302?",
    k: int = 3,
    vectorstore: Optional[Chroma] = None,
) -> None:
    """
    Run a test retrieval query and print the results.
    Use this to verify the RAG pipeline is working correctly.
    """
    vs = vectorstore or get_vectorstore()

    log.info(f"\nTest retrieval — query: '{query}'")
    retriever = vs.as_retriever(
        search_type="mmr",
        search_kwargs={
            "k": k,
            "fetch_k": k * 2,
            "lambda_mult": config.mmr_lambda,
        },
    )
    results = retriever.invoke(query)

    log.info(f"Retrieved {len(results)} chunks:")
    for i, doc in enumerate(results, 1):
        meta = doc.metadata
        preview = doc.page_content[:200].replace("\n", " ")
        log.info(
            f"\n  [{i}] {meta.get('source_file','?')}  "
            f"(chunk {meta.get('chunk_index','?')} of {meta.get('total_chunks','?')})\n"
            f"      Title   : {meta.get('title','?')[:60]}\n"
            f"      Category: {meta.get('category','?')}\n"
            f"      Preview : {preview}..."
        )


# ─────────────────────────────────────────────────────────────────────────────
# 7. CLI ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="LexAssist AI — Knowledge base ingestion pipeline"
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Force rebuild ChromaDB even if it already exists",
    )
    parser.add_argument(
        "--inspect",
        action="store_true",
        help="Inspect the existing ChromaDB without re-ingesting",
    )
    parser.add_argument(
        "--test-query",
        type=str,
        default=None,
        metavar="QUERY",
        help="Run a test MMR retrieval query after ingestion",
    )
    parser.add_argument(
        "--docs-dir",
        type=str,
        default=None,
        help="Override docs directory path",
    )
    args = parser.parse_args()

    log.info("=" * 60)
    log.info("LexAssist AI — Knowledge Base Ingestion")
    log.info("=" * 60)

    if args.inspect:
        inspect_vectorstore()
        return

    # ── Run full pipeline ─────────────────────────────────────────────────────
    documents = load_documents(args.docs_dir)
    chunks    = chunk_documents(documents)
    vs        = build_vectorstore(chunks=chunks, force_rebuild=args.rebuild)

    # ── Post-ingestion inspection ─────────────────────────────────────────────
    inspect_vectorstore(vs)

    # ── Optional test retrieval ───────────────────────────────────────────────
    if args.test_query:
        test_retrieval(query=args.test_query, vectorstore=vs)
    else:
        # Always run a default test so the user sees it's working
        test_retrieval(vectorstore=vs)

    log.info("\nIngestion complete. Next step: Build chunk 6 (graph/state.py)")


if __name__ == "__main__":
    main()
