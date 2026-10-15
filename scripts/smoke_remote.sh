#!/usr/bin/env bash
# Run ONLY on a rented GPU host. Refuses to start without the allow flag.
set -euo pipefail

if [[ "${CONTEXTWEAVE_ALLOW_MODEL_LOAD:-}" != "1" ]]; then
  echo "Refusing: set CONTEXTWEAVE_ALLOW_MODEL_LOAD=1 on the cloud GPU host only."
  echo "See Docs/local-safety.md and Docs/cloud-gpu-rental.md"
  exit 1
fi

if ! command -v nvidia-smi >/dev/null 2>&1; then
  echo "nvidia-smi not found — this does not look like a GPU host."
  exit 1
fi

echo "=== nvidia-smi ==="
nvidia-smi

export MODEL="${SMOKE_MODEL:-Qwen/Qwen3-8B}"
export MAX_LEN="${SMOKE_MAX_MODEL_LEN:-4096}"

python - <<'PY'
import os
import sys
from vllm import LLM, SamplingParams

model = os.environ["MODEL"]
max_len = int(os.environ["MAX_LEN"])
print("Loading", model)

# NOTE: trust_remote_code=True poses security risks from arbitrary remote code execution.
# For production use, revision pinning (e.g., revision="<commit-sha>") should be added.
llm = LLM(model=model, max_model_len=max_len, trust_remote_code=True)
params = SamplingParams(max_tokens=32, temperature=0.0)
outs = llm.generate(["Reply with exactly: smoke-ok"], params)
text = outs[0].outputs[0].text.strip()
print("OUTPUT:", text)
# Require the exact smoke token (case-insensitive). Non-empty junk must not pass.
if "smoke-ok" in text.lower():
    print("SMOKE_PASS")
else:
    print("SMOKE_FAIL")
    sys.exit(1)
PY
