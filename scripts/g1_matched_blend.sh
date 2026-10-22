#!/usr/bin/env bash
# Start lmcache blend server + run matched quality (control then blend) then optional TTFT.
# Stages C → D; Stage E only if D passes (set RUN_TTFT=1).
set -euo pipefail

if [[ "${CONTEXTWEAVE_ALLOW_MODEL_LOAD:-}" != "1" ]]; then
  echo "Refusing: set CONTEXTWEAVE_ALLOW_MODEL_LOAD=1 on the GPU host only."
  exit 1
fi

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
# shellcheck source=g1_lmcache_cmd.sh
source "$ROOT/scripts/g1_lmcache_cmd.sh"

export PYTHONHASHSEED=0
export VLLM_WORKER_MULTIPROC_METHOD=spawn
export LMCACHE_MP_HOST="${LMCACHE_MP_HOST:-127.0.0.1}"
export LMCACHE_MP_PORT="${LMCACHE_MP_PORT:-5555}"
HTTP_PORT="${LMCACHE_HTTP_PORT:-18080}"
LOG="${LMCACHE_MP_LOG:-/tmp/lmcache_matched_blend.log}"
READY_TIMEOUT_S="${LMCACHE_READY_TIMEOUT_S:-90}"

cleanup() {
  if [[ -n "${SERVER_PID:-}" ]] && kill -0 "$SERVER_PID" 2>/dev/null; then
    echo "Stopping lmcache server pid=$SERVER_PID"
    kill "$SERVER_PID" 2>/dev/null || true
    wait "$SERVER_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT

start_server() {
  local eng="$1"
  if [[ -n "${SERVER_PID:-}" ]] && kill -0 "$SERVER_PID" 2>/dev/null; then
    kill "$SERVER_PID" 2>/dev/null || true
    wait "$SERVER_PID" 2>/dev/null || true
  fi
  rm -f "$LOG"
  SERVER_PID="$(start_lmcache_server "$eng" "$LOG" 127.0.0.1 "$LMCACHE_MP_PORT" "$HTTP_PORT" "${LMCACHE_L1_GB:-8}")"
  if [[ -z "$SERVER_PID" ]]; then
    echo "failed to start lmcache. Log:"; cat "$LOG" || true; exit 2
  fi
  local ready=0
  local deadline=$((SECONDS + READY_TIMEOUT_S))
  while (( SECONDS < deadline )); do
    if ! kill -0 "$SERVER_PID" 2>/dev/null; then
      echo "lmcache server exited. Log:"; cat "$LOG" || true; exit 2
    fi
    if grep -qE 'address already in use|Address already in use|unrecognized arguments|error:' "$LOG" 2>/dev/null; then
      # Allow brief race before usage error is fatal
      if grep -qE 'unrecognized arguments|error:' "$LOG" 2>/dev/null; then
        echo "lmcache server error. Log:"; cat "$LOG" || true; exit 2
      fi
    fi
    if grep -qE 'ZMQ cache server is running|cache server is running|Uvicorn running|Application startup complete' "$LOG" 2>/dev/null; then
      ready=1; break
    fi
    curl -fsS "http://127.0.0.1:${HTTP_PORT}/healthcheck" >/dev/null 2>&1 && ready=1 && break || true
    # 0.4.x may have no HTTP — treat stable alive process after 5s + no error as ready
    if (( SECONDS > 5 )) && ! grep -qiE 'error|traceback|unrecognized' "$LOG" 2>/dev/null; then
      ready=1; break
    fi
    sleep 1
  done
  if [[ "$ready" -ne 1 ]]; then
    echo "not ready after ${READY_TIMEOUT_S}s. Log:"; cat "$LOG" || true; exit 2
  fi
  echo "lmcache server ready pid=$SERVER_PID eng=$eng"
}

# --- Gate C: control (default engine, no blend module) ---
start_server default
python scripts/g1_matched_quality_bench.py --mode control --order abc \
  --out g1_matched_control.json
python -c "import json,sys; p=json.load(open('g1_matched_control.json')); sys.exit(0 if p.get('gate_c_pass') or p.get('pass_heuristic') else 3)"

# --- Gate D: blend engine + reorder ---
start_server blend
# Pass --control-json on abc too so set -e does not treat missing agree_rate as fail.
python scripts/g1_matched_quality_bench.py --mode blend --order abc \
  --control-json g1_matched_control.json \
  --out g1_matched_blend_abc.json
python scripts/g1_matched_quality_bench.py --mode blend --order bac \
  --control-json g1_matched_control.json \
  --out g1_matched_blend_bac.json
python -c "import json,sys; p=json.load(open('g1_matched_blend_bac.json')); ok=p.get('gate_d_pass') or p.get('pass_heuristic'); print('GATE_D:', 'PASS' if ok else 'FAIL'); sys.exit(0 if ok else 4)"

if [[ "${RUN_TTFT:-0}" != "1" ]]; then
  echo "Gate D passed. Set RUN_TTFT=1 for Stage E, or run g1_matched_ttft_chunk_e.sh."
  exit 0
fi

echo "=== Stage E TTFT (chunk_sep; see g1_matched_ttft_chunk_e.sh) ==="
bash scripts/g1_matched_ttft_chunk_e.sh
