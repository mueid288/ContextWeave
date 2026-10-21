#!/usr/bin/env bash
# G1 CacheBlend via LMCache MP + blend engine (avoids broken in-process path on vLLM 0.32).
# Run ONLY on GPU host.
set -euo pipefail

if [[ "${CONTEXTWEAVE_ALLOW_MODEL_LOAD:-}" != "1" ]]; then
  echo "Refusing: set CONTEXTWEAVE_ALLOW_MODEL_LOAD=1 on the GPU host only."
  exit 1
fi

export PYTHONHASHSEED=0
export VLLM_WORKER_MULTIPROC_METHOD=spawn

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PORT="${LMCACHE_MP_PORT:-5555}"
LOG="${LMCACHE_MP_LOG:-/tmp/lmcache_blend_server.log}"

cleanup() {
  if [[ -n "${SERVER_PID:-}" ]] && kill -0 "$SERVER_PID" 2>/dev/null; then
    echo "Stopping lmcache server pid=$SERVER_PID"
    kill "$SERVER_PID" 2>/dev/null || true
    wait "$SERVER_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT

echo "=== starting lmcache server (engine-type=blend) on :$PORT ==="
lmcache server \
  --host 127.0.0.1 \
  --port "$PORT" \
  --l1-size-gb "${LMCACHE_L1_GB:-8}" \
  --eviction-policy LRU \
  --engine-type blend \
  --chunk-size 256 \
  --supported-transfer-mode auto \
  >"$LOG" 2>&1 &
SERVER_PID=$!
sleep 3
if ! kill -0 "$SERVER_PID" 2>/dev/null; then
  echo "lmcache server failed to start. Log:"
  cat "$LOG" || true
  exit 2
fi
echo "lmcache server pid=$SERVER_PID (log: $LOG)"

export LMCACHE_MP_HOST="127.0.0.1"
export LMCACHE_MP_PORT="$PORT"

python scripts/g1_cacheblend_mp_bench.py --json "$@" | tee g1_cacheblend_mp.json
