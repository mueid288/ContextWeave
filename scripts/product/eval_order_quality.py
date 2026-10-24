#!/usr/bin/env python3
"""Part B: quality of canonical order vs relevance order (HTTP → OpenAI server).

Does **not** load models on the laptop. Point ``--base-url`` at a GPU host
running vLLM (or ``cw-serve-order`` with upstream).

  # After vLLM OpenAI server is up on the GPU box:
  python scripts/product/eval_order_quality.py \\
    --base-url http://127.0.0.1:8000 \\
    --model mistralai/Mistral-7B-Instruct-v0.2 \\
    --out artifacts/product-order-quality/report.json --json

Pass: frequency contains_rate >= 0.90 × relevance contains_rate
      AND frequency contains_rate >= 0.80 (absolute floor).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

_REPO_BOOT = Path(__file__).resolve()
for _cand in _REPO_BOOT.parents:
    if (_cand / "pyproject.toml").exists():
        ROOT = _cand
        break
else:
    raise SystemExit("Could not find repo root (pyproject.toml)")
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from contextweave.product.frequency import FrequencyPrior  # noqa: E402
from contextweave.product.live_order import (  # noqa: E402
    DocumentChunk,
    apply_chat_documents,
    format_documents_block,
    reorder_documents,
)

# Fixed needle suite (same facts as EPIC quality lane).
DOCS: dict[str, str] = {
    "doc-alpha": "Document Alpha. Secret code: ALPHA-9173.",
    "doc-beta": "Document Beta. Named city: Karachi.",
    "doc-gamma": "Document Gamma. Stated year: 2019.",
}

CASES: tuple[dict[str, object], ...] = (
    {
        "id": "city",
        "question": "Which city is named in Document Beta? Reply with only the city name.",
        "gold": "Karachi",
        # Simulated retriever: most relevant first
        "relevance_order": ("doc-beta", "doc-alpha", "doc-gamma"),
    },
    {
        "id": "year",
        "question": "Which year is stated in Document Gamma? Reply with only the year.",
        "gold": "2019",
        "relevance_order": ("doc-gamma", "doc-beta", "doc-alpha"),
    },
    {
        "id": "code",
        "question": "What is the secret code in Document Alpha? Reply with only the code.",
        "gold": "ALPHA-9173",
        "relevance_order": ("doc-alpha", "doc-beta", "doc-gamma"),
    },
)

# Global popularity prior for frequency mode (beta hottest — Zipf-like).
FREQ_WARM: tuple[str, ...] = (
    "doc-beta",
    "doc-beta",
    "doc-beta",
    "doc-alpha",
    "doc-alpha",
    "doc-gamma",
)


def contains_gold(text: str, gold: str) -> bool:
    return gold.lower() in (text or "").lower()


def _chat(
    *,
    base_url: str,
    model: str,
    messages: list[dict],
    max_tokens: int,
    temperature: float,
    timeout: float,
) -> str:
    url = base_url.rstrip("/") + "/v1/chat/completions"
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code}: {detail}") from e
    choices = body.get("choices") or []
    if not choices:
        return ""
    msg = choices[0].get("message") or {}
    return str(msg.get("content") or "")


def _docs_as_chunks(order: tuple[str, ...] | list[str]) -> list[DocumentChunk]:
    return [DocumentChunk(document_id=d, content=DOCS[d]) for d in order]


def build_messages(
    *,
    mode: str,
    case: dict[str, object],
    prior: FrequencyPrior | None,
) -> list[dict]:
    q = str(case["question"])
    if mode == "relevance":
        chunks = _docs_as_chunks(tuple(case["relevance_order"]))  # type: ignore[arg-type]
        block = format_documents_block(chunks)
        return [{"role": "user", "content": f"{block}\n\n{q}"}]
    if mode == "natural":
        # Fixed adversarial order (answer doc last) — not RNG so bench is stable.
        natural = ("doc-alpha", "doc-gamma", "doc-beta")
        if case["id"] == "year":
            natural = ("doc-alpha", "doc-beta", "doc-gamma")
        if case["id"] == "code":
            natural = ("doc-beta", "doc-gamma", "doc-alpha")
        chunks = _docs_as_chunks(natural)
        block = format_documents_block(chunks)
        return [{"role": "user", "content": f"{block}\n\n{q}"}]
    if mode == "frequency":
        body = {
            "messages": [{"role": "user", "content": q}],
            "cw_documents": [
                {"document_id": d, "content": DOCS[d]}
                for d in ("doc-alpha", "doc-beta", "doc-gamma")
            ],
            "cw_chunk_order": "by_frequency_desc",
        }
        out = apply_chat_documents(body, prior=prior, observe=False)
        return list(out["messages"])
    raise ValueError(mode)


def run_suite(
    *,
    base_url: str,
    model: str,
    max_tokens: int,
    temperature: float,
    timeout: float,
    modes: tuple[str, ...] = ("relevance", "natural", "frequency"),
) -> dict:
    prior = FrequencyPrior(cold_start_n=0)
    prior.observe(FREQ_WARM)

    per_mode: dict[str, dict] = {}
    for mode in modes:
        rows = []
        for case in CASES:
            messages = build_messages(mode=mode, case=case, prior=prior)
            text = _chat(
                base_url=base_url,
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                timeout=timeout,
            )
            ok = contains_gold(text, str(case["gold"]))
            rows.append(
                {
                    "id": case["id"],
                    "gold": case["gold"],
                    "contains": ok,
                    "output": text[:500],
                }
            )
        n = len(rows) or 1
        rate = sum(1 for r in rows if r["contains"]) / n
        per_mode[mode] = {"contains_rate": rate, "cases": rows}

    rel = per_mode.get("relevance", {}).get("contains_rate", 0.0)
    freq = per_mode.get("frequency", {}).get("contains_rate", 0.0)
    ratio = (freq / rel) if rel > 0 else 0.0
    pass_heuristic = bool(freq >= 0.80 and (rel == 0.0 or ratio >= 0.90))
    return {
        "pre_reg": "Docs/pre-reg/pre-reg-product-live-shim.md#part-b",
        "model": model,
        "base_url": base_url,
        "modes": per_mode,
        "frequency_vs_relevance_ratio": ratio,
        "pass_heuristic": pass_heuristic,
        "pass_bar": "frequency contains >= 0.80 and >= 0.90 × relevance",
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--base-url", required=True, help="OpenAI-compatible base (no /v1 suffix needed)")
    p.add_argument("--model", default="mistralai/Mistral-7B-Instruct-v0.2")
    p.add_argument("--max-tokens", type=int, default=32)
    p.add_argument("--temperature", type=float, default=0.0)
    p.add_argument("--timeout", type=float, default=120.0)
    p.add_argument("--out", type=Path, default=None)
    p.add_argument("--json", action="store_true")
    p.add_argument(
        "--dry-build",
        action="store_true",
        help="CPU only: build messages for each mode, do not call the model",
    )
    args = p.parse_args(argv)

    if args.dry_build:
        prior = FrequencyPrior(cold_start_n=0)
        prior.observe(FREQ_WARM)
        built = {
            mode: [
                {
                    "id": c["id"],
                    "messages": build_messages(mode=mode, case=c, prior=prior),
                }
                for c in CASES
            ]
            for mode in ("relevance", "natural", "frequency")
        }
        print(json.dumps({"dry_build": built}, indent=2))
        return 0

    payload = run_suite(
        base_url=args.base_url,
        model=args.model,
        max_tokens=args.max_tokens,
        temperature=args.temperature,
        timeout=args.timeout,
    )
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(payload, indent=2) + "\n")
        print(f"Wrote {args.out}", flush=True)
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(
            f"pass={payload['pass_heuristic']} "
            f"freq={payload['modes']['frequency']['contains_rate']:.2f} "
            f"rel={payload['modes']['relevance']['contains_rate']:.2f} "
            f"ratio={payload['frequency_vs_relevance_ratio']:.2f}"
        )
    return 0 if payload["pass_heuristic"] else 4


if __name__ == "__main__":
    raise SystemExit(main())
