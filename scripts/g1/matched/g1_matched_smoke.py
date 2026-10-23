#!/usr/bin/env python3
"""Gate B: plain vLLM smoke (no LMCache). GPU only — must be a real .py file.

vLLM spawn workers cannot re-exec a bash heredoc ``<stdin>`` path.
"""

from __future__ import annotations

import os
import sys


def main() -> int:
    if os.environ.get("CONTEXTWEAVE_ALLOW_MODEL_LOAD") != "1":
        print(
            "Refusing: set CONTEXTWEAVE_ALLOW_MODEL_LOAD=1 on the GPU host only.",
            file=sys.stderr,
        )
        return 1

    os.environ.setdefault("VLLM_WORKER_MULTIPROC_METHOD", "spawn")
    from vllm import LLM, SamplingParams

    model = os.environ.get("SMOKE_MODEL", "Qwen/Qwen3-8B")
    print(f"=== Gate B smoke model={model} ===", flush=True)
    llm = LLM(
        model=model,
        max_model_len=2048,
        trust_remote_code=True,
        enforce_eager=True,
        gpu_memory_utilization=0.5,
    )
    # Qwen3 burns tokens on thinking unless /no_think (+ optional enable_thinking=False).
    prompt = (
        "Reply with exactly the two words smoke-ok and nothing else.\n/no_think"
    )
    sp_kwargs: dict = {"temperature": 0.0, "max_tokens": 16}
    try:
        params = SamplingParams(**sp_kwargs, extra_args={"enable_thinking": False})
    except TypeError:
        params = SamplingParams(**sp_kwargs)
    out = llm.generate([prompt], params)
    text = out[0].outputs[0].text if out and out[0].outputs else ""
    print("SMOKE_OUTPUT:", repr(text), flush=True)
    compact = "".join(text.lower().split())
    ok = "smoke-ok" in compact or "smokeok" in compact
    print("GATE_B:", "PASS" if ok else "FAIL", flush=True)
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
