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
export VLLM_WORKER_MULTIPROC_METHOD=spawn
export SMOKE_MODEL="${SMOKE_MODEL:-Qwen/Qwen3-8B}"
export CONTEXTWEAVE_ALLOW_MODEL_LOAD=1

# Real .py path required — vLLM spawn cannot re-exec a bash heredoc.
exec python scripts/g1_matched_smoke.py
