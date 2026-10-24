"""Unit tests for canonical chunk-order transforms."""

from __future__ import annotations

from hashlib import sha256

import pytest

from contextweave.trace_analysis.chunk_order import (
    build_doc_frequency,
    natural_doc_key,
    reorder_chunks,
)


def _row(docs: list[str], chunks: list[list[int]] | None = None) -> dict:
    chunks = chunks or [[i, i] for i in range(len(docs))]
    prefix = [100]
    query = [200]
    token_ids = prefix + [t for c in chunks for t in c] + query
    return {
        "document_ids": docs,
        "chunk_token_ids": chunks,
        "chunk_lengths": [len(c) for c in chunks],
        "prefix_token_ids": prefix,
        "query_token_ids": query,
        "token_ids": token_ids,
        "segments_canonical": True,
    }


def test_natural_sort_chunk_2_before_10():
    assert natural_doc_key("doc::chunk-2") < natural_doc_key("doc::chunk-10")


def test_by_doc_id_natural_sort():
    row = _row(["z::chunk-10", "a::chunk-2", "a::chunk-10"])
    out = reorder_chunks(row, "by_doc_id")
    assert out["document_ids"] == ["a::chunk-2", "a::chunk-10", "z::chunk-10"]
    assert len(out["token_ids"]) == len(row["token_ids"])
    assert out["prefix_token_ids"] == [100]
    assert out["query_token_ids"] == [200]


def test_by_sha256_differs_from_alpha_on_zipf_ids():
    docs = [f"doc-{i:04d}" for i in range(5)]
    row = _row(docs)
    alpha = reorder_chunks(row, "by_doc_id")["document_ids"]
    hashed = reorder_chunks(row, "by_sha256_doc_id")["document_ids"]
    assert alpha == docs  # already alpha
    # sha256 order should not match alpha for this set (extremely likely)
    expected = sorted(docs, key=lambda d: sha256(d.encode()).hexdigest())
    assert hashed == expected
    assert hashed != alpha


def test_by_frequency_desc_hot_first():
    rows = [
        _row(["rare", "hot"]),
        _row(["hot", "other"]),
        _row(["hot"]),
    ]
    freq = build_doc_frequency(rows)
    assert freq["hot"] == 3
    out = reorder_chunks(rows[0], "by_frequency_desc", freq=freq)
    assert out["document_ids"][0] == "hot"


def test_natural_noop_same_object_ok():
    row = _row(["b", "a"])
    out = reorder_chunks(row, "natural")
    assert out is row


def test_frequency_requires_map():
    with pytest.raises(ValueError, match="frequency"):
        reorder_chunks(_row(["a", "b"]), "by_frequency_desc")


def test_duplicate_ids_stable():
    row = _row(["same", "same"], [[1], [2]])
    out = reorder_chunks(row, "by_doc_id")
    assert out["chunk_token_ids"] == [[1], [2]]
