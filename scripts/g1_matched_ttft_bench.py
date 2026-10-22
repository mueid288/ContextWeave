#!/usr/bin/env python3
"""G1 matched-pin TTFT bench — streaming first-token when available (GPU).

Scenarios (1 discarded warmup + ``--runs`` measured):
  cold_abc, warm_abc, warm_bac, warm_cba

Backends:
  native_prefix — vLLM enable_prefix_caching=True, no LMCache
  blend — LMCacheMPConnector (blend server must already be running)

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

SCENARIOS = ("cold_abc", "warm_abc", "warm_bac", "warm_cba")
ORDERS = {
    "abc": ("A", "B", "C"),
    "bac": ("B", "A", "C"),
    "cba": ("C", "B", "A"),
}


def _docs(filler: str, order: tuple[str, ...]) -> str:
    blocks = {
        "A": f"### Document Alpha\nSecret code: ALPHA-9173.\n{filler}\n",
        "B": f"### Document Beta\nNamed city: Karachi.\n{filler}\n",
        "C": f"### Document Gamma\nStated year: 2019.\n{filler}\n",
    }
    head = "You are a careful assistant. Prefer a short answer.\n\n"
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default=os.environ.get("SMOKE_MODEL", "Qwen/Qwen3-8B"))
    parser.add_argument("--backend", choices=("native_prefix", "blend"), required=True)
    parser.add_argument("--runs", type=int, default=10)
    parser.add_argument("--max-model-len", type=int, default=8192)
    parser.add_argument("--max-tokens", type=int, default=8)
    parser.add_argument("--filler-chars", type=int, default=2000)
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

    filler = ("matched ttft filler sentence. " * 200)[: args.filler_chars]
    question = "Which city is named in Document Beta? Reply with only the city name."
    prompts = {
        "abc": _docs(filler, ORDERS["abc"]) + question,
        "bac": _docs(filler, ORDERS["bac"]) + question,
        "cba": _docs(filler, ORDERS["cba"]) + question,
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

    print(f"matched TTFT backend={args.backend} runs={args.runs}", flush=True)
    llm = LLM(**kwargs)
    sampling = SamplingParams(temperature=0.0, max_tokens=args.max_tokens)

    # Map scenarios to prompt keys; cold vs warm is timing/cache state.
    scenario_prompt = {
        "cold_abc": "abc",
        "warm_abc": "abc",
        "warm_bac": "bac",
        "warm_cba": "cba",
    }

    results: dict[str, dict] = {}
    ttft_method = "unknown"
    for scen in SCENARIOS:
        key = scenario_prompt[scen]
        prompt = prompts[key]
        # One discarded warmup
        _ttft_ms(llm, prompt, sampling)
        samples: list[float] = []
        last_text = ""
        for i in range(args.runs):
            # For cold_abc only: use a unique suffix so prefix cache cannot hit.
            p = prompt
            if scen == "cold_abc":
                p = prompt + f"\n[run-nonce {i}]"
            ms, text, method = _ttft_ms(llm, p, sampling)
            ttft_method = method
            samples.append(ms)
            last_text = text
            print(f"  {scen} {i + 1}/{args.runs} {ms:.0f} ms", flush=True)
        results[scen] = {
            "n": len(samples),
            "p50_ms": statistics.median(samples),
            "p90_ms": _percentile(samples, 0.9),
            "samples_ms": samples,
            "last_output": last_text,
        }

    del llm
    native_reorder = results["warm_bac"]["p50_ms"]
    blend_or_warm = statistics.median(
        [results["warm_bac"]["p50_ms"], results["warm_cba"]["p50_ms"]]
    )
    payload = {
        "gate": "G1-matched-ttft",
        "backend": args.backend,
        "model": args.model,
        "runs": args.runs,
        "ttft_method": ttft_method,
        "scenarios": results,
        "warm_reorder_p50_ms": blend_or_warm,
        "note": (
            "Compare blend warm_reorder_p50 to same-session native_prefix "
            "warm_bac/cba p50 for Gate E (≥15% faster)."
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
    return 0


if __name__ == "__main__":
    sys.exit(main())
