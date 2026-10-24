"""Corpus ingest: fixed-char windows with CW-style document ids."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path


DEFAULT_CHUNK_CHARS = 1000
DEFAULT_OVERLAP = 100


@dataclass(frozen=True)
class Chunk:
    document_id: str
    content: str
    source_path: str
    char_start: int
    char_end: int

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Chunk":
        return cls(
            document_id=str(d["document_id"]),
            content=str(d["content"]),
            source_path=str(d.get("source_path") or ""),
            char_start=int(d.get("char_start") or 0),
            char_end=int(d.get("char_end") or 0),
        )


def make_document_id(stem: str, idx: int) -> str:
    """Natural-sortable id: ``{stem}::chunk-{idx:03d}``."""
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in stem)
    return f"{safe}::chunk-{idx:03d}"


def chunk_text(
    text: str,
    *,
    stem: str,
    source_path: str = "",
    chunk_chars: int = DEFAULT_CHUNK_CHARS,
    overlap: int = DEFAULT_OVERLAP,
) -> list[Chunk]:
    if chunk_chars <= 0:
        raise ValueError("chunk_chars must be > 0")
    overlap = max(0, min(overlap, chunk_chars - 1))
    text = text.replace("\r\n", "\n")
    if not text.strip():
        return []
    chunks: list[Chunk] = []
    start = 0
    idx = 0
    n = len(text)
    while start < n:
        end = min(start + chunk_chars, n)
        piece = text[start:end]
        if piece.strip():
            chunks.append(
                Chunk(
                    document_id=make_document_id(stem, idx),
                    content=piece,
                    source_path=source_path,
                    char_start=start,
                    char_end=end,
                )
            )
            idx += 1
        if end >= n:
            break
        start = end - overlap
    return chunks


def iter_corpus_files(corpus_dir: Path) -> list[Path]:
    root = Path(corpus_dir)
    if not root.is_dir():
        raise FileNotFoundError(f"corpus directory not found: {root}")
    files = sorted(
        p
        for p in root.rglob("*")
        if p.is_file() and p.suffix.lower() in {".md", ".txt"}
    )
    return files


def chunk_corpus(
    corpus_dir: Path,
    *,
    chunk_chars: int = DEFAULT_CHUNK_CHARS,
    overlap: int = DEFAULT_OVERLAP,
) -> list[Chunk]:
    out: list[Chunk] = []
    for path in iter_corpus_files(corpus_dir):
        text = path.read_text(encoding="utf-8", errors="replace")
        out.extend(
            chunk_text(
                text,
                stem=path.stem,
                source_path=str(path),
                chunk_chars=chunk_chars,
                overlap=overlap,
            )
        )
    return out
