"""Unit tests: lexical retrieve returns k."""

from __future__ import annotations

from pathlib import Path

from contextweave.product.rag_demo.index import build_index
from contextweave.product.rag_demo.retrieve import retrieve

REPO = Path(__file__).resolve().parents[2]
SAMPLE = REPO / "benchmarks" / "corpora" / "sample_docs"


def test_retrieve_returns_k():
    idx = build_index(SAMPLE, chunk_chars=1000, overlap=100)
    docs = retrieve(idx, "What is the SLA uptime target for Inference API?", k=3)
    assert len(docs) == 3
    assert all("document_id" in d and "content" in d for d in docs)
    # deterministic
    docs2 = retrieve(idx, "What is the SLA uptime target for Inference API?", k=3)
    assert [d["document_id"] for d in docs] == [d["document_id"] for d in docs2]


def test_retrieve_sla_hits_sla_doc():
    idx = build_index(SAMPLE, chunk_chars=1000, overlap=100)
    docs = retrieve(idx, "monthly uptime 99.9% Inference API SLA credits", k=3)
    ids = " ".join(d["document_id"] for d in docs)
    assert "sla_uptime" in ids
