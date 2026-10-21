#!/usr/bin/env python3
"""G1 step 1 — full prefill vs native prefix caching TTFT (GPU only).

Run on Colab / rented GPU after smoke:

  export CONTEXTWEAVE_ALLOW_MODEL_LOAD=1
  python scripts/g1_ttft_bench.py --target-prefix-tokens 6000 --max-model-len 8192 \\
    --json | tee g1_ttft_long.json

Does not install LMCache / CacheBlend yet (G1 step 3).
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
from pathlib import Path

# Allow running from a bare clone without editable install.
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def _build_prefix(doc_chars: int) -> str:
    system = (
        "You are a careful assistant. Answer using only the documents below. "
        "If the answer is missing, say unknown.\n\n"
    )
    docs = []
    for i, name in enumerate(("Alpha", "Beta", "Gamma"), start=1):
        header = f"Document {name} (id={i}). "
        line = f"Fact-{name} token-fill line for ContextWeave G1 TTFT bench. "
        body = header + (line * max(1, (doc_chars // len(line)) + 1))
        body = body[:doc_chars]
        docs.append(f"### Doc {name}\n{body}\n")
    return system + "".join(docs)


def _questions() -> list[str]:
    return [
        "Question: What is the id of Document Alpha? Answer with only the number.",
        "Question: What is the id of Document Beta? Answer with only the number.",
        "Question: What is the id of Document Gamma? Answer with only the number.",
    ]


def _build_prompts_for_token_budget(
    *,
    model: str,
    target_prefix_tokens: int,
    max_model_len: int,
    max_tokens: int,
) -> tuple[str, list[str], int]:
    """Grow docs until shared prefix ≈ target tokens, capped to fit max_model_len."""
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(model, trust_remote_code=True)
    questions = _questions()
    q_max = max(len(tok.encode(q, add_special_tokens=False)) for q in questions)
    # Leave room for question + generation + small safety margin.
    prefix_cap = max_model_len - max_tokens - q_max - 8
    if prefix_cap < 256:
        raise SystemExit(
            f"max_model_len={max_model_len} too small for bench "
            f"(need room for question+{max_tokens} output tokens)."
        )
    want = min(target_prefix_tokens, prefix_cap)

    # Binary-search per-doc char budget (~2–4 chars/token for this filler).
    lo, hi = 200, max(2000, want * 2)
    best_prefix = _build_prefix(lo)
    best_n = len(tok.encode(best_prefix, add_special_tokens=True))
    while lo <= hi:
        mid = (lo + hi) // 2
        prefix = _build_prefix(mid)
        n = len(tok.encode(prefix, add_special_tokens=True))
        if n <= want:
            best_prefix, best_n = prefix, n
            lo = mid + 1
        else:
            hi = mid - 1

    prompts = [best_prefix + q for q in questions]
    for p in prompts:
        n = len(tok.encode(p, add_special_tokens=True))
        if n + max_tokens > max_model_len:
            raise SystemExit(
                f"Prompt still too long ({n} tokens + {max_tokens} gen > "
                f"{max_model_len}). Lower --target-prefix-tokens or raise "
                f"--max-model-len."
            )
    return best_prefix, prompts, best_n


def _run_mode(
    *,
    mode: str,
    enable_prefix_caching: bool,
    model: str,
    max_model_len: int,
    max_tokens: int,
    prompts: list[str],
    warmup: int,
) -> dict:
    from vllm import LLM, SamplingParams

    llm = LLM(
        model=model,
        max_model_len=max_model_len,
        trust_remote_code=True,
        enable_prefix_caching=enable_prefix_caching,
    )
    params = SamplingParams(max_tokens=max_tokens, temperature=0.0)

    for i in range(min(warmup, len(prompts))):
        llm.generate([prompts[i]], params)

    times_ms: list[float] = []
    texts: list[str] = []
    for prompt in prompts:
        t0 = time.perf_counter()
        outs = llm.generate([prompt], params)
        dt = (time.perf_counter() - t0) * 1000.0
        times_ms.append(dt)
        texts.append(outs[0].outputs[0].text.strip())

    del llm
    return {
        "mode": mode,
        "enable_prefix_caching": enable_prefix_caching,
        "n": len(times_ms),
        "ttft_ms": times_ms,
        "p50_ms": statistics.median(times_ms),
        "mean_ms": statistics.fmean(times_ms),
        "outputs": texts,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default=os.environ.get("SMOKE_MODEL", "Qwen/Qwen3-8B"))
    parser.add_argument("--max-model-len", type=int, default=8192)
    parser.add_argument("--max-tokens", type=int, default=16)
    parser.add_argument(
        "--target-prefix-tokens",
        type=int,
        default=6000,
        help="Approximate shared-prefix token count (capped to fit max_model_len).",
    )
    parser.add_argument(
        "--doc-chars",
        type=int,
        default=None,
        help="Deprecated. Prefer --target-prefix-tokens.",
    )
    parser.add_argument("--warmup", type=int, default=1)
    parser.add_argument(
        "--modes",
        default="full_prefill,prefix_cache",
        help="Comma list: full_prefill,prefix_cache",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if os.environ.get("CONTEXTWEAVE_ALLOW_MODEL_LOAD") != "1":
        print(
            "Refusing: set CONTEXTWEAVE_ALLOW_MODEL_LOAD=1 on the GPU host only.",
            file=sys.stderr,
        )
        return 1

    target = args.target_prefix_tokens
    if args.doc_chars is not None:
        # Rough legacy bridge: 3 docs * chars / ~4 chars-per-token.
        target = max(target, (args.doc_chars * 3) // 4)

    print(
        f"Building prompts (target_prefix_tokens≈{target}, "
        f"max_model_len={args.max_model_len})…",
        flush=True,
    )
    prefix, prompts, prefix_tokens = _build_prompts_for_token_budget(
        model=args.model,
        target_prefix_tokens=target,
        max_model_len=args.max_model_len,
        max_tokens=args.max_tokens,
    )
    print(
        f"shared_prefix_chars={len(prefix)} shared_prefix_tokens={prefix_tokens}",
        flush=True,
    )

    results = []
    for mode in [m.strip() for m in args.modes.split(",") if m.strip()]:
        if mode == "full_prefill":
            enable = False
        elif mode == "prefix_cache":
            enable = True
        else:
            print(f"Unknown mode: {mode}", file=sys.stderr)
            return 2
        print(f"=== Running {mode} (prefix_caching={enable}) ===", flush=True)
        results.append(
            _run_mode(
                mode=mode,
                enable_prefix_caching=enable,
                model=args.model,
                max_model_len=args.max_model_len,
                max_tokens=args.max_tokens,
                prompts=prompts,
                warmup=args.warmup,
            )
        )

    payload = {
        "gate": "G1-step1-ttft",
        "model": args.model,
        "max_model_len": args.max_model_len,
        "shared_prefix_chars": len(prefix),
        "shared_prefix_tokens": prefix_tokens,
        "n_prompts": len(prompts),
        "results": results,
    }
    if len(results) == 2:
        full = next(r for r in results if r["mode"] == "full_prefill")
        pref = next(r for r in results if r["mode"] == "prefix_cache")
        if full["p50_ms"] > 0:
            payload["prefix_vs_full_p50_speedup"] = full["p50_ms"] / pref["p50_ms"]

    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        for r in results:
            print(
                f"{r['mode']}: p50={r['p50_ms']:.1f} ms  "
                f"mean={r['mean_ms']:.1f} ms  samples={r['ttft_ms']}"
            )
        if "prefix_vs_full_p50_speedup" in payload:
            print(f"prefix/full p50 speedup: {payload['prefix_vs_full_p50_speedup']:.2f}x")
    return 0


if __name__ == "__main__":
    sys.exit(main())
