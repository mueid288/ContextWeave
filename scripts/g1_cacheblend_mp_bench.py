#!/usr/bin/env python3
"""G1 CacheBlend via LMCache **MP** blend engine (GPU).

Prefer this over in-process blending on vLLM 0.32 (in-process hits KV dim errors).

Started by ``scripts/g1_cacheblend_mp.sh`` (launches ``lmcache server --engine-type blend``).

  export CONTEXTWEAVE_ALLOW_MODEL_LOAD=1
  bash scripts/g1_cacheblend_mp.sh
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


def _ensure_spawn() -> None:
    os.environ.setdefault("VLLM_WORKER_MULTIPROC_METHOD", "spawn")
    import multiprocessing as mp

    try:
        mp.set_start_method("spawn", force=True)
    except RuntimeError:
        pass


def _fill_chunk(tokenizer, name: str, target_tokens: int) -> list[int]:
    line = f"Document {name} (id={name}). Fact-{name} token-fill for CacheBlend MP G1. "
    ids: list[int] = []
    piece = tokenizer.encode(line, add_special_tokens=False)
    while len(ids) < target_tokens:
        ids.extend(piece)
    return ids[:target_tokens]


def _join(
    tokenizer,
    *,
    system: list[int],
    chunks: list[list[int]],
    question: str,
    sep: list[int],
) -> list[int]:
    out = list(system)
    for ch in chunks:
        out.extend(sep)
        out.extend(ch)
    out.extend(sep)
    out.extend(tokenizer.encode(question, add_special_tokens=False))
    return out


def _timed(llm, prompt_ids: list[int], sampling) -> tuple[float, str]:
    t0 = time.perf_counter()
    outs = llm.generate(
        prompts={"prompt_token_ids": prompt_ids},
        sampling_params=sampling,
    )
    ms = (time.perf_counter() - t0) * 1000.0
    text = outs[0].outputs[0].text.strip() if outs and outs[0].outputs else ""
    return ms, text


def main(argv: list[str] | None = None) -> int:
    _ensure_spawn()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default=os.environ.get("SMOKE_MODEL", "Qwen/Qwen3-8B"))
    parser.add_argument("--max-model-len", type=int, default=8192)
    parser.add_argument("--chunk-tokens", type=int, default=1500)
    parser.add_argument("--max-tokens", type=int, default=16)
    parser.add_argument("--gpu-memory-utilization", type=float, default=0.70)
    parser.add_argument("--blend-special-str", default=" # # ")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if os.environ.get("CONTEXTWEAVE_ALLOW_MODEL_LOAD") != "1":
        print(
            "Refusing: set CONTEXTWEAVE_ALLOW_MODEL_LOAD=1 on the GPU host only.",
            file=sys.stderr,
        )
        return 1

    host = os.environ.get("LMCACHE_MP_HOST", "127.0.0.1")
    port = int(os.environ.get("LMCACHE_MP_PORT", "5555"))

    from transformers import AutoTokenizer
    from vllm import LLM, SamplingParams
    from vllm.config import KVTransferConfig

    tokenizer = AutoTokenizer.from_pretrained(args.model, trust_remote_code=True)
    sep = tokenizer.encode(args.blend_special_str, add_special_tokens=False)
    if sep and sep[0] == tokenizer.bos_token_id and len(sep) > 1:
        sep = sep[1:]

    system = tokenizer.encode(
        "You are a careful assistant. Answer using only the documents. "
        "Reply with only the document id number.",
        add_special_tokens=True,
    )
    chunk_a = _fill_chunk(tokenizer, "Alpha", args.chunk_tokens)
    chunk_b = _fill_chunk(tokenizer, "Beta", args.chunk_tokens)
    chunk_c = _fill_chunk(tokenizer, "Gamma", args.chunk_tokens)

    cold = _join(
        tokenizer,
        system=system,
        chunks=[chunk_a, chunk_b, chunk_c],
        question="What is the id of Document Alpha?",
        sep=sep,
    )
    warm = _join(
        tokenizer,
        system=system,
        chunks=[chunk_b, chunk_a, chunk_c],
        question="What is the id of Document Alpha?",
        sep=sep,
    )
    warm2 = _join(
        tokenizer,
        system=system,
        chunks=[chunk_c, chunk_b, chunk_a],
        question="What is the id of Document Beta?",
        sep=sep,
    )

    for name, ids in (("cold", cold), ("warm", warm), ("warm2", warm2)):
        if len(ids) + args.max_tokens > args.max_model_len:
            print(f"Prompt {name} too long ({len(ids)} tokens).", file=sys.stderr)
            return 3

    ktc = KVTransferConfig(
        kv_connector="LMCacheMPConnector",
        kv_connector_module_path="lmcache.integration.vllm.lmcache_mp_connector",
        kv_role="kv_both",
        kv_connector_extra_config={
            "lmcache.mp.host": f"tcp://{host}",
            "lmcache.mp.port": port,
        },
    )

    print(
        f"MP CacheBlend bench model={args.model} server={host}:{port} "
        f"cold_len={len(cold)}",
        flush=True,
    )
    print("=== loading vLLM + LMCacheMPConnector ===", flush=True)
    llm = LLM(
        model=args.model,
        kv_transfer_config=ktc,
        max_model_len=args.max_model_len,
        gpu_memory_utilization=args.gpu_memory_utilization,
        enable_prefix_caching=False,
        enforce_eager=True,
        trust_remote_code=True,
    )
    sampling = SamplingParams(temperature=0.0, max_tokens=args.max_tokens)

    print("  [cold ABC] …", flush=True)
    cold_ms, cold_text = _timed(llm, cold, sampling)
    print(f"  [cold ABC] {cold_ms:.0f} ms", flush=True)
    print("  [warm BAC] …", flush=True)
    warm_ms, warm_text = _timed(llm, warm, sampling)
    print(f"  [warm BAC] {warm_ms:.0f} ms", flush=True)
    print("  [warm CBA] …", flush=True)
    warm2_ms, warm2_text = _timed(llm, warm2, sampling)
    print(f"  [warm CBA] {warm2_ms:.0f} ms", flush=True)

    del llm
    warm_p50 = statistics.median([warm_ms, warm2_ms])
    payload = {
        "gate": "G1-step3-cacheblend-mp",
        "model": args.model,
        "lmcache_mp": {"host": host, "port": port},
        "cold_abc_ms": cold_ms,
        "warm_bac_ms": warm_ms,
        "warm_cba_ms": warm2_ms,
        "warm_p50_ms": warm_p50,
        "cold_vs_warm_p50_speedup": cold_ms / warm_p50 if warm_p50 > 0 else None,
        "outputs": {"cold": cold_text, "warm_bac": warm_text, "warm_cba": warm2_text},
        "pass_heuristic": warm_p50 < 0.85 * cold_ms,
        "note": (
            "MP blend engine path. pass_heuristic True ⇒ reordered warm ≥15% faster "
            "than cold — evidence of non-prefix reuse."
        ),
    }

    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(
            f"cold={cold_ms:.0f} warm_p50={warm_p50:.0f} "
            f"speedup={payload['cold_vs_warm_p50_speedup']:.2f}x "
            f"pass={payload['pass_heuristic']}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
