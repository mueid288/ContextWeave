#!/usr/bin/env python3
"""G1 quality slice — answer preservation: full prefill vs native prefix (GPU only).

No LMCache. Uses the stack that already works on Colab (vLLM + Qwen3-8B).

  export CONTEXTWEAVE_ALLOW_MODEL_LOAD=1
  python scripts/g1_quality_bench.py --json | tee g1_quality.json

Gold answers are private facts in the shared docs. We report:
  - exact / contains match vs gold
  - agreement between full_prefill and prefix_cache outputs
"""

from __future__ import annotations

import argparse
import json
import os
import re
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


CASES = [
    {
        "id": "alpha_code",
        "question": "What is the secret code of Document Alpha? Reply with only the code.",
        "gold": "ALPHA-9173",
    },
    {
        "id": "beta_city",
        "question": "Which city is named in Document Beta? Reply with only the city name.",
        "gold": "Karachi",
    },
    {
        "id": "gamma_year",
        "question": "What year is stated in Document Gamma? Reply with only the year.",
        "gold": "2019",
    },
]


def _build_shared_docs(*, filler_chars: int) -> str:
    """Long shared docs with planted private facts (receiver-necessary)."""
    filler = ("contextweave quality filler sentence. " * 200)[:filler_chars]
    return (
        "You are a careful assistant. Use only the documents. "
        "If missing, say unknown. Prefer a short answer.\n\n"
        f"### Document Alpha\nSecret code: ALPHA-9173.\n{filler}\n\n"
        f"### Document Beta\nNamed city: Karachi.\n{filler}\n\n"
        f"### Document Gamma\nStated year: 2019.\n{filler}\n\n"
    )


def _normalize(text: str) -> str:
    t = text.strip().lower()
    # Drop common chatter / thinking tails for Qwen-style outputs.
    t = re.split(r"\n+", t)[0]
    t = re.sub(r"[^a-z0-9\-]+", " ", t).strip()
    return t


def _score(output: str, gold: str) -> dict:
    norm_out = _normalize(output)
    norm_gold = _normalize(gold)
    exact = norm_out == norm_gold
    contains = norm_gold in norm_out
    return {
        "exact": exact,
        "contains": contains,
        "output": output,
        "normalized": norm_out,
    }


def _run_mode(
    *,
    mode: str,
    enable_prefix_caching: bool,
    model: str,
    max_model_len: int,
    max_tokens: int,
    prompts: list[str],
) -> dict:
    from vllm import LLM, SamplingParams

    llm = LLM(
        model=model,
        max_model_len=max_model_len,
        trust_remote_code=True,
        enable_prefix_caching=enable_prefix_caching,
    )
    params = SamplingParams(max_tokens=max_tokens, temperature=0.0)
    # Warm shared prefix once when caching is on.
    if enable_prefix_caching and prompts:
        llm.generate([prompts[0]], SamplingParams(max_tokens=1, temperature=0.0))

    times_ms: list[float] = []
    texts: list[str] = []
    for prompt in prompts:
        t0 = time.perf_counter()
        outs = llm.generate([prompt], params)
        times_ms.append((time.perf_counter() - t0) * 1000.0)
        texts.append(outs[0].outputs[0].text.strip())
    del llm
    return {
        "mode": mode,
        "enable_prefix_caching": enable_prefix_caching,
        "ttft_ms": times_ms,
        "p50_ms": statistics.median(times_ms),
        "outputs": texts,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default=os.environ.get("SMOKE_MODEL", "Qwen/Qwen3-8B"))
    parser.add_argument("--max-model-len", type=int, default=8192)
    parser.add_argument("--max-tokens", type=int, default=32)
    parser.add_argument("--filler-chars", type=int, default=2500)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if os.environ.get("CONTEXTWEAVE_ALLOW_MODEL_LOAD") != "1":
        print(
            "Refusing: set CONTEXTWEAVE_ALLOW_MODEL_LOAD=1 on the GPU host only.",
            file=sys.stderr,
        )
        return 1

    docs = _build_shared_docs(filler_chars=args.filler_chars)
    prompts = [docs + c["question"] for c in CASES]
    print(
        f"Quality bench model={args.model} n={len(CASES)} "
        f"shared_chars={len(docs)}",
        flush=True,
    )

    results = []
    for mode, enable in (
        ("full_prefill", False),
        ("prefix_cache", True),
    ):
        print(f"=== {mode} ===", flush=True)
        results.append(
            _run_mode(
                mode=mode,
                enable_prefix_caching=enable,
                model=args.model,
                max_model_len=args.max_model_len,
                max_tokens=args.max_tokens,
                prompts=prompts,
            )
        )

    by_mode = {r["mode"]: r for r in results}
    per_case = []
    for i, case in enumerate(CASES):
        full_sc = _score(by_mode["full_prefill"]["outputs"][i], case["gold"])
        pref_sc = _score(by_mode["prefix_cache"]["outputs"][i], case["gold"])
        agree = _normalize(full_sc["output"]) == _normalize(pref_sc["output"])
        per_case.append(
            {
                "id": case["id"],
                "gold": case["gold"],
                "full_prefill": full_sc,
                "prefix_cache": pref_sc,
                "modes_agree": agree,
            }
        )

    n = len(per_case)
    payload = {
        "gate": "G1-quality-answer-preservation",
        "model": args.model,
        "max_model_len": args.max_model_len,
        "shared_docs_chars": len(docs),
        "latency": {
            "full_prefill_p50_ms": by_mode["full_prefill"]["p50_ms"],
            "prefix_cache_p50_ms": by_mode["prefix_cache"]["p50_ms"],
        },
        "cases": per_case,
        "summary": {
            "full_contains_rate": sum(c["full_prefill"]["contains"] for c in per_case) / n,
            "prefix_contains_rate": sum(c["prefix_cache"]["contains"] for c in per_case) / n,
            "modes_agree_rate": sum(c["modes_agree"] for c in per_case) / n,
        },
        "pass_heuristic": (
            sum(c["full_prefill"]["contains"] for c in per_case) / n >= 0.66
            and sum(c["modes_agree"] for c in per_case) / n >= 0.66
        ),
        "note": (
            "pass_heuristic: full prefill finds gold on ≥2/3 cases AND "
            "prefix_cache agrees with full on ≥2/3 (normalized)."
        ),
    }

    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        s = payload["summary"]
        print(
            f"full_contains={s['full_contains_rate']:.2f} "
            f"prefix_contains={s['prefix_contains_rate']:.2f} "
            f"agree={s['modes_agree_rate']:.2f} "
            f"pass={payload['pass_heuristic']}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
