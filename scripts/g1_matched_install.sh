#!/usr/bin/env bash
# Fresh Colab: install a Python-compatible vLLM + lmcache pair.
# Destructive — only on a new session you are willing to reinstall.
set -euo pipefail

if [[ "${CONTEXTWEAVE_ALLOW_MODEL_LOAD:-}" != "1" ]]; then
  echo "Refusing: set CONTEXTWEAVE_ALLOW_MODEL_LOAD=1 on the GPU host only."
  exit 1
fi
if [[ "${CONTEXTWEAVE_ALLOW_MATCHED_REINSTALL:-}" != "1" ]]; then
  echo "Refusing: set CONTEXTWEAVE_ALLOW_MATCHED_REINSTALL=1 to reinstall vLLM/lmcache."
  exit 1
fi

PY_MINOR="$(python - <<'PY'
import sys
print(f"{sys.version_info.major}.{sys.version_info.minor}")
PY
)"

# Defaults from LMCache compatibility matrix (docs.lmcache.ai) for modern Colab.
# Python ≥3.13 cannot install the old "0.5.3 era" vLLM 0.6.x wheels (torchvision pin).
if [[ -z "${VLLM_PIN:-}" || -z "${LMCACHE_PIN:-}" ]]; then
  case "$PY_MINOR" in
    3.10|3.11|3.12)
      VLLM_PIN="${VLLM_PIN:-0.6.6.post1}"
      LMCACHE_PIN="${LMCACHE_PIN:-0.5.3}"
      ;;
    *)
      # Colab A100 today ships Python 3.13 — use a matrix-green modern pair.
      VLLM_PIN="${VLLM_PIN:-0.18.0}"
      LMCACHE_PIN="${LMCACHE_PIN:-0.4.2}"
      ;;
  esac
fi

echo "=== python=${PY_MINOR} installing vllm==${VLLM_PIN} lmcache==${LMCACHE_PIN} ==="
pip install -U pip
pip install "vllm==${VLLM_PIN}" "lmcache==${LMCACHE_PIN}"
# Ensure console script is present (some installs omit it from PATH).
pip install --force-reinstall --no-deps "lmcache==${LMCACHE_PIN}" >/dev/null 2>&1 || true

# Dual CuPy packages → CUDA IPC hangs in LMCache blend server.
echo "=== normalizing CuPy to match torch CUDA ==="
CUDA_VER="$(python -c 'import torch; print((torch.version.cuda or "12").split(".")[0])' 2>/dev/null || echo 12)"
pip uninstall -y cupy cupy-cuda11x cupy-cuda12x cupy-cuda13x >/dev/null 2>&1 || true
pip install -q "cupy-cuda${CUDA_VER}x" || pip install -q cupy-cuda12x
python -c "import cupy; print('cupy OK', cupy.__version__)" || echo "WARN: cupy import failed"

OUT="${G1_MATCHED_ENV_JSON:-g1_matched_env.json}"
python - <<'PY' >"$OUT"
import json, sys
payload = {
    "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
}
for name in ("vllm", "lmcache", "torch"):
    try:
        m = __import__(name)
        payload[name] = getattr(m, "__version__", "unknown")
    except Exception as e:
        payload[name] = f"ERR: {e}"
print(json.dumps(payload, indent=2))
PY
echo "Wrote $OUT:"
cat "$OUT"
SCRIPTS_DIR="$(python -c 'import sysconfig; print(sysconfig.get_path("scripts"))')"
export PATH="${SCRIPTS_DIR}:${PATH}"
if command -v lmcache >/dev/null 2>&1; then
  echo "lmcache CLI: $(command -v lmcache)"
  lmcache -h >/dev/null 2>&1 && echo "lmcache CLI OK" || echo "WARN: lmcache -h failed"
else
  echo "WARN: lmcache not on PATH; scripts will try ${SCRIPTS_DIR}/lmcache or python -m"
  ls -la "${SCRIPTS_DIR}/lmcache" 2>/dev/null || true
fi
echo "Next: bash scripts/g1_matched_smoke.sh"
