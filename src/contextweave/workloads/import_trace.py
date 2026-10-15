"""Normalize partner / real serving traces into canonical JSONL for G0."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable
import hashlib
import json
import math

from contextweave.tokenization.boundaries import ChunkingConfig, assemble_prompt_token_ids
from contextweave.workloads._common import approx_token_count


class TraceImportError(ValueError):
    pass


@dataclass
class ImportStats:
    rows_in: int = 0
    rows_out: int = 0
    format_name: str = ""
    synthetic_token_rows: int = 0
    text_approx_rows: int = 0
    errors: list[str] | None = None

    def __post_init__(self) -> None:
        if self.errors is None:
            self.errors = []


def _stable_tokens_from_hash(
    text: str,
    count: int,
    *,
    salt: int = 0,
    vocab_min: int = 1_000,
    vocab_max: int = 31_000,
) -> list[int]:
    """Deterministic pseudo token ids from a content key (not a real tokenizer)."""
    if count <= 0:
        return []
    out: list[int] = []
    counter = salt
    span = max(1, vocab_max - vocab_min)
    while len(out) < count:
        digest = hashlib.sha256(f"{text}:{counter}".encode()).digest()
        for i in range(0, len(digest), 4):
            val = int.from_bytes(digest[i : i + 4], "big") % span + vocab_min
            out.append(val)
            if len(out) >= count:
                break
        counter += 1
    return out


_approx_token_count = approx_token_count


def _as_canonical(
    *,
    request_id: str,
    query_type: str,
    prefix_token_ids: list[int],
    document_ids: list[str],
    chunk_token_ids: list[list[int]],
    query_token_ids: list[int],
    segments_canonical: bool = False,
    chunking: ChunkingConfig | None = None,
) -> dict[str, Any]:
    if query_type not in {"lookup", "synthesis"}:
        # Infer if partner omitted it.
        query_type = "synthesis" if len(chunk_token_ids) >= 2 else "lookup"
    if len(document_ids) != len(chunk_token_ids):
        raise TraceImportError(
            f"{request_id}: document_ids/chunk length mismatch "
            f"({len(document_ids)} vs {len(chunk_token_ids)})"
        )
    if segments_canonical:
        # Partner/corpus lengths already include boundary-then-pad.
        token_ids = (
            list(prefix_token_ids)
            + [t for c in chunk_token_ids for t in c]
            + list(query_token_ids)
        )
        prefix_out = list(prefix_token_ids)
        chunks_out = [list(c) for c in chunk_token_ids]
    else:
        token_ids, chunks_out, prefix_out = assemble_prompt_token_ids(
            prefix_token_ids=prefix_token_ids,
            chunk_token_ids=chunk_token_ids,
            query_token_ids=query_token_ids,
            cfg=chunking or ChunkingConfig(),
        )
    return {
        "request_id": request_id,
        "query_type": query_type,
        "prefix_token_ids": prefix_out,
        "document_ids": document_ids,
        "chunk_token_ids": chunks_out,
        "chunk_lengths": [len(c) for c in chunks_out],
        "query_token_ids": query_token_ids,
        "token_ids": token_ids,
        "context_length": len(token_ids),
        "segments_canonical": True,
    }


def detect_format(row: dict[str, Any]) -> str:
    if "chunk_token_ids" in row and "token_ids" in row and "prefix_token_ids" in row:
        return "canonical"
    if "chunks" in row and isinstance(row["chunks"], list):
        chunks = row["chunks"]
        if chunks and any("text" in c for c in chunks if isinstance(c, dict)):
            return "text_approx"
        return "partner_v1"
    if "prefix_text" in row or "query_text" in row:
        return "text_approx"
    raise TraceImportError("Unrecognized trace row schema")


def normalize_row(
    row: dict[str, Any],
    *,
    format_name: str = "auto",
    chars_per_token: float = 4.0,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return (canonical_row, flags)."""
    fmt = detect_format(row) if format_name == "auto" else format_name
    flags: dict[str, Any] = {"source_format": fmt, "token_ids_synthetic": False, "text_approx": False}

    if fmt == "canonical":
        # Fill missing pieces if possible.
        prefix = list(row.get("prefix_token_ids") or [])
        chunks = [list(c) for c in (row.get("chunk_token_ids") or [])]
        docs = list(row.get("document_ids") or [f"chunk-{i}" for i in range(len(chunks))])
        query = list(row.get("query_token_ids") or [])
        qtype = row.get("query_type") or ("synthesis" if len(chunks) >= 2 else "lookup")
        rid = str(row.get("request_id") or "unknown")
        already = bool(row.get("segments_canonical"))
        canon = _as_canonical(
            request_id=rid,
            query_type=qtype,
            prefix_token_ids=prefix,
            document_ids=docs,
            chunk_token_ids=chunks,
            query_token_ids=query,
            segments_canonical=already,
        )
        return canon, flags

    if fmt == "partner_v1":
        rid = str(row.get("request_id") or "unknown")
        qtype = row.get("query_type") or "lookup"
        prefix = list(row.get("prefix_token_ids") or [])
        if not prefix and row.get("prefix_token_count"):
            prefix = _stable_tokens_from_hash(f"prefix:{rid}", int(row["prefix_token_count"]), salt=1)
            flags["token_ids_synthetic"] = True
        query = list(row.get("query_token_ids") or [])
        if not query and row.get("query_token_count"):
            query = _stable_tokens_from_hash(f"query:{rid}", int(row["query_token_count"]), salt=2)
            flags["token_ids_synthetic"] = True

        docs: list[str] = []
        chunks: list[list[int]] = []
        for i, ch in enumerate(row.get("chunks") or []):
            if not isinstance(ch, dict):
                raise TraceImportError(f"{rid}: chunk {i} must be an object")
            doc_id = str(ch.get("document_id") or f"chunk-{i}")
            docs.append(doc_id)
            if ch.get("token_ids"):
                chunks.append(list(ch["token_ids"]))
            else:
                n = int(ch.get("token_count") or 0)
                key = str(ch.get("content_hash") or doc_id)
                if n <= 0:
                    raise TraceImportError(f"{rid}: chunk {doc_id} needs token_ids or token_count")
                # Salt must NOT depend on chunk position — same hash => same tokens
                # so recurrence detection works across reordered documents.
                chunks.append(_stable_tokens_from_hash(key, n, salt=0))
                flags["token_ids_synthetic"] = True
        # Path C / partner_v1 token_counts are already boundary-then-pad segment sizes.
        already = bool(row.get("segments_canonical", True))
        canon = _as_canonical(
            request_id=rid,
            query_type=qtype,
            prefix_token_ids=prefix,
            document_ids=docs,
            chunk_token_ids=chunks,
            query_token_ids=query,
            segments_canonical=already,
        )
        return canon, flags

    if fmt == "text_approx":
        flags["text_approx"] = True
        flags["token_ids_synthetic"] = True
        rid = str(row.get("request_id") or "unknown")
        qtype = row.get("query_type") or "lookup"
        prefix_text = str(row.get("prefix_text") or "")
        prefix = _stable_tokens_from_hash(
            f"prefix-text:{hashlib.sha256(prefix_text.encode()).hexdigest()}",
            _approx_token_count(prefix_text, chars_per_token),
            salt=1,
        )
        query_text = str(row.get("query_text") or "")
        query = _stable_tokens_from_hash(
            f"query-text:{rid}",
            _approx_token_count(query_text, chars_per_token),
            salt=2,
        )
        docs = []
        chunks = []
        for i, ch in enumerate(row.get("chunks") or []):
            if not isinstance(ch, dict):
                raise TraceImportError(f"{rid}: chunk {i} must be an object")
            doc_id = str(ch.get("document_id") or f"chunk-{i}")
            text = str(ch.get("text") or "")
            docs.append(doc_id)
            key = hashlib.sha256(text.encode()).hexdigest() if text else doc_id
            n = int(ch.get("token_count") or _approx_token_count(text, chars_per_token))
            chunks.append(_stable_tokens_from_hash(key, n, salt=0))
        if not chunks and row.get("documents"):
            raise TraceImportError(f"{rid}: use chunks[].text, not documents")
        canon = _as_canonical(
            request_id=rid,
            query_type=qtype,
            prefix_token_ids=prefix,
            document_ids=docs,
            chunk_token_ids=chunks,
            query_token_ids=query,
            segments_canonical=False,
        )
        return canon, flags

    raise TraceImportError(f"Unsupported format: {fmt}")


