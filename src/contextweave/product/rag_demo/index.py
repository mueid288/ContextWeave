"""Lexical index: JSONL chunks + inverted term postings (stdlib only)."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import json
import math
import re
from pathlib import Path

from contextweave.product.rag_demo.chunk import Chunk, chunk_corpus

_TOKEN_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)


def tokenize(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text)]


@dataclass
class LexicalIndex:
    chunks: list[Chunk]
    # term -> list of (chunk_idx, tf)
    postings: dict[str, list[tuple[int, int]]]
    doc_lens: list[int]
    avgdl: float
    meta: dict

    def __len__(self) -> int:
        return len(self.chunks)


def _build_postings(chunks: list[Chunk]) -> tuple[dict[str, list[tuple[int, int]]], list[int], float]:
    postings: dict[str, list[tuple[int, int]]] = defaultdict(list)
    doc_lens: list[int] = []
    for i, ch in enumerate(chunks):
        toks = tokenize(ch.content)
        doc_lens.append(len(toks))
        tf: dict[str, int] = defaultdict(int)
        for t in toks:
            tf[t] += 1
        for term, count in tf.items():
            postings[term].append((i, count))
    avgdl = (sum(doc_lens) / len(doc_lens)) if doc_lens else 0.0
    return dict(postings), doc_lens, avgdl


def build_index(
    corpus_dir: Path,
    *,
    chunk_chars: int = 1000,
    overlap: int = 100,
) -> LexicalIndex:
    chunks = chunk_corpus(corpus_dir, chunk_chars=chunk_chars, overlap=overlap)
    postings, doc_lens, avgdl = _build_postings(chunks)
    return LexicalIndex(
        chunks=chunks,
        postings=postings,
        doc_lens=doc_lens,
        avgdl=avgdl,
        meta={
            "corpus_dir": str(corpus_dir),
            "chunk_chars": chunk_chars,
            "overlap": overlap,
            "n_chunks": len(chunks),
        },
    )


def save_index(index: LexicalIndex, out_dir: Path) -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    chunks_path = out_dir / "chunks.jsonl"
    with chunks_path.open("w", encoding="utf-8") as f:
        for ch in index.chunks:
            f.write(json.dumps(ch.to_dict(), ensure_ascii=False) + "\n")
    meta = {
        **index.meta,
        "avgdl": index.avgdl,
        "doc_lens": index.doc_lens,
        "postings": {
            term: [[i, tf] for i, tf in posting]
            for term, posting in index.postings.items()
        },
    }
    (out_dir / "meta.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    return chunks_path


def load_index(index_dir: Path) -> LexicalIndex:
    index_dir = Path(index_dir)
    chunks: list[Chunk] = []
    with (index_dir / "chunks.jsonl").open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                chunks.append(Chunk.from_dict(json.loads(line)))
    meta = json.loads((index_dir / "meta.json").read_text(encoding="utf-8"))
    raw_postings = meta.get("postings") or {}
    postings = {
        term: [(int(i), int(tf)) for i, tf in pairs]
        for term, pairs in raw_postings.items()
    }
    doc_lens = [int(x) for x in (meta.get("doc_lens") or [0] * len(chunks))]
    avgdl = float(meta.get("avgdl") or 0.0)
    keep = {k: v for k, v in meta.items() if k not in ("postings", "doc_lens", "avgdl")}
    return LexicalIndex(
        chunks=chunks,
        postings=postings,
        doc_lens=doc_lens,
        avgdl=avgdl,
        meta=keep,
    )


def bm25_scores(
    index: LexicalIndex,
    query: str,
    *,
    k1: float = 1.5,
    b: float = 0.75,
) -> list[float]:
    """Okapi BM25 scores for every chunk (deterministic)."""
    q_terms = tokenize(query)
    n = len(index.chunks)
    scores = [0.0] * n
    if n == 0 or not q_terms:
        return scores
    avgdl = index.avgdl or 1.0
    # unique query terms preserve first-seen order for stability
    seen: set[str] = set()
    uniq: list[str] = []
    for t in q_terms:
        if t not in seen:
            seen.add(t)
            uniq.append(t)
    for term in uniq:
        posting = index.postings.get(term)
        if not posting:
            continue
        df = len(posting)
        idf = math.log(1.0 + (n - df + 0.5) / (df + 0.5))
        for doc_i, tf in posting:
            dl = index.doc_lens[doc_i] or 1
            denom = tf + k1 * (1.0 - b + b * dl / avgdl)
            scores[doc_i] += idf * (tf * (k1 + 1.0) / denom)
    return scores


def ensure_index(
    corpus_dir: Path,
    index_dir: Path,
    *,
    rebuild: bool = False,
    chunk_chars: int = 1000,
    overlap: int = 100,
) -> LexicalIndex:
    index_dir = Path(index_dir)
    meta_path = index_dir / "meta.json"
    chunks_path = index_dir / "chunks.jsonl"
    if (
        not rebuild
        and meta_path.is_file()
        and chunks_path.is_file()
    ):
        idx = load_index(index_dir)
        if idx.meta.get("corpus_dir") == str(corpus_dir):
            return idx
    idx = build_index(corpus_dir, chunk_chars=chunk_chars, overlap=overlap)
    save_index(idx, index_dir)
    return idx
