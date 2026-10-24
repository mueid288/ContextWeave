"""Top-k lexical retrieval over a frozen index."""

from __future__ import annotations

from contextweave.product.rag_demo.chunk import Chunk
from contextweave.product.rag_demo.index import LexicalIndex, bm25_scores


def retrieve(
    index: LexicalIndex,
    question: str,
    *,
    k: int = 3,
) -> list[dict[str, str]]:
    """
    Return top-k ``{document_id, content}`` dicts.

    Deterministic: BM25 score desc, then document_id asc for ties.
    """
    if k <= 0 or not index.chunks:
        return []
    scores = bm25_scores(index, question)
    ranked = sorted(
        range(len(index.chunks)),
        key=lambda i: (-scores[i], index.chunks[i].document_id),
    )
    out: list[dict[str, str]] = []
    for i in ranked[:k]:
        ch: Chunk = index.chunks[i]
        out.append({"document_id": ch.document_id, "content": ch.content})
    return out
