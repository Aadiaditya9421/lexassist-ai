"""
tests/test_ingest.py — Unit tests for knowledge_base/ingest.py
Run: pytest tests/test_ingest.py -v
"""

import pytest
from pathlib import Path
from langchain_core.documents import Document
from knowledge_base.ingest import (
    parse_frontmatter,
    load_documents,
    chunk_documents,
    _clean_chunk,
)


# ── parse_frontmatter ─────────────────────────────────────────────────────────

VALID_DOC = """---
title: Indian Penal Code Test
category: criminal_law
source: Government of India
year: 1860
---

Section 1 — This is the body of the legal document.
It contains multiple paragraphs about legal provisions."""

def test_parse_frontmatter_returns_metadata():
    meta, body = parse_frontmatter(VALID_DOC)
    assert meta["title"] == "Indian Penal Code Test"
    assert meta["category"] == "criminal_law"
    assert meta["year"] == 1860

def test_parse_frontmatter_returns_body():
    meta, body = parse_frontmatter(VALID_DOC)
    assert "Section 1" in body
    assert "---" not in body

def test_parse_frontmatter_no_yaml():
    meta, body = parse_frontmatter("Just plain text with no frontmatter.")
    assert meta == {}
    assert "plain text" in body

def test_parse_frontmatter_missing_closing_delimiter():
    bad = "---\ntitle: broken\nno closing delimiter here"
    meta, body = parse_frontmatter(bad)
    # Should not crash — returns empty or partial
    assert isinstance(meta, dict)
    assert isinstance(body, str)

def test_parse_frontmatter_coerces_all_values_to_primitives():
    doc = "---\ntitle: Test\ncategory: law\nyear: 1860\nlist_field: [a, b, c]\n---\nBody"
    meta, body = parse_frontmatter(doc)
    # list_field should be coerced to string for ChromaDB compatibility
    if "list_field" in meta:
        assert isinstance(meta["list_field"], str)

def test_parse_frontmatter_empty_body():
    doc = "---\ntitle: Test\ncategory: law\nsource: Govt\nyear: 2000\n---\n"
    meta, body = parse_frontmatter(doc)
    assert meta["title"] == "Test"
    assert body == ""

def test_parse_frontmatter_source_file_not_in_meta():
    """source_file is added by load_documents, not parse_frontmatter."""
    meta, _ = parse_frontmatter(VALID_DOC)
    assert "source_file" not in meta


# ── _clean_chunk ─────────────────────────────────────────────────────────────

def test_clean_chunk_removes_divider_lines():
    text = "=" * 80 + "\nSection 1 text\n" + "-" * 80
    result = _clean_chunk(text)
    assert "=" * 10 not in result
    assert "-" * 10 not in result
    assert "Section 1 text" in result

def test_clean_chunk_collapses_blank_lines():
    text = "Line 1\n\n\n\n\nLine 2"
    result = _clean_chunk(text)
    assert "\n\n\n" not in result

def test_clean_chunk_strips_whitespace():
    text = "  \n  Section text  \n  "
    result = _clean_chunk(text)
    assert result == result.strip()

def test_clean_chunk_preserves_content():
    text = "Section 302 — Punishment for murder.\nWhoever commits murder shall be punished."
    result = _clean_chunk(text)
    assert "Section 302" in result
    assert "murder" in result


# ── load_documents ────────────────────────────────────────────────────────────

def test_load_documents_raises_on_missing_dir():
    with pytest.raises(FileNotFoundError):
        load_documents("/this/path/does/not/exist")

def test_load_documents_raises_on_empty_dir(tmp_path):
    with pytest.raises(ValueError, match="No .txt files"):
        load_documents(str(tmp_path))

def test_load_documents_returns_documents(tmp_path):
    (tmp_path / "test_act.txt").write_text(VALID_DOC, encoding="utf-8")
    docs = load_documents(str(tmp_path))
    assert len(docs) == 1
    assert isinstance(docs[0], Document)

