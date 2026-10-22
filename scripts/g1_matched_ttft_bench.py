#!/usr/bin/env python3
"""G1 matched-pin TTFT bench — streaming first-token when available (GPU).

Native prefix protocol (critical — prior version was wrong):
  1. Seed ABC once (discarded)
  2. Measure warm_abc × N  (exact repeat → prefix hit)
  3. Measure warm_bac × N  (reorder, **no** BAC seed → should miss)
  4. Measure warm_cba × N  (reorder, no CBA seed)
  5. Measure cold_abc × N  (unique leading nonce so almost no prefix hit)

A prior bug warmed each scenario's own prompt before measuring it, so
warm_bac was a self-hit and looked identical to warm_abc.

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
    """Return (ttft_ms, text, method). Prefer vLLM request metrics; else wall clock."""
    t0 = time.perf_counter()
    outs = llm.generate([prompt], sampling, use_tqdm=False)
    wall = (time.perf_counter() - t0) * 1000.0
    text = outs[0].outputs[0].text.strip() if outs and outs[0].outputs else ""
    metrics = getattr(outs[0], "metrics", None) if outs else None
    if metrics is not None:
        ft = getattr(metrics, "first_token_time", None)
        fs = getattr(metrics, "first_scheduled_time", None)
        if ft is not None and fs is not None:
            return (ft - fs) * 1000.0, text, "vllm_metrics_first_token"
    return wall, text, "wall_clock_generate"


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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default=os.environ.get("SMOKE_MODEL", "Qwen/Qwen3-8B"))
    parser.add_argument("--backend", choices=("native_prefix", "blend"), required=True)
    parser.add_argument("--runs", type=int, default=10)
    parser.add_argument("--max-model-len", type=int, default=8192)
    parser.add_argument("--max-tokens", type=int, default=8)
    parser.add_argument(
        "--filler-chars",
        type=int,
        default=2500,
        help="Per-document filler chars (distinct per doc so orders diverge early).",
    )
    parser.add_argument("--gpu-memory-utilization", type=float, default=0.75)
    parser.add_argument("--out", type=Path, default=None, help="Write clean JSON payload here")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if os.environ.get("CONTEXTWEAVE_ALLOW_MODEL_LOAD") != "1":
        print(
            "Refusing: set CONTEXTWEAVE_ALLOW_MODEL_LOAD=1 on the GPU host only.",
            file=sys.stderr,
        )
        return 1

    from vllm import LLM, SamplingParams

    # Distinct fillers so ABC vs BAC diverge at the first document body,
    # not only at a short header.
    fillers = {
        "A": ("alpha-only filler sentence for prefix bench. " * 200)[: args.filler_chars],
        "B": ("beta-unique filler sentence for prefix bench. " * 200)[: args.filler_chars],
        "C": ("gamma-unique filler sentence for prefix bench. " * 200)[: args.filler_chars],
    }
    head = (
        "You are a careful assistant. Prefer a short answer.\n"
        "Reply with only the requested value.\n\n"
    )
    question = (
        "\nWhich city is named in Document Beta? Reply with only the city name.\n/no_think"
    )
    prompts = {
        key: _docs(order, fillers=fillers, head=head) + question
        for key, order in ORDERS.items()
    }

    kwargs: dict = {
        "model": args.model,
        "max_model_len": args.max_model_len,
        "gpu_memory_utilization": args.gpu_memory_utilization,
        "trust_remote_code": True,
        "enforce_eager": True,
    }
    if args.backend == "native_prefix":
        kwargs["enable_prefix_caching"] = True
    else:
        from vllm.config import KVTransferConfig

        host = os.environ.get("LMCACHE_MP_HOST", "127.0.0.1")
        port = int(os.environ.get("LMCACHE_MP_PORT", "5555"))
        kwargs["enable_prefix_caching"] = False
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
        f"filler_chars/doc={args.filler_chars}",
        flush=True,
    )
    llm = LLM(**kwargs)
    sampling = SamplingParams(temperature=0.0, max_tokens=args.max_tokens)

    # --- Protocol ---
    print("  [seed abc] discarded", flush=True)
    _ttft_ms(llm, prompts["abc"], sampling)

    results: dict[str, dict] = {}
    ttft_method = "unknown"

    warm_abc, ttft_method = _measure(
        llm, prompts["abc"], sampling, n=args.runs, label="warm_abc"
    )
    results["warm_abc"] = warm_abc

    # Reorders: do NOT seed bac/cba first.
    warm_bac, ttft_method = _measure(
        llm, prompts["bac"], sampling, n=args.runs, label="warm_bac"
    )
    results["warm_bac"] = warm_bac

    warm_cba, ttft_method = _measure(
        llm, prompts["cba"], sampling, n=args.runs, label="warm_cba"
    )
    results["warm_cba"] = warm_cba

    # Cold: unique leading nonce so shared prefix is tiny.
    cold_samples: list[float] = []
    cold_text = ""
    for i in range(args.runs):
        cold_prompt = (
            f"[cold-nonce-{i}-{time.time_ns()}]\n" + prompts["abc"]
        )
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
    reorder_gap = (
        warm_reorder_p50 / warm_abc_p50 if warm_abc_p50 > 0 else None
    )
    # Native harness sanity: reorder should be ≥15% slower than warm ABC.
    harness_reorder_gap_ok = (
        reorder_gap is not None and reorder_gap >= 1.15
    )

    payload = {
        "gate": "G1-matched-ttft",
        "backend": args.backend,
        "model": args.model,
        "runs": args.runs,
        "filler_chars_per_doc": args.filler_chars,
        "ttft_method": ttft_method,
        "protocol": (
            "seed_abc → warm_abc×N → warm_bac×N (no seed) → "
            "warm_cba×N (no seed) → cold_abc×N (leading nonce)"
        ),
        "scenarios": results,
        "warm_abc_p50_ms": warm_abc_p50,
        "warm_reorder_p50_ms": warm_reorder_p50,
        "reorder_vs_warm_abc": reorder_gap,
        "harness_reorder_gap_ok": harness_reorder_gap_ok,
        "note": (
            "For native_prefix, harness_reorder_gap_ok must be true before "
            "Gate E is meaningful. Gate E: blend warm_reorder_p50 ≤ 0.85 × "
            "same-session native warm_reorder_p50."
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
            f"reorder_vs_warm_abc={reorder_gap} "
            f"harness_ok={harness_reorder_gap_ok}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
