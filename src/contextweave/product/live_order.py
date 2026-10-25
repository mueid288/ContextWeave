"""Apply canonical document order to chat / RAG requests (CPU, no model)."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from contextweave.product.frequency import FrequencyPrior
from contextweave.trace_analysis.chunk_order import (
    CHUNK_ORDER_MODES,
    ChunkOrderMode,
    ordered_document_indices,
)


@dataclass(frozen=True)
class DocumentChunk:
    document_id: str
    content: str


def _as_chunks(docs: list[Any]) -> list[DocumentChunk]:
    out: list[DocumentChunk] = []
    for i, d in enumerate(docs):
        if isinstance(d, DocumentChunk):
            out.append(d)
            continue
        if not isinstance(d, dict):
            raise TypeError(f"document[{i}] must be dict or DocumentChunk")
        doc_id = d.get("document_id") or d.get("id") or f"doc-{i}"
        content = d.get("content")
        if content is None:
            content = d.get("text") or d.get("body") or ""
        out.append(DocumentChunk(document_id=str(doc_id), content=str(content)))
    return out


def resolve_mode(
    requested: str,
    prior: FrequencyPrior | None,
) -> ChunkOrderMode:
    mode = requested if requested in CHUNK_ORDER_MODES else "by_frequency_desc"
    mode = mode  # type: ignore[assignment]
    if mode == "by_frequency_desc" and (prior is None or prior.is_cold()):
        return "by_doc_id"
    return mode  # type: ignore[return-value]


def reorder_documents(
    documents: list[Any],
    mode: str = "by_frequency_desc",
    *,
    prior: FrequencyPrior | None = None,
    observe: bool = True,
    effective_mode: str | None = None,
) -> list[DocumentChunk]:
    """Reorder RAG documents; optionally update ``prior`` after ordering.

    Pass ``effective_mode`` when the caller already resolved cold/warm so
    ``cw_mode_effective`` cannot disagree with the sort under concurrency.
    """
    chunks = _as_chunks(documents)
    if not chunks:
        return []
    effective = effective_mode if effective_mode is not None else resolve_mode(mode, prior)
    freq = None if prior is None else prior.as_mapping()
    order = ordered_document_indices(
        [c.document_id for c in chunks],
        effective,  # type: ignore[arg-type]
        freq=freq,
    )
    ordered = [chunks[i] for i in order]
    if observe and prior is not None:
        prior.observe(c.document_id for c in ordered)
    return ordered


def format_documents_block(documents: list[DocumentChunk]) -> str:
    parts = []
    for i, doc in enumerate(documents, start=1):
        parts.append(f"[doc {i} id={doc.document_id}]\n{doc.content}")
    return "\n\n".join(parts)


def apply_chat_documents(
    body: dict[str, Any],
    *,
    prior: FrequencyPrior | None = None,
    default_mode: str = "by_frequency_desc",
    observe: bool = True,
) -> dict[str, Any]:
    """
    Rewrite an OpenAI-style chat body.

    Looks for ``cw_documents`` (list of {document_id, content}) and optional
    ``cw_chunk_order``. Inserts/replaces a context block in the last user message.
    Strips cw_* fields before return so upstream engines do not see them.
    """
    out = deepcopy(body)
    docs_raw = out.pop("cw_documents", None)
    mode = str(out.pop("cw_chunk_order", default_mode) or default_mode)
    meta: dict[str, Any] = {
        "cw_applied": False,
        "cw_mode_requested": mode,
        "cw_mode_effective": None,
        "cw_document_ids": [],
        "cw_prior_cold": None if prior is None else prior.is_cold(),
        "cw_prior_observations": None if prior is None else prior.total_observations,
    }
    if not docs_raw:
        out["cw_meta"] = meta
        return out

    effective = resolve_mode(mode, prior)
    ordered = reorder_documents(
        docs_raw,
        mode,
        prior=prior,
        observe=observe,
        effective_mode=effective,
    )
    block = format_documents_block(ordered)
    messages = list(out.get("messages") or [])
    if not messages:
        messages = [{"role": "user", "content": block}]
    else:
        # Find last user message; prepend docs block.
        last_user = None
        for i in range(len(messages) - 1, -1, -1):
            if messages[i].get("role") == "user":
                last_user = i
                break
        if last_user is None:
            messages.append({"role": "user", "content": block})
        else:
            msg = dict(messages[last_user])
            content = msg.get("content") or ""
            if isinstance(content, list):
                # multimodal — prepend a text part
                msg["content"] = [{"type": "text", "text": block}, *content]
            else:
                marker = "<!-- cw_documents -->"
                if marker in str(content):
                    # replace previous injection
                    before, _, after = str(content).partition(marker)
                    # drop old block through next marker end if present
                    rest = after
                    end = "<!-- /cw_documents -->"
                    if end in rest:
                        rest = rest.split(end, 1)[1]
                    msg["content"] = (
                        f"{before}{marker}\n{block}\n{end}{rest}"
                    )
                else:
                    msg["content"] = (
                        f"{marker}\n{block}\n<!-- /cw_documents -->\n\n{content}"
                    )
            messages[last_user] = msg
    out["messages"] = messages
    meta.update(
        {
            "cw_applied": True,
            "cw_mode_effective": effective,
            "cw_document_ids": [c.document_id for c in ordered],
            "cw_prior_cold": None if prior is None else prior.is_cold(),
            "cw_prior_observations": (
                None if prior is None else prior.total_observations
            ),
        }
    )
    out["cw_meta"] = meta
    return out
