"""FR-02 / v2.1 §H + Gemini_3 §1.1: boundary-then-pad block alignment."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


# Stand-in boundary token ids when no real tokenizer is loaded.
# Real runs must replace with tokenizer-specific ids for "\\n\\n".
DEFAULT_BOUNDARY_TOKEN_IDS: tuple[int, ...] = (198, 198)


@dataclass(frozen=True)
class ChunkingConfig:
    chunking_config_id: str = "boundary_v1"
    boundary_token_ids: tuple[int, ...] = DEFAULT_BOUNDARY_TOKEN_IDS
    kv_block_size: int = 16
    pad_to_block: bool = True
    chars_per_token: float = 4.0

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["boundary_token_ids"] = list(self.boundary_token_ids)
        return d


def pad_token_count_to_block(n: int, block_size: int) -> int:
    if block_size <= 0:
        return n
    rem = n % block_size
    if rem == 0:
        return n
    return n + (block_size - rem)


def pad_token_ids_to_block(token_ids: list[int], block_size: int, *, pad_id: int = 0) -> list[int]:
    n = pad_token_count_to_block(len(token_ids), block_size)
    if n == len(token_ids):
        return list(token_ids)
    return list(token_ids) + [pad_id] * (n - len(token_ids))


def canonicalize_segment_tokens(
    token_ids: list[int],
    cfg: ChunkingConfig,
    *,
    append_boundary: bool = True,
) -> list[int]:
    """
    Append trailing boundary tokens *then* pad to kv_block_size so each segment
    starts on a page boundary when concatenated (Gemini_3 §1.1).
    """
    tokens = list(token_ids)
    if append_boundary and cfg.boundary_token_ids:
        tokens.extend(cfg.boundary_token_ids)
    if cfg.pad_to_block:
        tokens = pad_token_ids_to_block(tokens, cfg.kv_block_size)
    return tokens


def assemble_prompt_token_ids(
    *,
    prefix_token_ids: list[int],
    chunk_token_ids: list[list[int]],
    query_token_ids: list[int],
    cfg: ChunkingConfig | None = None,
) -> tuple[list[int], list[list[int]], list[int]]:
    """
    Assemble prompt by concatenating *already canonicalized* segments.

    Returns (token_ids, canonical_chunks, canonical_prefix) so analyzers can
    advance cursors by len(canonical_chunk) without drifting on boundaries.
    Query is appended raw (not a reusable KV artifact).
    """
    cfg = cfg or ChunkingConfig()
    canon_prefix = (
        canonicalize_segment_tokens(
            prefix_token_ids, cfg, append_boundary=bool(chunk_token_ids or query_token_ids)
        )
        if prefix_token_ids
        else []
    )

    canon_chunks: list[list[int]] = []
    for i, chunk in enumerate(chunk_token_ids):
        # Each chunk carries its own trailing boundary+pad except possibly the last
        # before query — still append boundary so chunk KV pages are self-contained.
        canon_chunks.append(canonicalize_segment_tokens(chunk, cfg, append_boundary=True))

    out = list(canon_prefix)
    for body in canon_chunks:
        out.extend(body)
    out.extend(query_token_ids)
    return out, canon_chunks, canon_prefix
