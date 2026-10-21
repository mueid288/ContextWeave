#!/usr/bin/env python3
"""G1 step 3 — CacheBlend non-prefix reuse TTFT (GPU only).

Adapted from LMCache ``examples/blend_in_process/blend.py`` (Apache-2.0).

Install on the GPU host (after smoke + G1 TTFT):

  pip install lmcache
  # If CUDA ABI conflicts with the already-installed vLLM/torch stack:
  #   pip install 'lmcache' --no-deps
  #   pip install msgspec pyyaml zstandard aiohttp redis  # add whatever import asks for

Run:

  export CONTEXTWEAVE_ALLOW_MODEL_LOAD=1
  export PYTHONHASHSEED=0
  export VLLM_WORKER_MULTIPROC_METHOD=spawn
  python scripts/g1_cacheblend_bench.py --json | tee g1_cacheblend.json

Success signal: reordered-chunk (warm) p50 TTFT clearly below first-order (cold)
full prefill, with the same chunks only reordered. If times stay ≈ equal, treat as
a #3238-class failure for this pin and document — do not expand the matrix yet.
"""

from __future__ import annotations

import argparse
import contextlib
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


def _setup_blend_env(*, blend_special_str: str, cpu_gb: float) -> None:
    os.environ["LMCACHE_CHUNK_SIZE"] = "256"
    os.environ["LMCACHE_ENABLE_BLENDING"] = "True"
    os.environ["LMCACHE_BLEND_SPECIAL_STR"] = blend_special_str
    os.environ["LMCACHE_USE_LAYERWISE"] = "True"
    os.environ["LMCACHE_BLEND_CHECK_LAYERS"] = "1"
    os.environ["LMCACHE_BLEND_RECOMPUTE_RATIOS"] = "0.15"
    os.environ["LMCACHE_LOCAL_CPU"] = "True"
    os.environ["LMCACHE_MAX_LOCAL_CPU_SIZE"] = str(cpu_gb)


def _patch_vllm_register_model_for_blend() -> None:
    """Stock vLLM never calls VLLMModelTracker.register_model (LMCache #4131).

    CacheBlend's blender then fails with: ``vllm model for vllm-instance not found``.
    Hook ``GPUModelRunner.load_model`` so registration happens before KV init.
    Must run in the same process as the worker — we disable V1 multiprocessing.
    """
    import importlib

    from lmcache.integration.vllm.utils import ENGINE_NAME
    from lmcache.v1.compute.models.utils import VLLMModelTracker

    for mod_name in (
        "vllm.v1.worker.gpu_model_runner",
        "vllm.v1.worker.gpu.model_runner",
    ):
        try:
            mod = importlib.import_module(mod_name)
        except Exception:
            continue
        cls = getattr(mod, "GPUModelRunner", None)
        if cls is None:
            continue
        orig = cls.load_model
        if getattr(orig, "_cw_blend_patched", False):
            continue

        def load_model(self, *args, _orig=orig, **kwargs):  # noqa: ANN001
            out = _orig(self, *args, **kwargs)
            model_obj = getattr(self, "model", None)
            if model_obj is not None:
                VLLMModelTracker.register_model(ENGINE_NAME, model_obj)
            return out

        load_model._cw_blend_patched = True  # type: ignore[attr-defined]
        cls.load_model = load_model  # type: ignore[method-assign]
        print(f"patched {mod_name}.GPUModelRunner.load_model for CacheBlend", flush=True)