def test_load_documents_metadata_includes_source_file(tmp_path):
    (tmp_path / "test_act.txt").write_text(VALID_DOC, encoding="utf-8")
    docs = load_documents(str(tmp_path))
    assert docs[0].metadata["source_file"] == "test_act.txt"

def test_load_documents_metadata_from_frontmatter(tmp_path):
    (tmp_path / "ipc.txt").write_text(VALID_DOC, encoding="utf-8")
    docs = load_documents(str(tmp_path))
    assert docs[0].metadata["category"] == "criminal_law"
    assert docs[0].metadata["year"] == 1860

def test_load_documents_skips_empty_files(tmp_path):
    (tmp_path / "empty.txt").write_text("   \n  ", encoding="utf-8")
    (tmp_path / "valid.txt").write_text(VALID_DOC, encoding="utf-8")
    docs = load_documents(str(tmp_path))
    assert len(docs) == 1   # empty file skipped

def test_load_documents_no_frontmatter_still_loads(tmp_path):
    plain = "Section 1 — This is plain text without any YAML frontmatter."
    (tmp_path / "plain.txt").write_text(plain, encoding="utf-8")
    docs = load_documents(str(tmp_path))
    assert len(docs) == 1
    assert docs[0].metadata["category"] == "general"   # default


# ── chunk_documents ───────────────────────────────────────────────────────────

def _make_doc(content: str, meta: dict = None) -> Document:
    return Document(
        page_content=content,
        metadata=meta or {"source_file": "test.txt", "category": "test"},
    )

def test_chunk_documents_raises_on_empty_list():
    with pytest.raises(ValueError, match="No documents"):
        chunk_documents([])

def test_chunk_documents_returns_list_of_documents():
    doc = _make_doc("Section 1. " * 200)   # long enough to produce multiple chunks
    chunks = chunk_documents([doc])
    assert isinstance(chunks, list)
    assert all(isinstance(c, Document) for c in chunks)

def test_chunk_documents_inherits_metadata():
    doc = _make_doc("Section 1. " * 200, meta={"source_file": "ipc.txt", "category": "criminal_law"})
    chunks = chunk_documents([doc])
    for chunk in chunks:
        assert chunk.metadata["source_file"] == "ipc.txt"
        assert chunk.metadata["category"] == "criminal_law"

def test_chunk_documents_adds_chunk_index():
    doc = _make_doc("Section 1. " * 200)
    chunks = chunk_documents([doc])
    assert "chunk_index" in chunks[0].metadata
    assert chunks[0].metadata["chunk_index"] == 0

def test_chunk_documents_adds_total_chunks():
    doc = _make_doc("Section 1. " * 200)
    chunks = chunk_documents([doc])
    expected_total = len(chunks)
    for chunk in chunks:
        assert chunk.metadata["total_chunks"] == expected_total

def test_chunk_documents_chunk_size_respected():
    doc = _make_doc("Section 1. " * 300)
    chunks = chunk_documents([doc])
    # Allow 10% tolerance above chunk_size for boundary cases
    from config import config
    for chunk in chunks:
        assert len(chunk.page_content) <= config.chunk_size * 1.1, (
            f"Chunk too large: {len(chunk.page_content)} chars"
        )

def test_chunk_documents_multiple_docs():
    docs = [
        _make_doc("Section 1. " * 100, {"source_file": "a.txt", "category": "law"}),
        _make_doc("Section 2. " * 100, {"source_file": "b.txt", "category": "law"}),
    ]
    chunks = chunk_documents(docs)
    sources = {c.metadata["source_file"] for c in chunks}
    assert "a.txt" in sources
    assert "b.txt" in sources

def test_chunk_content_is_non_empty():
    doc = _make_doc("Legal provision text. " * 50)
    chunks = chunk_documents([doc])
    for chunk in chunks:
        assert chunk.page_content.strip() != ""
