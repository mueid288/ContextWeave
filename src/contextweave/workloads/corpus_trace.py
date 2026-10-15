"""Build partner_v1 traces from a local document corpus (Path C).

CPU-only. No model tokenizer — token_count ≈ ceil(chars / chars_per_token).
G0 from this path is provisional (corpus-backed replay, not a serving log).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Any, Iterator
import hashlib
import json
import math
import random
import re

from contextweave.tokenization.boundaries import ChunkingConfig, pad_token_count_to_block
from contextweave.workloads._common import _zipf_weights, approx_token_count


TEXT_SUFFIXES = {".md", ".txt", ".markdown", ".rst"}


@dataclass
class CorpusChunk:
    document_id: str
    source_path: str
    chunk_index: int
    text: str
    content_hash: str
    token_count: int

    def partner_chunk(self) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "content_hash": self.content_hash,
            "token_count": self.token_count,
        }


@dataclass
class CorpusTraceConfig:
    name: str = "corpus_replay_default"
    seed: int = 42
    num_requests: int = 300
    chars_per_token: float = 4.0
    # Chunking
    chunk_chars_target: int = 3200  # ~800 tokens at 4 chars/token
    chunk_chars_min: int = 2048  # ~512 tokens
    chunk_chars_max: int = 8192
    # Request mix
    synthesis_fraction: float = 0.45
    docs_per_request_min: int = 1
    docs_per_request_max: int = 4
    shared_prefix_fraction: float = 0.9
    prefix_token_count: int = 256
    query_tokens_min: int = 24
    query_tokens_max: int = 96
    popularity_alpha: float = 1.05
    reuse_distance_max: int = 40
    # File discovery
    recursive: bool = True
    # v2.1: pad chunk token counts to KV block size (boundary appended first)
    kv_block_size: int = 16
    pad_to_block: bool = True
    # Gemini_2 §1.2: off by default — short docs must fail G0 honestly
    pad_short_docs_for_demo: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CorpusTraceConfig":
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in known})

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def chunking_config(self) -> ChunkingConfig:
        return ChunkingConfig(
            chunking_config_id="corpus_boundary_v1",
            kv_block_size=self.kv_block_size,
            pad_to_block=self.pad_to_block,
            chars_per_token=self.chars_per_token,
        )


def content_hash(text: str) -> str:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def _normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def discover_documents(corpus_dir: Path, *, recursive: bool = True) -> list[Path]:
    if not corpus_dir.is_dir():
        raise FileNotFoundError(f"Corpus directory not found: {corpus_dir}")
    pattern = "**/*" if recursive else "*"
    files = [
        p
        for p in sorted(corpus_dir.glob(pattern))
        if p.is_file() and p.suffix.lower() in TEXT_SUFFIXES and not p.name.startswith(".")
    ]
    if not files:
        raise FileNotFoundError(
            f"No {sorted(TEXT_SUFFIXES)} files under {corpus_dir}. "
            "Add .md/.txt docs or use benchmarks/corpora/sample_docs."
        )
    return files


def _split_paragraphs(text: str) -> list[str]:
    parts = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    return parts or [text]


def chunk_document(
    path: Path,
    *,
    chars_per_token: float,
    chunk_chars_target: int,
    chunk_chars_min: int,
    chunk_chars_max: int,
    pad_short_docs_for_demo: bool = False,
) -> list[CorpusChunk]:
    raw = _normalize_text(path.read_text(encoding="utf-8"))
    if not raw:
        return []
    paragraphs = _split_paragraphs(raw)
    doc_stem = path.stem
    chunks: list[CorpusChunk] = []
    buf: list[str] = []
    buf_len = 0
    idx = 0

    def flush() -> None:
        nonlocal buf, buf_len, idx
        if not buf:
            return
        body = "\n\n".join(buf).strip()
        if len(body) < chunk_chars_min and chunks:
            # Merge undersized tail into previous chunk when possible.
            prev = chunks[-1]
            merged = prev.text + "\n\n" + body
            if len(merged) <= chunk_chars_max:
                chunks[-1] = CorpusChunk(
                    document_id=prev.document_id,
                    source_path=prev.source_path,
                    chunk_index=prev.chunk_index,
                    text=merged,
                    content_hash=content_hash(merged),
                    token_count=approx_token_count(merged, chars_per_token),
                )
                buf, buf_len = [], 0
                return
        if len(body) < chunk_chars_min and pad_short_docs_for_demo:
            # Explicit demo-only padding — never silent (Gemini_2 §1.2).
            pad_unit = (
                f"\n\n[contextweave-pad] Additional reference material for {doc_stem}, "
                f"section {idx}. " + ("Details follow. " * 40)
            )
            while len(body) < chunk_chars_min:
                body += pad_unit
            body = body[:chunk_chars_max]
        doc_id = f"{doc_stem}::chunk-{idx:03d}"
        n_tok = approx_token_count(body, chars_per_token)
        chunks.append(
            CorpusChunk(
                document_id=doc_id,
                source_path=str(path),
                chunk_index=idx,
                text=body,
                content_hash=content_hash(body),
                token_count=n_tok,
            )
        )
        idx += 1
        buf, buf_len = [], 0

    for para in paragraphs:
        # Hard-split oversized paragraphs.
        while len(para) > chunk_chars_max:
            piece = para[:chunk_chars_max]
            para = para[chunk_chars_max:]
            if buf_len and buf_len + len(piece) + 2 > chunk_chars_max:
                flush()
            buf.append(piece)
            buf_len += len(piece) + 2
            flush()
        if buf_len and buf_len + len(para) + 2 > chunk_chars_target:
            flush()
        buf.append(para)
        buf_len += len(para) + 2
    flush()
    return chunks


def build_corpus_index(corpus_dir: Path, cfg: CorpusTraceConfig) -> list[CorpusChunk]:
    files = discover_documents(corpus_dir, recursive=cfg.recursive)
    chunks: list[CorpusChunk] = []
    for path in files:
        chunks.extend(
            chunk_document(
                path,
                chars_per_token=cfg.chars_per_token,
                chunk_chars_target=cfg.chunk_chars_target,
                chunk_chars_min=cfg.chunk_chars_min,
                chunk_chars_max=cfg.chunk_chars_max,
                pad_short_docs_for_demo=cfg.pad_short_docs_for_demo,
            )
        )
    if not chunks:
        raise RuntimeError(f"No non-empty chunks produced from {corpus_dir}")
    if cfg.pad_to_block:
        # Boundary tokens are part of the cached segment *before* block padding
        # (Gemini_3 §1.1). Import/assembly treat token_count as the full segment.
        boundary_len = len(cfg.chunking_config().boundary_token_ids)
        padded: list[CorpusChunk] = []
        for c in chunks:
            n = pad_token_count_to_block(c.token_count + boundary_len, cfg.kv_block_size)
            padded.append(
                CorpusChunk(
                    document_id=c.document_id,
                    source_path=c.source_path,
                    chunk_index=c.chunk_index,
                    text=c.text,
                    content_hash=c.content_hash,
                    token_count=n,
                )
            )
        return padded
    return chunks


def generate_partner_requests(
    chunks: list[CorpusChunk],
    cfg: CorpusTraceConfig,
) -> Iterator[dict[str, Any]]:
    rng = random.Random(cfg.seed)
    weights = _zipf_weights(len(chunks), cfg.popularity_alpha)
    ids = list(range(len(chunks)))
    recent: list[int] = []
    # Prefix segment includes trailing boundary then pad (Gemini_3 §1.1).
    boundary_len = len(cfg.chunking_config().boundary_token_ids)
    prefix_len = (
        pad_token_count_to_block(cfg.prefix_token_count + boundary_len, cfg.kv_block_size)
        if cfg.pad_to_block
        else cfg.prefix_token_count
    )
    prefix_a = list(range(10, 10 + prefix_len))
    prefix_b = list(range(10_000, 10_000 + prefix_len))

    for i in range(cfg.num_requests):
        is_synthesis = rng.random() < cfg.synthesis_fraction
        if is_synthesis:
            lo = max(2, cfg.docs_per_request_min)
            hi = max(lo, cfg.docs_per_request_max)
            n_docs = rng.randint(lo, hi)
            query_type = "synthesis"
        else:
            n_docs = 1
            query_type = "lookup"

        n_docs = min(n_docs, len(ids))
        chosen: list[int] = []
        for _ in range(n_docs):
            if recent and rng.random() < 0.55:
                window = recent[-cfg.reuse_distance_max :] if cfg.reuse_distance_max > 0 else []
                cand = rng.choice(window) if window else rng.choices(ids, weights=weights, k=1)[0]
            else:
                cand = rng.choices(ids, weights=weights, k=1)[0]
            attempts = 0
            while cand in chosen:
                if attempts >= 8:
                    remaining = [d for d in ids if d not in chosen]
                    if not remaining:
                        cand = None
                        break
                    cand = rng.choice(remaining)
                    break
                cand = rng.choices(ids, weights=weights, k=1)[0]
                attempts += 1
            if cand is None or cand in chosen:
                break
            chosen.append(cand)
            recent.append(cand)

        rng.shuffle(chosen)
        selected = [chunks[j] for j in chosen]
        prefix = prefix_a if rng.random() < cfg.shared_prefix_fraction else prefix_b
        qlen = rng.randint(cfg.query_tokens_min, cfg.query_tokens_max)
        # Unique query ids per request (not recurring chunks).
        query = [50_000 + i * 200 + k for k in range(qlen)]

        yield {
            "request_id": f"corpus-{cfg.name}-{i:06d}",
            "query_type": query_type,
            "prefix_token_ids": prefix,
            "chunks": [c.partner_chunk() for c in selected],
            "query_token_ids": query,
            "timestamp": f"corpus-replay-{i:06d}",
            "source": "corpus_replay",
        }


def write_corpus_trace(
    corpus_dir: Path,
    out_dir: Path,
    cfg: CorpusTraceConfig,
) -> dict[str, Any]:
    chunks = build_corpus_index(corpus_dir, cfg)
    out_dir.mkdir(parents=True, exist_ok=True)
    partner_path = out_dir / "partner_v1.jsonl"
    catalog_path = out_dir / "chunk_catalog.json"
    config_path = out_dir / "config.json"
    meta_path = out_dir / "meta.json"

    with partner_path.open("w", encoding="utf-8") as fh:
        n = 0
        for row in generate_partner_requests(chunks, cfg):
            fh.write(json.dumps(row) + "\n")
            n += 1

    catalog = [
        {
            "document_id": c.document_id,
            "source_path": c.source_path,
            "chunk_index": c.chunk_index,
            "content_hash": c.content_hash,
            "token_count": c.token_count,
            "char_count": len(c.text),
        }
        for c in chunks
    ]
    catalog_path.write_text(json.dumps(catalog, indent=2) + "\n", encoding="utf-8")
    config_path.write_text(json.dumps(cfg.to_dict(), indent=2) + "\n", encoding="utf-8")
    meta = {
        "name": cfg.name,
        "corpus_dir": str(corpus_dir),
        "num_source_files": len({c.source_path for c in chunks}),
        "num_chunks": len(chunks),
        "num_requests": n,
        "partner_trace": str(partner_path),
        "provisional_g0": True,
        "path": "C",
        "notes": (
            "Corpus-backed replay (Path C). Real document text chunked locally; "
            "request mix is simulated. token_count uses chars/chars_per_token — "
            "not a model tokenizer. G0 remains provisional."
        ),
        "median_chunk_tokens": sorted(c.token_count for c in chunks)[len(chunks) // 2],
    }
    meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    return meta
