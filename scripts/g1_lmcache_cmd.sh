#!/usr/bin/env bash
# Resolve `lmcache` CLI (PATH or python -m). Source from other scripts:
#   # shellcheck source=g1_lmcache_cmd.sh
#   source "$(dirname "$0")/g1_lmcache_cmd.sh"
#   run_lmcache server --host ...

run_lmcache() {
  if command -v lmcache >/dev/null 2>&1; then
    lmcache "$@"
    return
  fi
  # Common Colab miss: scripts dir not on PATH after pip install --user.
  local pybin
  pybin="$(python -c 'import sys; print(sys.executable)')"
  local scripts_dir
  scripts_dir="$(python -c 'import sysconfig; print(sysconfig.get_path("scripts"))')"
  if [[ -x "${scripts_dir}/lmcache" ]]; then
    "${scripts_dir}/lmcache" "$@"
    return
  fi
  if python -c "import lmcache" >/dev/null 2>&1; then
    # Fallback entry points used across lmcache versions.
    if python -c "import lmcache.__main__" >/dev/null 2>&1; then
      "$pybin" -m lmcache "$@"
      return
    fi
    if python -c "import lmcache.v1.multiprocess.server" >/dev/null 2>&1; then
      # Legacy: only supports `server`-like argv after module — map subcommand.
      if [[ "${1:-}" == "server" ]]; then
        shift
        "$pybin" -m lmcache.v1.multiprocess.server "$@"
        return
      fi
    fi
  fi
  echo "lmcache CLI not found. Install full package: pip install 'lmcache==${LMCACHE_PIN:-0.4.2}'" >&2
  echo "Debug: python=$(command -v python) scripts_dir=${scripts_dir:-?} which=$(command -v lmcache || true)" >&2
  python -c "import lmcache,sys; print('lmcache', getattr(lmcache,'__version__','?'), lmcache.__file__)" >&2 || true
  return 127
}
