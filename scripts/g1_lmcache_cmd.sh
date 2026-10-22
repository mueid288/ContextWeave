#!/usr/bin/env bash
# Launch LMCache MP server when `lmcache` console_script is missing (common on Colab).
# Source: source "$(dirname "$0")/g1_lmcache_cmd.sh"
# Use:   SERVER_PID="$(start_lmcache_server eng LOG HOST PORT HTTP_PORT L1_GB)"

_lmcache_server_prefix() {
  export PATH="$(python -c 'import sysconfig; print(sysconfig.get_path("scripts"))'):${PATH}"
  if command -v lmcache >/dev/null 2>&1; then
    echo "lmcache server"
    return 0
  fi
  local scripts_dir
  scripts_dir="$(python -c 'import sysconfig; print(sysconfig.get_path("scripts"))')"
  if [[ -x "${scripts_dir}/lmcache" ]]; then
    echo "${scripts_dir}/lmcache server"
    return 0
  fi
  # Documented module entry (0.4.x / 0.5.x) — works without console_scripts.
  if python -c "import lmcache.v1.multiprocess.http_server" >/dev/null 2>&1; then
    echo "python -m lmcache.v1.multiprocess.http_server"
    return 0
  fi
  if python -c "import lmcache.v1.multiprocess.server" >/dev/null 2>&1; then
    echo "python -m lmcache.v1.multiprocess.server"
    return 0
  fi
  return 1
}

start_lmcache_server() {
  local eng="$1"
  local log="$2"
  local host="${3:-127.0.0.1}"
  local port="${4:-5555}"
  local http_port="${5:-18080}"
  local l1_gb="${6:-8}"

  local prefix
  if ! prefix="$(_lmcache_server_prefix)"; then
    echo "No lmcache server entry. Try: python -c 'import lmcache.v1.multiprocess.http_server'" >&2
    return 127
  fi

  local help=""
  # shellcheck disable=SC2086
  help="$(${prefix} -h 2>&1 || true)"

  echo "=== lmcache via: ${prefix} eng=${eng} ==="

  local -a cmd=()
  # Split prefix into array safely for common cases.
  # shellcheck disable=SC2206
  cmd=(${prefix})

  if grep -q -- '--http-host' <<<"$help" || [[ "$prefix" == *http_server* ]]; then
    cmd+=(
      --host "$host" --port "$port"
      --http-host "$host" --http-port "$http_port"
      --l1-size-gb "$l1_gb" --eviction-policy LRU
      --engine-type "$eng" --chunk-size 256
    )
    if grep -q -- '--supported-transfer-mode' <<<"$help"; then
      cmd+=(--supported-transfer-mode lmcache_driven)
    fi
  else
    cmd+=(
      --host "$host" --port "$port"
      --l1-size-gb "$l1_gb" --eviction-policy LRU
      --engine-type "$eng" --chunk-size 256
    )
  fi

  "${cmd[@]}" >"$log" 2>&1 &
  echo $!
}
