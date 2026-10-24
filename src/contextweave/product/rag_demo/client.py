"""HTTP ask client → cw-serve-order (stdlib urllib only)."""

from __future__ import annotations

from dataclasses import dataclass
import json
import time
import urllib.error
import urllib.request
from typing import Any


@dataclass(frozen=True)
class AskResult:
    answer: str
    wall_ms: float
    cw_meta: dict[str, Any] | None
    raw: dict[str, Any]
    retrieved_ids: list[str]


def build_ask_body(
    question: str,
    documents: list[dict[str, str]],
    *,
    model: str,
    chunk_order: str = "by_frequency_desc",
    system: str | None = None,
    max_tokens: int = 256,
    temperature: float = 0.0,
) -> dict[str, Any]:
    messages: list[dict[str, str]] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": question})
    return {
        "model": model,
        "messages": messages,
        "cw_documents": [
            {"document_id": d["document_id"], "content": d["content"]} for d in documents
        ],
        "cw_chunk_order": chunk_order,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }


def ask(
    *,
    base_url: str,
    question: str,
    documents: list[dict[str, str]],
    model: str,
    chunk_order: str = "by_frequency_desc",
    system: str | None = (
        "Answer using only the provided documents. "
        "Be concise; prefer exact phrases from the docs when possible."
    ),
    max_tokens: int = 256,
    temperature: float = 0.0,
    timeout: float = 180.0,
) -> AskResult:
    body = build_ask_body(
        question,
        documents,
        model=model,
        chunk_order=chunk_order,
        system=system,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    url = base_url.rstrip("/") + "/v1/chat/completions"
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw_bytes = resp.read()
    except urllib.error.HTTPError as e:
        raise RuntimeError(
            f"HTTP {e.code}: {e.read().decode('utf-8', errors='replace')}"
        ) from e
    wall_ms = (time.perf_counter() - t0) * 1000.0
    raw = json.loads(raw_bytes.decode("utf-8"))
    answer = ((raw.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
    cw_meta = raw.get("cw_meta")
    return AskResult(
        answer=str(answer),
        wall_ms=wall_ms,
        cw_meta=cw_meta if isinstance(cw_meta, dict) else None,
        raw=raw,
        retrieved_ids=[d["document_id"] for d in documents],
    )
