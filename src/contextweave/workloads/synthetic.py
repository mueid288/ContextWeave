"""CPU-only synthetic multi-document RAG request stream generator."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Any, Iterator
import json
import random

from contextweave.tokenization.boundaries import (
    ChunkingConfig,
    assemble_prompt_token_ids,
)
from contextweave.workloads._common import _zipf_weights


@dataclass
class SyntheticWorkloadConfig:
    """Controllable recurrence statistics for a provisional G0 workload."""

    name: str = "synthetic_rag_default"
    seed: int = 42
    num_requests: int = 500
    corpus_size: int = 80
    # Chunk length distribution (tokens), inclusive bounds.
    chunk_len_min: int = 256
    chunk_len_max: int = 4096
    chunk_len_median_target: int = 768
    # How many documents appear in a typical request.
    docs_per_request_min: int = 1
    docs_per_request_max: int = 4
    # Fraction of requests that are multi-document synthesis vs single-doc lookup.
    synthesis_fraction: float = 0.45
    # Shared system / instruction prefix length (tokens) — served by native prefix cache.
    system_prefix_tokens: int = 256
    # Probability a request reuses the same system prefix template id.
    shared_prefix_fraction: float = 0.85
    # Zipf-like popularity: higher => heavier head on hot docs.
    popularity_alpha: float = 1.1
    # Max reuse distance (requests) when sampling hot docs again.
    reuse_distance_max: int = 40
    # Query / instruction suffix after retrieved docs.
    query_tokens_min: int = 32
    query_tokens_max: int = 128
    # Token id vocabulary for synthetic token sequences (not a real tokenizer).
    vocab_size: int = 32_000
    # Reserved id ranges: 1..prefix for system templates, rest for docs/queries.
    num_prefix_templates: int = 3
    kv_block_size: int = 16
    pad_to_block: bool = True

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SyntheticWorkloadConfig":
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in known})

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def chunking_config(self) -> ChunkingConfig:
        return ChunkingConfig(
            chunking_config_id="synthetic_boundary_v1",
            kv_block_size=self.kv_block_size,
            pad_to_block=self.pad_to_block,
        )


@dataclass
class TraceRequest:
    request_id: str
    query_type: str  # "lookup" | "synthesis"
    prefix_template_id: int
    prefix_token_ids: list[int]
    document_ids: list[str]
    chunk_token_ids: list[list[int]]
    chunk_lengths: list[int]
    query_token_ids: list[int]
    # Full prompt token ids = prefix + concat(chunks) + query
    token_ids: list[int] = field(default_factory=list)

    def to_json(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "query_type": self.query_type,
            "prefix_template_id": self.prefix_template_id,
            "prefix_token_ids": self.prefix_token_ids,
            "document_ids": self.document_ids,
            "chunk_token_ids": self.chunk_token_ids,
            "chunk_lengths": self.chunk_lengths,
            "query_token_ids": self.query_token_ids,
            "token_ids": self.token_ids,
            "context_length": len(self.token_ids),
            "segments_canonical": True,
        }


def _sample_chunk_length(rng: random.Random, cfg: SyntheticWorkloadConfig) -> int:
    """Skew lengths so the sample median sits near the configured target."""
    # Mixture: 60% around median, 40% uniform across full range.
    if rng.random() < 0.6:
        lo = max(cfg.chunk_len_min, int(cfg.chunk_len_median_target * 0.7))
        hi = min(cfg.chunk_len_max, int(cfg.chunk_len_median_target * 1.4))
        if lo > hi:
            lo, hi = cfg.chunk_len_min, cfg.chunk_len_max
        return rng.randint(lo, hi)
    return rng.randint(cfg.chunk_len_min, cfg.chunk_len_max)


def _build_corpus(rng: random.Random, cfg: SyntheticWorkloadConfig) -> dict[str, list[int]]:
    corpus: dict[str, list[int]] = {}
    # Document tokens start above reserved prefix template space.
    base = cfg.num_prefix_templates * cfg.system_prefix_tokens + 100
    for i in range(cfg.corpus_size):
        length = _sample_chunk_length(rng, cfg)
        # Deterministic unique token stream per doc (stable across regenerations with same seed).
        start = base + i * (cfg.chunk_len_max + 16)
        token_ids = [start + j for j in range(length)]
        # Clamp into vocab for realism without collisions across docs.
        token_ids = [((t % (cfg.vocab_size - 1000)) + 1000) for t in token_ids]
        corpus[f"doc-{i:04d}"] = token_ids
    return corpus


def _build_prefix_templates(cfg: SyntheticWorkloadConfig) -> dict[int, list[int]]:
    templates: dict[int, list[int]] = {}
    for tid in range(cfg.num_prefix_templates):
        start = 10 + tid * cfg.system_prefix_tokens
        templates[tid] = list(range(start, start + cfg.system_prefix_tokens))
    return templates


def generate_trace(cfg: SyntheticWorkloadConfig) -> Iterator[TraceRequest]:
    """Yield synthetic requests with controllable recurrence and prefix sharing."""
    rng = random.Random(cfg.seed)
    corpus = _build_corpus(rng, cfg)
    prefixes = _build_prefix_templates(cfg)
    doc_ids = list(corpus.keys())
    weights = _zipf_weights(len(doc_ids), cfg.popularity_alpha)

    # Track recent doc picks for reuse-distance shaping.
    recent: list[str] = []

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

        n_docs = min(n_docs, len(doc_ids))
        chosen: list[str] = []
        # Prefer recent hot docs with some probability to create reuse distance structure.
        for _ in range(n_docs):
            if recent and rng.random() < 0.55:
                window = recent[-cfg.reuse_distance_max :] if cfg.reuse_distance_max > 0 else []
                cand = rng.choice(window) if window else rng.choices(doc_ids, weights=weights, k=1)[0]
            else:
                cand = rng.choices(doc_ids, weights=weights, k=1)[0]
            # Never allow duplicate docs inside one request (Gemini_2 §1.4).
            attempts = 0
            while cand in chosen:
                if attempts >= 8:
                    remaining = [d for d in doc_ids if d not in chosen]
                    if not remaining:
                        cand = None
                        break
                    cand = rng.choice(remaining)
                    break
                cand = rng.choices(doc_ids, weights=weights, k=1)[0]
                attempts += 1
            if cand is None or cand in chosen:
                break
            chosen.append(cand)
            recent.append(cand)

        if rng.random() < cfg.shared_prefix_fraction:
            prefix_tid = 0
        else:
            prefix_tid = rng.randint(0, cfg.num_prefix_templates - 1)
        prefix_ids = list(prefixes[prefix_tid])

        # Shuffle document order for non-prefix recurrence.
        order = list(chosen)
        rng.shuffle(order)
        raw_chunks = [list(corpus[d]) for d in order]

        qlen = rng.randint(cfg.query_tokens_min, cfg.query_tokens_max)
        # Query tokens are unique per request so they never count as recurring chunks.
        q_base = 50_000 + i * 200
        query_ids = [((q_base + j) % (cfg.vocab_size - 2000)) + 2000 for j in range(qlen)]

        token_ids, canon_chunks, canon_prefix = assemble_prompt_token_ids(
            prefix_token_ids=prefix_ids,
            chunk_token_ids=raw_chunks,
            query_token_ids=query_ids,
            cfg=cfg.chunking_config(),
        )
        yield TraceRequest(
            request_id=f"req-{i:06d}",
            query_type=query_type,
            prefix_template_id=prefix_tid,
            prefix_token_ids=canon_prefix,
            document_ids=order,
            chunk_token_ids=canon_chunks,
            chunk_lengths=[len(c) for c in canon_chunks],
            query_token_ids=query_ids,
            token_ids=token_ids,
        )


def write_trace(
    cfg: SyntheticWorkloadConfig,
    out_dir: Path,
) -> Path:
    """Write config + JSONL trace under out_dir. Returns path to trace.jsonl."""
    out_dir.mkdir(parents=True, exist_ok=True)
    config_path = out_dir / "config.json"
    trace_path = out_dir / "trace.jsonl"
    meta_path = out_dir / "meta.json"

    config_path.write_text(json.dumps(cfg.to_dict(), indent=2) + "\n", encoding="utf-8")

    n = 0
    with trace_path.open("w", encoding="utf-8") as fh:
        for req in generate_trace(cfg):
            fh.write(json.dumps(req.to_json()) + "\n")
            n += 1

    meta_path.write_text(
        json.dumps(
            {
                "name": cfg.name,
                "num_requests": n,
                "provisional_g0": True,
                "source": "synthetic",
                "notes": (
                    "Synthetic RAG workload with documented recurrence stats. "
                    "G0 result is provisional until a real serving trace is analyzed."
                ),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return trace_path