def iter_jsonl(path: Path) -> Iterable[str]:
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            yield line


def import_trace_file(
    input_path: Path,
    output_path: Path,
    *,
    format_name: str = "auto",
    chars_per_token: float = 4.0,
) -> ImportStats:
    stats = ImportStats(format_name=format_name)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    detected: set[str] = set()

    with output_path.open("w", encoding="utf-8") as out:
        for lineno, line in enumerate(iter_jsonl(input_path), start=1):
            stats.rows_in += 1
            try:
                try:
                    row = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise TraceImportError(f"{input_path}:{lineno}: invalid JSON ({exc})") from exc
                canon, flags = normalize_row(
                    row, format_name=format_name, chars_per_token=chars_per_token
                )
            except TraceImportError as exc:
                stats.errors.append(str(exc))
                continue
            detected.add(flags["source_format"])
            if flags["token_ids_synthetic"]:
                stats.synthetic_token_rows += 1
            if flags["text_approx"]:
                stats.text_approx_rows += 1
            out.write(json.dumps(canon) + "\n")
            stats.rows_out += 1

    if len(detected) == 1:
        stats.format_name = next(iter(detected))
    elif detected:
        stats.format_name = "mixed:" + ",".join(sorted(detected))

    meta_path = output_path.parent / "import_meta.json"
    meta_path.write_text(
        json.dumps(
            {
                "source": str(input_path),
                "output": str(output_path),
                "format": stats.format_name,
                "rows_in": stats.rows_in,
                "rows_out": stats.rows_out,
                "synthetic_token_rows": stats.synthetic_token_rows,
                "text_approx_rows": stats.text_approx_rows,
                "errors": stats.errors,
                "provisional_g0": stats.text_approx_rows > 0 or stats.synthetic_token_rows > 0,
                "notes": "CPU-only import. No model tokenization.",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return stats
