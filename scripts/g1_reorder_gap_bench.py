#!/usr/bin/env python3
"""G1 reorder gap — show why non-prefix reuse matters (GPU, no LMCache).

Same planted facts as the quality bench, but document **order changes**.
Native prefix caching cannot reuse reordered middle docs; TTFT stays near
full prefill while answers should still be correct under full compute.

  export CONTEXTWEAVE_ALLOW_MODEL_LOAD=1
  python scripts/g1_reorder_gap_bench.py --json | tee g1_reorder_gap.json

This does **not** replace CacheBlend — it quantifies the gap CacheBlend targets
on a stack where CacheBlend is currently pin-blocked.
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# Reuse quality helpers / cases.
import importlib.util


def _load_quality():
    path = ROOT / "scripts" / "g1_quality_bench.py"
    spec = importlib.util.spec_from_file_location("g1_quality_bench", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _docs_in_order(filler: str, order: tuple[str, ...]) -> str:
    blocks = {
        "A": f"### Document Alpha\nSecret code: ALPHA-9173.\n{filler}\n",
        "B": f"### Document Beta\nNamed city: Karachi.\n{filler}\n",
        "C": f"### Document Gamma\nStated year: 2019.\n{filler}\n",
    }
    head = (
        "You are a careful assistant. Use only the documents. "
        "Prefer a short answer.\n\n"
    )
    return head + "\n".join(blocks[k] for k in order)


def main(argv: list[str] | None = None) -> int:
    q = _load_quality()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default=os.environ.get("SMOKE_MODEL", "Qwen/Qwen3-8B"))
    parser.add_argument("--max-model-len", type=int, default=8192)
    parser.add_argument("--max-tokens", type=int, default=24)
    parser.add_argument("--filler-chars", type=int, default=2500)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if os.environ.get("CONTEXTWEAVE_ALLOW_MODEL_LOAD") != "1":
        print(
            "Refusing: set CONTEXTWEAVE_ALLOW_MODEL_LOAD=1 on the GPU host only.",
            file=sys.stderr,
        )
        return 1

    from vllm import LLM, SamplingParams

    filler = ("contextweave reorder filler sentence. " * 200)[: args.filler_chars]
    order_abc = ("A", "B", "C")
    order_bca = ("B", "C", "A")
    docs_abc = _docs_in_order(filler, order_abc)
    docs_bca = _docs_in_order(filler, order_bca)

    # One representative question (Beta city) — answer must survive reorder.
    question = next(c["question"] for c in q.CASES if c["id"] == "beta_city")
    gold = "Karachi"
    prompt_abc = docs_abc + question
    prompt_bca = docs_bca + question

    print(
        f"Reorder gap bench model={args.model} "
        f"abc_chars={len(docs_abc)} bca_chars={len(docs_bca)}",
        flush=True,
    )

    # Single engine with prefix caching ON — shared system prefix is tiny;
    # reordered docs should NOT get a large prefix hit.
    print("=== loading prefix_caching=True engine ===", flush=True)
    llm = LLM(
        model=args.model,
        max_model_len=args.max_model_len,
        trust_remote_code=True,
        enable_prefix_caching=True,
    )
    params = SamplingParams(max_tokens=args.max_tokens, temperature=0.0)

    def timed(prompt: str, label: str) -> tuple[float, str]:
        print(f"  [{label}] …", flush=True)
        t0 = time.perf_counter()
        outs = llm.generate([prompt], params)
        ms = (time.perf_counter() - t0) * 1000.0
        text = outs[0].outputs[0].text.strip()
        print(f"  [{label}] {ms:.0f} ms", flush=True)
        return ms, text

    # Warm the ABC order twice so prefix cache is hot for ABC.
    timed(prompt_abc, "abc_cold")
    abc_ms, abc_text = timed(prompt_abc, "abc_warm")
    # Reordered docs — native prefix should miss most of the body.
    bca_ms, bca_text = timed(prompt_bca, "bca_reorder")

    del llm

    abc_sc = q._score(abc_text, gold)
    bca_sc = q._score(bca_text, gold)
    payload = {
        "gate": "G1-reorder-gap",
        "model": args.model,
        "gold": gold,
        "abc_warm_ms": abc_ms,
        "bca_reorder_ms": bca_ms,
        "reorder_vs_warm_prefix_slowdown": (
            bca_ms / abc_ms if abc_ms > 0 else None
        ),
        "abc_score": abc_sc,
        "bca_score": bca_sc,
        "both_contain_gold": abc_sc["contains"] and bca_sc["contains"],
        "pass_heuristic": (
            abc_sc["contains"]
            and bca_sc["contains"]
            and abc_ms > 0
            and bca_ms > 1.15 * abc_ms
        ),
        "note": (
            "pass_heuristic: both orders answer correctly AND reordered TTFT is "
            "≥15% slower than warm ABC — gap that non-prefix methods target."
        ),
    }

    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(
            f"abc_warm={abc_ms:.0f}ms bca={bca_ms:.0f}ms "
            f"slowdown={payload['reorder_vs_warm_prefix_slowdown']:.2f}x "
            f"both_ok={payload['both_contain_gold']} "
            f"pass={payload['pass_heuristic']}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