@contextlib.contextmanager
def _build_llm(*, model: str, max_model_len: int, gpu_mem: float):
    from vllm import LLM
    from vllm.config import KVTransferConfig

    from lmcache.integration.vllm.utils import ENGINE_NAME
    from lmcache.v1.cache_engine import LMCacheEngineBuilder

    # In-process worker so the register_model monkeypatch is visible.
    os.environ["VLLM_ENABLE_V1_MULTIPROCESSING"] = "0"
    _patch_vllm_register_model_for_blend()

    # Construct LLM with explicit kwargs — asdict(EngineArgs) breaks on vLLM 0.32
    # (CompilationConfig.cudagraph_capture_sizes=None fails pydantic validation).
    ktc = KVTransferConfig(
        kv_connector="LMCacheConnectorV1",
        kv_role="kv_both",
    )
    llm = LLM(
        model=model,
        kv_transfer_config=ktc,
        max_model_len=max_model_len,
        gpu_memory_utilization=gpu_mem,
        enable_prefix_caching=False,  # isolate non-prefix blend signal
        enforce_eager=True,
        trust_remote_code=True,
    )
    try:
        yield llm
    finally:
        try:
            LMCacheEngineBuilder.destroy(ENGINE_NAME)
        except Exception as exc:  # pragma: no cover
            print(f"warn: LMCache teardown: {exc}", file=sys.stderr)
        del llm


def _fill_chunk(tokenizer, name: str, target_tokens: int) -> list[int]:
    line = f"Document {name} (id={name}). Fact-{name} token-fill for CacheBlend G1. "
    ids: list[int] = []
    # Drop BOS on continuations the same way the upstream example does ([1:]).
    piece = tokenizer.encode(line, add_special_tokens=False)
    while len(ids) < target_tokens:
        ids.extend(piece)
    return ids[:target_tokens]


