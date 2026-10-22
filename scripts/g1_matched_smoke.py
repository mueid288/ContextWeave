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
    out = llm.generate(
        ["Reply with exactly: smoke-ok"],
        SamplingParams(temperature=0.0, max_tokens=8),
    )
    text = out[0].outputs[0].text if out and out[0].outputs else ""
    print("SMOKE_OUTPUT:", repr(text), flush=True)
    ok = "smoke-ok" in text.lower().replace(" ", "")
    print("GATE_B:", "PASS" if ok else "FAIL", flush=True)
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
