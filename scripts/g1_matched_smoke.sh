#!/usr/bin/env bash
# Gate B: plain vLLM smoke (no LMCache). GPU only.
set -euo pipefail

if [[ "${CONTEXTWEAVE_ALLOW_MODEL_LOAD:-}" != "1" ]]; then
  echo "Refusing: set CONTEXTWEAVE_ALLOW_MODEL_LOAD=1 on the GPU host only."
  exit 1
fi

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PYTHONHASHSEED=0
MODEL="${SMOKE_MODEL:-Qwen/Qwen3-8B}"

python - <<PY
import os, sys
os.environ["CONTEXTWEAVE_ALLOW_MODEL_LOAD"] = "1"
from vllm import LLM, SamplingParams
model = os.environ.get("SMOKE_MODEL", "${MODEL}")
print(f"=== Gate B smoke model={model} ===", flush=True)
llm = LLM(model=model, max_model_len=2048, trust_remote_code=True, enforce_eager=True, gpu_memory_utilization=0.5)
out = llm.generate(["Reply with exactly: smoke-ok"], SamplingParams(temperature=0.0, max_tokens=8))
text = out[0].outputs[0].text if out and out[0].outputs else ""
print("SMOKE_OUTPUT:", repr(text), flush=True)
ok = "smoke" in text.lower() or "ok" in text.lower()
print("GATE_B:", "PASS" if ok else "FAIL", flush=True)
sys.exit(0 if ok else 2)
PY
