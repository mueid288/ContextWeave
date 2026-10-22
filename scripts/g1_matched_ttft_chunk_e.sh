#!/usr/bin/env bash
# Stage E on chunk+separator prompts (native then blend). GPU only.
#   export CONTEXTWEAVE_ALLOW_MODEL_LOAD=1
#   bash scripts/g1_matched_ttft_chunk_e.sh
set -euo pipefail

if [[ "${CONTEXTWEAVE_ALLOW_MODEL_LOAD:-}" != "1" ]]; then
  echo "Refusing: set CONTEXTWEAVE_ALLOW_MODEL_LOAD=1 on the GPU host only."
  exit 1
fi

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

export PYTHONHASHSEED=0
export VLLM_WORKER_MULTIPROC_METHOD=spawn
export LMCACHE_MP_HOST="${LMCACHE_MP_HOST:-127.0.0.1}"
export LMCACHE_MP_PORT="${LMCACHE_MP_PORT:-5555}"
HTTP_PORT="${LMCACHE_HTTP_PORT:-18080}"
LOG="${LMCACHE_MP_LOG:-/tmp/lmcache_matched_blend.log}"
READY_TIMEOUT_S="${LMCACHE_READY_TIMEOUT_S:-90}"
MAX_LEN="${TTFT_MAX_MODEL_LEN:-16384}"
TARGET="${TTFT_TARGET_TOKENS:-12000}"
RUNS="${TTFT_RUNS:-10}"
GPU_UTIL="${TTFT_GPU_UTIL:-0.88}"

echo "=== native_prefix chunk_sep TTFT ==="
python scripts/g1_matched_ttft_bench.py --backend native_prefix --runs "$RUNS" \
  --max-model-len "$MAX_LEN" --target-prefix-tokens "$TARGET" \
  --gpu-memory-utilization "$GPU_UTIL" \
  --out g1_ttft_native_12k_chunks.json

pkill -f 'lmcache server' 2>/dev/null || true
sleep 2
rm -f "$LOG"
echo "=== lmcache blend server ==="
lmcache server \
  --host 127.0.0.1 \
  --port "$LMCACHE_MP_PORT" \
  --http-host 127.0.0.1 \
  --http-port "$HTTP_PORT" \
  --l1-size-gb "${LMCACHE_L1_GB:-8}" \
  --eviction-policy LRU \
  --engine-type blend \
  --chunk-size 256 \
  --supported-transfer-mode lmcache_driven \
  >"$LOG" 2>&1 &
SERVER_PID=$!
ready=0
deadline=$((SECONDS + READY_TIMEOUT_S))
while (( SECONDS < deadline )); do
  if ! kill -0 "$SERVER_PID" 2>/dev/null; then
    echo "lmcache server exited:"; cat "$LOG" || true; exit 2
  fi
  if grep -qE 'ZMQ cache server is running|cache server is running' "$LOG" 2>/dev/null; then
    ready=1; break
  fi
  sleep 1
done
if [[ "$ready" -ne 1 ]]; then
  echo "not ready after ${READY_TIMEOUT_S}s:"; cat "$LOG" || true; exit 2
fi
echo "lmcache ready pid=$SERVER_PID"

echo "=== blend chunk_sep TTFT ==="
python scripts/g1_matched_ttft_bench.py --backend blend --runs "$RUNS" \
  --max-model-len "$MAX_LEN" --target-prefix-tokens "$TARGET" \
  --gpu-memory-utilization "$GPU_UTIL" \
  --out g1_ttft_blend_12k_chunks.json

python - <<'PY'
import json
n=json.load(open("g1_ttft_native_12k_chunks.json"))
b=json.load(open("g1_ttft_blend_12k_chunks.json"))
nr, br = n["warm_reorder_p50_ms"], b["warm_reorder_p50_ms"]
print("prompt_format", b.get("prompt_format"), "polluted", b.get("reorder_series_polluted"))
print("native_reorder", nr, "blend_reorder", br)
print("speedup", (nr/br) if br else None)
print("gate_e", br < 0.85*nr if nr and br else None)
print("blend warm_abc", b["warm_abc_p50_ms"], "blend cold", b["scenarios"]["cold_abc"]["p50_ms"])
PY
