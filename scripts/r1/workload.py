"""Zipfian multi-doc RAG requests for Gate R1 (CPU-safe; no model load)."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Sequence


DOC_POOL = (
    ("doc-alpha", "ALPHA-9173", "Karachi"),
    ("doc-beta", "BETA-4421", "Lahore"),
    ("doc-gamma", "GAMMA-1100", "Islamabad"),
    ("doc-delta", "DELTA-8802", "Peshawar"),
    ("doc-epsilon", "EPS-3310", "Quetta"),
    ("doc-zeta", "ZETA-2299", "Multan"),
    ("doc-eta", "ETA-1001", "Faisalabad"),
    ("doc-theta", "THETA-5505", "Hyderabad"),
)


@dataclass(frozen=True)
class R1Request:
    request_id: str
    slice_id: str  # "lookup" | "synthesis"
    question: str
    gold: str
    document_ids: tuple[str, ...]
    bodies: dict[str, str]


def build_bodies(*, filler_chars: int) -> dict[str, str]:
    fill = ("r1 filler sentence. " * max(1, filler_chars // 20))[:filler_chars]
    out: dict[str, str] = {}
    for doc_id, code, city in DOC_POOL:
        out[doc_id] = (
            f"Document {doc_id}. Secret code: {code}. Named city: {city}.\n{fill}"
        )
    return out


def generate_requests(
    *,
    n: int,
    seed: int = 42,
    filler_chars: int = 1800,
    zipf_alpha: float = 1.1,
    synthesis_fraction: float = 0.55,
) -> list[R1Request]:
    rng = random.Random(seed)
    bodies = build_bodies(filler_chars=filler_chars)
    ids = [d[0] for d in DOC_POOL]
    meta = {d[0]: (d[1], d[2]) for d in DOC_POOL}
    weights = [1.0 / ((i + 1) ** zipf_alpha) for i in range(len(ids))]

    reqs: list[R1Request] = []
    for i in range(n):
        synthesis = rng.random() < synthesis_fraction
        if synthesis:
            # two distinct docs; ask for city of less popular of the pair + code of other
            a, b = rng.sample(ids, 2)
            # bias toward popular docs via weighted sample for first
            a = rng.choices(ids, weights=weights, k=1)[0]
            b = a
            while b == a:
                b = rng.choices(ids, weights=weights, k=1)[0]
            city = meta[a][1]
            code = meta[b][0]
            q = (
                f"Using only the documents, what city is named in {a} "
                f"and what secret code is in {b}? "
                f"Reply as: <city> <code>"
            )
            gold = f"{city} {code}"
            doc_ids = (a, b)
            slice_id = "synthesis"
        else:
            doc_id = rng.choices(ids, weights=weights, k=1)[0]
            city = meta[doc_id][1]
            q = (
                f"Using only the documents, which city is named in {doc_id}? "
                f"Reply with only the city name."
            )
            gold = city
            doc_ids = (doc_id,)
            slice_id = "lookup"
        reqs.append(
            R1Request(
                request_id=f"r{i}",
                slice_id=slice_id,
                question=q,
                gold=gold,
                document_ids=doc_ids,
                bodies={d: bodies[d] for d in doc_ids},
            )
        )
    return reqs


def format_prompt(
    req: R1Request,
    ordered_ids: Sequence[str],
    *,
    blend_special_str: str | None = None,
) -> str:
    """Build the user prompt. For CacheBlend, pass ``blend_special_str`` (e.g. ``" # # "``)."""
    blocks = []
    for did in ordered_ids:
        blocks.append(f"### {did}\n{req.bodies[did]}")
    sep = blend_special_str if blend_special_str is not None else "\n\n"
    return sep.join(blocks) + f"{sep}Question: {req.question}"


def quality_contains(text: str, gold: str) -> float:
    t = " ".join((text or "").lower().split())
    g = " ".join(gold.lower().split())
    if not g:
        return 0.0
    return 1.0 if g in t else 0.0


def zipf_share_check(n: int = 40) -> dict[str, float]:
    """Sanity helper for tests — not a gate."""
    reqs = generate_requests(n=n)
    syn = sum(1 for r in reqs if r.slice_id == "synthesis")
    return {"synthesis_fraction": syn / max(1, n), "n": float(n)}
