#!/usr/bin/env bash
# Resolve `lmcache` CLI and launch MP server across 0.5.x / 0.4.x flag sets.
# Source from other scripts:
#   source "$(dirname "$0")/g1_lmcache_cmd.sh"
#   start_lmcache_server default|/blend  LOG  HOST  PORT  HTTP_PORT  L1_GB

_lmcache_bin() {
  if command -v lmcache >/dev/null 2>&1; then
    echo "lmcache"
    return 0
  fi
  local scripts_dir
  scripts_dir="$(python -c 'import sysconfig; print(sysconfig.get_path("scripts"))')"
  if [[ -x "${scripts_dir}/lmcache" ]]; then
    echo "${scripts_dir}/lmcache"
    return 0
  fi
  return 1
}

run_lmcache() {
  local bin
  if bin="$(_lmcache_bin)"; then
    "$bin" "$@"
    return
  fi
  echo "lmcache CLI missing. Reinstall: pip install -U 'lmcache==${LMCACHE_PIN:-0.4.2}'" >&2
  python - <<'PY' >&2
import lmcache, pathlib
print("lmcache file:", getattr(lmcache, "__file__", "?"))
print("version file:", end=" ")
try:
    from importlib.metadata import version
    print(version("lmcache"))
except Exception as e:
    print("?", e)
PY
  return 127
}

# Launch server; prefer modern `lmcache server` flags, fall back to 0.4.x argv.
start_lmcache_server() {
  local eng="$1"
  local log="$2"
  local host="${3:-127.0.0.1}"
  local port="${4:-5555}"
  local http_port="${5:-18080}"
  local l1_gb="${6:-8}"

  export PATH="$(python -c 'import sysconfig; print(sysconfig.get_path("scripts"))'):${PATH}"

  local bin
  if ! bin="$(_lmcache_bin)"; then
    echo "Cannot find lmcache CLI" >&2
    return 127
  fi

  # Probe whether this CLI accepts HTTP / transfer-mode flags (0.5.x era).
  local help
  help="$("$bin" server -h 2>&1 || true)"
  if grep -q -- '--http-host' <<<"$help" && grep -q -- '--supported-transfer-mode' <<<"$help"; then
    echo "=== lmcache server (modern flags) eng=${eng} ==="
    "$bin" server \
      --host "$host" \
      --port "$port" \
      --http-host "$host" \
      --http-port "$http_port" \
      --l1-size-gb "$l1_gb" \
      --eviction-policy LRU \
      --engine-type "$eng" \
      --chunk-size 256 \
      --supported-transfer-mode lmcache_driven \
      >"$log" 2>&1 &
  else
    echo "=== lmcache server (0.4.x flags) eng=${eng} ==="
    "$bin" server \
      --host "$host" \
      --port "$port" \
      --l1-size-gb "$l1_gb" \
      --eviction-policy LRU \
      --engine-type "$eng" \
      --chunk-size 256 \
      >"$log" 2>&1 &
  fi
  echo $!
}
