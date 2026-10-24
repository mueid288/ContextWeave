"""Unit tests: chunker document ids."""

from __future__ import annotations

from contextweave.product.rag_demo.chunk import chunk_text, make_document_id


def test_make_document_id_zero_padded():
    assert make_document_id("api_authentication", 0) == "api_authentication::chunk-000"
    assert make_document_id("api_authentication", 12) == "api_authentication::chunk-012"


def test_chunk_text_overlap_and_ids():
    text = "A" * 2500
    chunks = chunk_text(text, stem="doc", chunk_chars=1000, overlap=100)
    assert len(chunks) >= 3
    assert chunks[0].document_id == "doc::chunk-000"
    assert chunks[1].document_id == "doc::chunk-001"
    # overlap: second starts 100 chars before first ends
    assert chunks[1].char_start == chunks[0].char_end - 100
