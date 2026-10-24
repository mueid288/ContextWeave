"""Canonical chunk-order transforms for native prefix-cache amplification (CPU).

Modes
-----
natural            — no-op
by_doc_id          — natural-sort by document_id (stable)
by_sha256_doc_id   — sort by sha256(document_id) hex (de-correlated from Zipf/alpha)
by_frequency_desc  — hottest docs first (needs freq map); tie-break natural doc id

Does not overload ``segments_canonical`` (boundary/pad). Reorder is length-invariant.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from copy import deepcopy
from hashlib import sha256
import re
from typing import Any, Literal

ChunkOrderMode = Literal[
    "natural",
    "by_doc_id",
    "by_sha256_doc_id",
    "by_frequency_desc",
]

CHUNK_ORDER_MODES: tuple[ChunkOrderMode, ...] = (
    "natural",
    "by_doc_id",
    "by_sha256_doc_id",
    "by_frequency_desc",
)


def natural_doc_key(doc_id: str) -> tuple[tuple[int, object], ...]:
    """Natural sort key so ``chunk-2`` precedes ``chunk-10``.

    Each part is tagged ``(0, int)`` or ``(1, str)`` so keys never compare
    ``str`` to ``int`` across heterogeneous document ids.
    """
    key: list[tuple[int, object]] = []
    for part in re.split(r"(\d+)", doc_id):
        if not part:
            continue
        if part.isdigit():
            key.append((0, int(part)))
        else:
            key.append((1, part.lower()))
    return tuple(key)


def build_doc_frequency(rows: Iterable[dict[str, Any]]) -> dict[str, int]:
    freq: dict[str, int] = {}
    for row in rows:
        for doc_id in row.get("document_ids") or []:
            freq[str(doc_id)] = freq.get(str(doc_id), 0) + 1
    return freq


def _sort_key(
    doc_id: str,
    mode: ChunkOrderMode,
    freq: Mapping[str, int] | None,
) -> tuple[object, ...]:
    if mode == "by_doc_id":
        return natural_doc_key(doc_id)
    if mode == "by_sha256_doc_id":
        digest = sha256(doc_id.encode("utf-8")).hexdigest()
        return (digest,)
    if mode == "by_frequency_desc":
        if freq is None:
            raise ValueError("by_frequency_desc requires a frequency map")
        # Negate count for descending; tie-break natural id.
        return (-int(freq.get(doc_id, 0)),) + natural_doc_key(doc_id)
    raise ValueError(f"unsupported mode for sort: {mode}")


def reorder_chunks(
    row: dict[str, Any],
    mode: ChunkOrderMode = "natural",
    *,
    freq: Mapping[str, int] | None = None,
) -> dict[str, Any]:
    """Return a copy of ``row`` with chunks reordered. Length of token_ids unchanged."""
    if mode == "natural":
        return row

    if mode not in CHUNK_ORDER_MODES:
        raise ValueError(f"unknown chunk order mode: {mode}")

    out = deepcopy(row)
    doc_ids = list(out.get("document_ids") or [])
    chunks = [list(c) for c in (out.get("chunk_token_ids") or [])]
    lengths = list(out.get("chunk_lengths") or [len(c) for c in chunks])

    if not chunks:
        return out
    if len(doc_ids) != len(chunks):
        raise ValueError(
            f"document_ids/chunk_token_ids length mismatch "
            f"({len(doc_ids)} vs {len(chunks)})"
        )
    if lengths and len(lengths) != len(chunks):
        lengths = [len(c) for c in chunks]

    indexed = list(enumerate(zip(doc_ids, chunks, lengths, strict=True)))
    indexed.sort(key=lambda t: _sort_key(str(t[1][0]), mode, freq))

    new_docs: list[str] = []
    new_chunks: list[list[int]] = []
    new_lengths: list[int] = []
    for _, (doc_id, chunk, clen) in indexed:
        new_docs.append(str(doc_id))
        new_chunks.append(list(chunk))
        new_lengths.append(int(clen))

    prefix = list(out.get("prefix_token_ids") or [])
    query = list(out.get("query_token_ids") or [])
    assembled = list(prefix)
    for body in new_chunks:
        assembled.extend(body)
    assembled.extend(query)

    old_tokens = list(out.get("token_ids") or [])
    if old_tokens and len(assembled) != len(old_tokens):
        raise AssertionError(
            f"reorder changed token length {len(old_tokens)} -> {len(assembled)}"
        )

    out["document_ids"] = new_docs
    out["chunk_token_ids"] = new_chunks
    out["chunk_lengths"] = new_lengths
    out["token_ids"] = assembled
    out["chunk_order_mode"] = mode
    return out


def load_trace_rows(path: Any) -> list[dict[str, Any]]:
    from pathlib import Path

    p = Path(path)
    rows: list[dict[str, Any]] = []
    with p.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            import json

            rows.append(json.loads(line))
    return rows