def _join_chunks(
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


def _timed_generate(llm, prompt_ids: list[int], sampling) -> tuple[float, str]:
    t0 = time.perf_counter()
    outs = llm.generate(
        prompts={"prompt_token_ids": prompt_ids},
        sampling_params=sampling,
    )
    ms = (time.perf_counter() - t0) * 1000.0
    text = outs[0].outputs[0].text.strip() if outs and outs[0].outputs else ""
    return ms, text


def _ensure_spawn() -> None:
    """vLLM EngineCore forks; importing lmcache touches CUDA in the parent.

    Force spawn so the child does not inherit an initialized CUDA context.
    """
    os.environ.setdefault("VLLM_WORKER_MULTIPROC_METHOD", "spawn")
    import multiprocessing as mp

    try:
        mp.set_start_method("spawn", force=True)
    except RuntimeError:
        pass


def main(argv: list[str] | None = None) -> int:
    _ensure_spawn()

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default=os.environ.get("SMOKE_MODEL", "Qwen/Qwen3-8B"))
    parser.add_argument("--max-model-len", type=int, default=8192)
    parser.add_argument("--chunk-tokens", type=int, default=1500)
    parser.add_argument("--max-tokens", type=int, default=16)
    parser.add_argument("--gpu-memory-utilization", type=float, default=0.70)
    parser.add_argument("--lmcache-cpu-gb", type=float, default=8.0)
    parser.add_argument("--blend-special-str", default=" # # ")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if os.environ.get("CONTEXTWEAVE_ALLOW_MODEL_LOAD") != "1":
        print(
            "Refusing: set CONTEXTWEAVE_ALLOW_MODEL_LOAD=1 on the GPU host only.",
            file=sys.stderr,
        )
        return 1

    _setup_blend_env(
        blend_special_str=args.blend_special_str,
        cpu_gb=args.lmcache_cpu_gb,
    )

    # Tokenize before importing lmcache (lmcache import initializes CUDA).
    from transformers import AutoTokenizer
    from vllm import SamplingParams

    tokenizer = AutoTokenizer.from_pretrained(args.model, trust_remote_code=True)
    sep = tokenizer.encode(args.blend_special_str, add_special_tokens=False)
    # Prefer continuation tokens for the separator (match upstream example).
    if len(sep) > 1:
        sep = sep[1:] if sep[0] == tokenizer.bos_token_id else sep

    system = tokenizer.encode(
        "You are a careful assistant. Answer using only the documents. "
        "Reply with only the document id number.",
        add_special_tokens=True,
    )
    chunk_a = _fill_chunk(tokenizer, "Alpha", args.chunk_tokens)
    chunk_b = _fill_chunk(tokenizer, "Beta", args.chunk_tokens)
    chunk_c = _fill_chunk(tokenizer, "Gamma", args.chunk_tokens)

    # Cold: order A-B-C. Warm reorder: B-A-C (same chunks, not a shared prefix).
    cold = _join_chunks(
        tokenizer,
        system=system,
        chunks=[chunk_a, chunk_b, chunk_c],
        question="What is the id of Document Alpha?",
        sep=sep,
    )
    warm = _join_chunks(
        tokenizer,
        system=system,
        chunks=[chunk_b, chunk_a, chunk_c],
        question="What is the id of Document Alpha?",
        sep=sep,
    )
    warm2 = _join_chunks(
        tokenizer,
        system=system,
        chunks=[chunk_c, chunk_b, chunk_a],
        question="What is the id of Document Beta?",
        sep=sep,
    )

    for name, ids in (("cold", cold), ("warm", warm), ("warm2", warm2)):
        if len(ids) + args.max_tokens > args.max_model_len:
            print(
                f"Prompt '{name}' is {len(ids)} tokens; raise --max-model-len "
                f"or lower --chunk-tokens.",
                file=sys.stderr,
            )
            return 3

    sampling = SamplingParams(temperature=0.0, max_tokens=args.max_tokens)
    print(
        f"CacheBlend bench model={args.model} chunk_tokens={args.chunk_tokens} "
        f"cold_len={len(cold)} warm_len={len(warm)}",
        flush=True,
    )

    try:
        import lmcache  # noqa: F401
    except ImportError as exc:
        print(
            "lmcache not importable. On the GPU host run: pip install lmcache\n"
            f"Import error: {exc}",
            file=sys.stderr,
        )
        return 2

    with _build_llm(
        model=args.model,
        max_model_len=args.max_model_len,
        gpu_mem=args.gpu_memory_utilization,
    ) as llm:
        # Tiny warmup so CUDA graphs / kernels settle (not counted).
        warm_ids = tokenizer.encode("warmup " * 64, add_special_tokens=True)
        _timed_generate(llm, warm_ids, SamplingParams(temperature=0.0, max_tokens=1))

        cold_ms, cold_text = _timed_generate(llm, cold, sampling)
        warm_ms, warm_text = _timed_generate(llm, warm, sampling)
        warm2_ms, warm2_text = _timed_generate(llm, warm2, sampling)

    warm_samples = [warm_ms, warm2_ms]
    payload = {
        "gate": "G1-step3-cacheblend",
        "model": args.model,
        "max_model_len": args.max_model_len,
        "chunk_tokens": args.chunk_tokens,
        "blend_special_str": args.blend_special_str,
        "cold_prompt_tokens": len(cold),
        "results": {
            "cold_abc_ms": cold_ms,
            "warm_bac_ms": warm_ms,
            "warm_cba_ms": warm2_ms,
            "warm_p50_ms": statistics.median(warm_samples),
            "cold_vs_warm_p50_speedup": (
                cold_ms / statistics.median(warm_samples)
                if statistics.median(warm_samples) > 0
                else None
            ),
        },
        "outputs": {
            "cold": cold_text,
            "warm_bac": warm_text,
            "warm_cba": warm2_text,
        },
        "pass_heuristic": statistics.median(warm_samples) < 0.85 * cold_ms,
        "note": (
            "pass_heuristic True means warm reorder was ≥15% faster than cold — "
            "consistent with non-prefix KV reuse. False → document pin failure."
        ),
    }

    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        r = payload["results"]
        print(
            f"cold={r['cold_abc_ms']:.1f} ms  "
            f"warm_p50={r['warm_p50_ms']:.1f} ms  "
            f"speedup={r['cold_vs_warm_p50_speedup']:.2f}x  "
            f"pass_heuristic={payload['pass_heuristic']}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
