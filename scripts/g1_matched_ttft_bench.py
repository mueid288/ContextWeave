#!/usr/bin/env python3
"""G1 matched-pin TTFT bench (GPU).

Native prefix protocol:
  1. Seed ABC once (discarded)
  2. Measure warm_abc × N  (exact repeat → prefix hit)
  3. Measure warm_bac × N  (reorder, **no** BAC seed → should miss)
  4. Measure warm_cba × N
  5. Measure cold_abc × N  (unique **leading** nonce)

Size prompts to ``--target-prefix-tokens`` (default 6000) — short fillers on A100
only show ~tens of ms cold/warm delta, which hides the reorder gap.

  export CONTEXTWEAVE_ALLOW_MODEL_LOAD=1
  python scripts/g1_matched_ttft_bench.py --backend native_prefix --runs 10 --json
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

ORDERS = {
    "abc": ("A", "B", "C"),
    "bac": ("B", "A", "C"),
    "cba": ("C", "B", "A"),
}


def _docs(order: tuple[str, ...], *, fillers: dict[str, str], head: str) -> str:
    blocks = {
        "A": f"### Document Alpha\nSecret code: ALPHA-9173.\n{fillers['A']}\n",
        "B": f"### Document Beta\nNamed city: Karachi.\n{fillers['B']}\n",
        "C": f"### Document Gamma\nStated year: 2019.\n{fillers['C']}\n",
    }
    return head + "\n".join(blocks[k] for k in order)


def _fillers_for_chars(n: int, *, salt: str = "") -> dict[str, str]:
    """Build per-doc fillers. ``salt`` makes LMCache chunk ids unique across trials."""
    prefix = f"{salt}" if salt else ""
    return {
        "A": (prefix + "alpha-only filler sentence for prefix bench. " * 400)[:n],
        "B": (prefix + "beta-unique filler sentence for prefix bench. " * 400)[:n],
        "C": (prefix + "gamma-unique filler sentence for prefix bench. " * 400)[:n],
    }


def _reorder_series_polluted(samples: list[float]) -> bool:
    """True when trial-1 looks like a miss but p50 collapsed to later self-hits."""
    if len(samples) < 3:
        return False
    first = samples[0]
    rest_p50 = statistics.median(samples[1:])
    return first >= 1.15 * rest_p50


def _percentile(xs: list[float], p: float) -> float:
    if not xs:
        return float("nan")
    ys = sorted(xs)
    if len(ys) == 1:
        return ys[0]
    k = (len(ys) - 1) * p
    f = int(k)
    c = min(f + 1, len(ys) - 1)
    if f == c:
        return ys[f]
    return ys[f] + (ys[c] - ys[f]) * (k - f)


def _ttft_ms(llm, prompt: str, sampling) -> tuple[float, str, str]:
    """Wall-clock generate time (same as working g1_reorder_gap / g1_ttft)."""
    t0 = time.perf_counter()
    outs = llm.generate([prompt], sampling, use_tqdm=False)
    wall = (time.perf_counter() - t0) * 1000.0
    text = outs[0].outputs[0].text.strip() if outs and outs[0].outputs else ""
    return wall, text, "wall_clock_generate"


def _reset_prefix_cache(llm) -> bool:
    """Clear automatic prefix cache so the next reorder is a real miss."""
    fn = getattr(llm, "reset_prefix_cache", None)
    if callable(fn):
        try:
            fn()
            return True
        except TypeError:
            try:
                fn(reset_running_requests=True)
                return True
            except Exception:  # noqa: BLE001
                pass
        except Exception:  # noqa: BLE001
            pass
    engine = getattr(llm, "llm_engine", None)
    if engine is not None:
        fn2 = getattr(engine, "reset_prefix_cache", None)
        if callable(fn2):
            try:
                fn2()
                return True
            except Exception:  # noqa: BLE001
                pass
    return False


def _measure(llm, prompt: str, sampling, *, n: int, label: str) -> tuple[dict, str]:
    samples: list[float] = []
    last_text = ""
    method = "unknown"
    for i in range(n):
        ms, text, method = _ttft_ms(llm, prompt, sampling)
        samples.append(ms)
        last_text = text
        print(f"  {label} {i + 1}/{n} {ms:.0f} ms", flush=True)
    return {
        "n": len(samples),
        "p50_ms": statistics.median(samples),
        "p90_ms": _percentile(samples, 0.9),
        "samples_ms": samples,
        "last_output": last_text,
    }, method


def _measure_reorder_after_abc(
    llm,
    *,
    abc_prompt: str,
    reorder_prompt: str,
    sampling,
    n: int,
    label: str,
    prompt_pair_fn=None,
) -> tuple[dict, str, bool]:
    """Each trial: clear cache → seed ABC → measure reorder once (true miss).

    For blend/LMCache, pass ``prompt_pair_fn(i) -> (abc, reorder)`` with a unique
    filler salt each trial so prior BAC/CBA entries cannot self-hit (vLLM
    ``reset_prefix_cache`` often fails while LMCache still holds blocks).
    """
    samples: list[float] = []
    last_text = ""
    method = "unknown"
    cleared = True
    for i in range(n):
        if prompt_pair_fn is not None:
            abc_i, reorder_i = prompt_pair_fn(i)
        else:
            abc_i, reorder_i = abc_prompt, reorder_prompt
        if not _reset_prefix_cache(llm):
            cleared = False
        # Repopulate ABC so we measure "reorder after prefix-hot ABC".
        _ttft_ms(llm, abc_i, sampling)
        ms, text, method = _ttft_ms(llm, reorder_i, sampling)
        samples.append(ms)
        last_text = text
        print(f"  {label} {i + 1}/{n} {ms:.0f} ms", flush=True)
    polluted = _reorder_series_polluted(samples)
    if polluted:
        print(
            f"  WARN {label}: first={samples[0]:.0f} ms vs later p50="
            f"{statistics.median(samples[1:]):.0f} ms — self-hit pollution",
            flush=True,
        )
    return (
        {
            "n": len(samples),
            "p50_ms": statistics.median(samples),
            "p90_ms": _percentile(samples, 0.9),
            "first_ms": samples[0] if samples else float("nan"),
            "samples_ms": samples,
            "series_polluted": polluted,
            "last_output": last_text,
        },
        method,
        cleared and not polluted,
    )


def _size_fillers(
    *,
    model: str,
    target_prefix_tokens: int,
    max_model_len: int,
    max_tokens: int,
    head: str,
    question: str,
) -> tuple[dict[str, str], int, str]:
    """Binary-search per-doc chars so ABC prompt ≈ target tokens."""
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(model, trust_remote_code=True)
    q_n = len(tok.encode(question, add_special_tokens=False))
    prefix_cap = max_model_len - max_tokens - q_n - 16
    want = min(target_prefix_tokens, prefix_cap)
    if want < 512:
        raise SystemExit(f"max_model_len={max_model_len} too small for TTFT bench")

    lo, hi = 400, max(4000, want * 5)
    best_fillers = _fillers_for_chars(lo)
    best_n = 0
    best_prompt = ""
    while lo <= hi:
        mid = (lo + hi) // 2
        fillers = _fillers_for_chars(mid)
        prompt = _docs(ORDERS["abc"], fillers=fillers, head=head) + question
        n = len(tok.encode(prompt, add_special_tokens=True))
        if n <= want:
            best_fillers, best_n, best_prompt = fillers, n, prompt
            lo = mid + 1
        else:
            hi = mid - 1
    print(f"  sized ABC prompt ≈ {best_n} tokens (target {want})", flush=True)
    return best_fillers, best_n, best_prompt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default=os.environ.get("SMOKE_MODEL", "Qwen/Qwen3-8B"))
    parser.add_argument("--backend", choices=("native_prefix", "blend"), required=True)
    parser.add_argument("--runs", type=int, default=10)
    parser.add_argument("--max-model-len", type=int, default=8192)
    parser.add_argument("--max-tokens", type=int, default=16)
    parser.add_argument(
        "--target-prefix-tokens",
        type=int,
        default=6000,
        help="Approximate ABC prompt tokens (matches g1_ttft scale where gap showed).",
    )
    parser.add_argument(
        "--filler-chars",
        type=int,
        default=None,
        help="If set, skip token sizing and use this many chars per doc.",
    )
    parser.add_argument("--gpu-memory-utilization", type=float, default=0.75)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if os.environ.get("CONTEXTWEAVE_ALLOW_MODEL_LOAD") != "1":
        print(
            "Refusing: set CONTEXTWEAVE_ALLOW_MODEL_LOAD=1 on the GPU host only.",
            file=sys.stderr,
        )
        return 1

    from vllm import LLM, SamplingParams

    head = (
        "You are a careful assistant. Prefer a short answer.\n"
        "Reply with only the requested value.\n\n"
    )
    question = (
        "\nWhich city is named in Document Beta? Reply with only the city name.\n/no_think"
    )

    if args.filler_chars is not None:
        fillers = _fillers_for_chars(args.filler_chars)
        prompt_tokens = None
        filler_chars = args.filler_chars
    else:
        fillers, prompt_tokens, _ = _size_fillers(
            model=args.model,
            target_prefix_tokens=args.target_prefix_tokens,
            max_model_len=args.max_model_len,
            max_tokens=args.max_tokens,
            head=head,
            question=question,
        )
        filler_chars = len(fillers["A"])

    prompts = {
        key: _docs(order, fillers=fillers, head=head) + question
        for key, order in ORDERS.items()
    }

    def _blend_prompt_pair(order_key: str):
        """Unique filler salt per trial so LMCache cannot BAC/CBA self-hit."""

        def _fn(i: int) -> tuple[str, str]:
            salted = _fillers_for_chars(filler_chars, salt=f"t{i}-{order_key}-")
            abc = _docs(ORDERS["abc"], fillers=salted, head=head) + question
            reo = _docs(ORDERS[order_key], fillers=salted, head=head) + question
            return abc, reo

        return _fn

    kwargs: dict = {
        "model": args.model,
        "max_model_len": args.max_model_len,
        "gpu_memory_utilization": args.gpu_memory_utilization,
        "trust_remote_code": True,
        # Match working g1_ttft / reorder_gap (no enforce_eager).
    }
    if args.backend == "native_prefix":
        kwargs["enable_prefix_caching"] = True
    else:
        from vllm.config import KVTransferConfig

        host = os.environ.get("LMCACHE_MP_HOST", "127.0.0.1")
        port = int(os.environ.get("LMCACHE_MP_PORT", "5555"))
        kwargs["enable_prefix_caching"] = False
        kwargs["enforce_eager"] = True  # blend path was more stable eager
        kwargs["kv_transfer_config"] = KVTransferConfig(
            kv_connector="LMCacheMPConnector",
            kv_connector_module_path="lmcache.integration.vllm.lmcache_mp_connector",
            kv_role="kv_both",
            kv_connector_extra_config={
                "lmcache.mp.host": f"tcp://{host}",
                "lmcache.mp.port": port,
            },
        )

    print(
        f"matched TTFT backend={args.backend} runs={args.runs} "
        f"target_tokens={args.target_prefix_tokens}",
        flush=True,
    )
    llm = LLM(**kwargs)
    sampling = SamplingParams(temperature=0.0, max_tokens=args.max_tokens)

    print("  [seed abc] discarded", flush=True)
    _ttft_ms(llm, prompts["abc"], sampling)

    results: dict[str, dict] = {}
    ttft_method = "wall_clock_generate"

    warm_abc, ttft_method = _measure(
        llm, prompts["abc"], sampling, n=args.runs, label="warm_abc"
    )
    results["warm_abc"] = warm_abc

    # Critical: do NOT measure bac×N without clearing — trial 2..N become BAC self-hits
    # (previous false harness_ok=False with warm≈reorder while cold_vs_warm≈2.5×).
    # Blend: also salt fillers per trial — LMCache ignores failed reset_prefix_cache.
    blend_pairs = args.backend == "blend"
    warm_bac, ttft_method, cleared_bac = _measure_reorder_after_abc(
        llm,
        abc_prompt=prompts["abc"],
        reorder_prompt=prompts["bac"],
        sampling=sampling,
        n=args.runs,
        label="warm_bac",
        prompt_pair_fn=_blend_prompt_pair("bac") if blend_pairs else None,
    )
    results["warm_bac"] = warm_bac

    warm_cba, ttft_method, cleared_cba = _measure_reorder_after_abc(
        llm,
        abc_prompt=prompts["abc"],
        reorder_prompt=prompts["cba"],
        sampling=sampling,
        n=args.runs,
        label="warm_cba",
        prompt_pair_fn=_blend_prompt_pair("cba") if blend_pairs else None,
    )
    results["warm_cba"] = warm_cba
    reorder_polluted = bool(
        results["warm_bac"].get("series_polluted")
        or results["warm_cba"].get("series_polluted")
    )
    prefix_cache_reset_ok = cleared_bac and cleared_cba and not reorder_polluted
    if not prefix_cache_reset_ok:
        print(
            "WARN: reorder series may be polluted "
            "(reset failed and/or first≫later p50 self-hits)",
            flush=True,
        )

    cold_samples: list[float] = []
    cold_text = ""
    for i in range(args.runs):
        _reset_prefix_cache(llm)
        cold_prompt = f"[cold-nonce-{i}-{time.time_ns()}]\n" + prompts["abc"]
        ms, text, ttft_method = _ttft_ms(llm, cold_prompt, sampling)
        cold_samples.append(ms)
        cold_text = text
        print(f"  cold_abc {i + 1}/{args.runs} {ms:.0f} ms", flush=True)
    results["cold_abc"] = {
        "n": len(cold_samples),
        "p50_ms": statistics.median(cold_samples),
        "p90_ms": _percentile(cold_samples, 0.9),
        "samples_ms": cold_samples,
        "last_output": cold_text,
    }

    del llm

    warm_abc_p50 = results["warm_abc"]["p50_ms"]
    warm_reorder_p50 = statistics.median(
        [results["warm_bac"]["p50_ms"], results["warm_cba"]["p50_ms"]]
    )
    reorder_gap = warm_reorder_p50 / warm_abc_p50 if warm_abc_p50 > 0 else None
    cold_vs_warm = (
        results["cold_abc"]["p50_ms"] / warm_abc_p50 if warm_abc_p50 > 0 else None
    )
    harness_reorder_gap_ok = reorder_gap is not None and reorder_gap >= 1.15

    payload = {
        "gate": "G1-matched-ttft",
        "backend": args.backend,
        "model": args.model,
        "runs": args.runs,
        "target_prefix_tokens": args.target_prefix_tokens,
        "abc_prompt_tokens": prompt_tokens,
        "ttft_method": ttft_method,
        "protocol": (
            "seed_abc → warm_abc×N → "
            "for reorder: reset_prefix_cache → seed abc → measure bac/cba ×N "
            "(blend: unique filler salt per trial) → "
            "cold_abc×N (reset + leading nonce)"
        ),
        "prefix_cache_reset_ok": prefix_cache_reset_ok,
        "reorder_series_polluted": reorder_polluted,
        "scenarios": results,
        "warm_abc_p50_ms": warm_abc_p50,
        "warm_reorder_p50_ms": warm_reorder_p50,
        "warm_reorder_first_ms": statistics.median(
            [
                results["warm_bac"].get("first_ms", float("nan")),
                results["warm_cba"].get("first_ms", float("nan")),
            ]
        ),
        "reorder_vs_warm_abc": reorder_gap,
        "cold_vs_warm_abc": cold_vs_warm,
        "harness_reorder_gap_ok": harness_reorder_gap_ok and prefix_cache_reset_ok,
        "note": (
            "harness_reorder_gap_ok requires reorder ≥1.15× warm ABC and no "
            "self-hit pollution (first≫later). "
            "Gate E: blend warm_reorder ≤ 0.85 × native warm_reorder. "
            "Do not cite gate_e if reorder_series_polluted."
        ),
    }
    if args.out:
        args.out.write_text(json.dumps(payload, indent=2) + "\n")
        print(f"Wrote {args.out}", flush=True)
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        for scen, r in results.items():
            print(f"{scen}: p50={r['p50_ms']:.0f} p90={r['p90_ms']:.0f} n={r['n']}")
        print(
            f"reorder_vs_warm_abc={reorder_gap} cold_vs_warm={cold_vs_warm} "
            f"harness_ok={harness_reorder_gap_ok}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
