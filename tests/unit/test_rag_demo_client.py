"""Unit tests: ask client builds cw_documents correctly."""

from __future__ import annotations

from contextweave.product.rag_demo.client import build_ask_body


def test_build_ask_body_includes_cw_fields():
    docs = [
        {"document_id": "a::chunk-000", "content": "alpha"},
        {"document_id": "b::chunk-000", "content": "beta"},
    ]
    body = build_ask_body(
        "What city?",
        docs,
        model="mistral",
        chunk_order="by_frequency_desc",
        system="Be brief.",
    )
    assert body["model"] == "mistral"
    assert body["cw_chunk_order"] == "by_frequency_desc"
    assert body["cw_documents"] == docs
    assert body["messages"][0]["role"] == "system"
    assert body["messages"][-1]["content"] == "What city?"
