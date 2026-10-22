#!/usr/bin/env bash
# Install DerekHJH/epic (vLLM ~0.7 fork) for G1 step 4.
# Use a **fresh** GPU session only (replaces stock vLLM in the EPIC venv).
#
# On Colab Python 3.13: bootstraps an isolated CPython 3.11 via `uv`
# (torch==2.5.1 has no 3.13 wheels; EPIC CMake supports 3.9–3.12 only).
set -euo pipefail

if [[ "${CONTEXTWEAVE_ALLOW_MODEL_LOAD:-}" != "1" ]]; then
  echo "Refusing: set CONTEXTWEAVE_ALLOW_MODEL_LOAD=1 on the GPU host only."
  exit 1
fi
if [[ "${CONTEXTWEAVE_ALLOW_EPIC_REINSTALL:-}" != "1" ]]; then
  echo "Refusing: EPIC replaces vLLM entirely."
  echo "Set CONTEXTWEAVE_ALLOW_EPIC_REINSTALL=1 only on a fresh Colab/GPU session"
  echo "you are willing to rebuild (torch==2.5.1 + cmake CUDA build)."
  exit 1
fi

EPIC_DIR="${EPIC_DIR:-/content/epic}"
EPIC_REPO="${EPIC_REPO:-https://github.com/DerekHJH/epic.git}"
EPIC_VENV="${EPIC_VENV:-/content/epic-venv}"
EPIC_PY_TARGET="${EPIC_PY_TARGET:-3.11}"
CW_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# Prefer ContextWeave under /content when present (Colab).
if [[ -d /content/ContextWeave ]]; then
  CW_ROOT=/content/ContextWeave
fi

_py_minor() {
  "$1" - <<'PY'
import sys
print(f"{sys.version_info.major}.{sys.version_info.minor}")
PY
}

ensure_epic_python() {
  local sys_py="python"
  local minor
  minor="$(_py_minor "$sys_py")"
  case "$minor" in
    3.10|3.11|3.12)
      echo "=== system Python ${minor} OK for EPIC ==="
      EPIC_PYTHON="$(command -v python)"
      return 0
      ;;
  esac

  echo "=== system Python ${minor} incompatible; bootstrapping ${EPIC_PY_TARGET} venv at ${EPIC_VENV} ==="

  if [[ -x "${EPIC_VENV}/bin/python" ]]; then
    local vminor
    vminor="$(_py_minor "${EPIC_VENV}/bin/python")"
    case "$vminor" in
      3.10|3.11|3.12)
        EPIC_PYTHON="${EPIC_VENV}/bin/python"
        echo "Reusing existing venv Python ${vminor}: ${EPIC_PYTHON}"
        # shellcheck disable=SC1091
        source "${EPIC_VENV}/bin/activate"
        return 0
        ;;
    esac
  fi

  if ! command -v uv >/dev/null 2>&1; then
    echo "=== installing uv ==="
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="${HOME}/.local/bin:${PATH}"
  fi
  if ! command -v uv >/dev/null 2>&1; then
    echo "BLOCK: uv not on PATH after install. Add ~/.local/bin and retry."
    exit 4
  fi

  uv python install "$EPIC_PY_TARGET"
  uv venv "$EPIC_VENV" --python "$EPIC_PY_TARGET" --seed
  # shellcheck disable=SC1091
  source "${EPIC_VENV}/bin/activate"
  EPIC_PYTHON="${EPIC_VENV}/bin/python"
  echo "EPIC_PYTHON=${EPIC_PYTHON} ($(_py_minor "$EPIC_PYTHON"))"
}

ensure_epic_python
export PATH="$(dirname "$EPIC_PYTHON"):${PATH}"
hash -r 2>/dev/null || true

echo "=== cloning EPIC fork into $EPIC_DIR ==="
if [[ ! -d "$EPIC_DIR/.git" ]]; then
  git clone --depth 1 "$EPIC_REPO" "$EPIC_DIR"
else
  git -C "$EPIC_DIR" pull --ff-only || true
fi

echo "=== installing build deps + torch==2.5.1 into EPIC env ==="
"$EPIC_PYTHON" -m pip install -U pip setuptools wheel ninja cmake packaging \
  "setuptools-scm>=8" jinja2
# cu124 wheels run on newer Colab drivers; pin matches EPIC / vLLM 0.7.
"$EPIC_PYTHON" -m pip install \
  "torch==2.5.1" "torchvision==0.20.1" "torchaudio==2.5.1" \
  --index-url https://download.pytorch.org/whl/cu124

# setup.py imports torch at import time → must not use build isolation.
# Shallow clone often has no tags → pretend a v0.7-era version for setuptools_scm.
export SETUPTOOLS_SCM_PRETEND_VERSION="${SETUPTOOLS_SCM_PRETEND_VERSION:-0.7.0}"
# Parallelism: Colab A100 is fine at 4; drop to 2 if the VM OOMs.
export MAX_JOBS="${MAX_JOBS:-4}"
export NVCC_THREADS="${NVCC_THREADS:-4}"
# Default to A100 (sm_80). Override for other GPUs, e.g. T4 → 7.5, L4 → 8.9.
# Building 8.0+8.6+8.9+9.0 makes the Colab compile multi-hour.
if [[ -z "${TORCH_CUDA_ARCH_LIST:-}" ]]; then
  if command -v nvidia-smi >/dev/null 2>&1; then
    case "$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -1)" in
      *A100*) export TORCH_CUDA_ARCH_LIST="8.0" ;;
      *H100*) export TORCH_CUDA_ARCH_LIST="9.0" ;;
      *L4*)   export TORCH_CUDA_ARCH_LIST="8.9" ;;
      *T4*)   export TORCH_CUDA_ARCH_LIST="7.5" ;;
      *)      export TORCH_CUDA_ARCH_LIST="8.0" ;;
    esac
  else
    export TORCH_CUDA_ARCH_LIST="8.0"
  fi
fi
echo "=== TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST} MAX_JOBS=${MAX_JOBS} ==="

_find_cuda_home() {
  if [[ -n "${CUDA_HOME:-}" && -x "${CUDA_HOME}/bin/nvcc" ]]; then
    echo "$CUDA_HOME"
    return 0
  fi
  local cand
  for cand in /usr/local/cuda /usr/local/cuda-12.8 /usr/local/cuda-12.6 \
    /usr/local/cuda-12.4 /usr/local/cuda-12.1 /usr/local/cuda-12; do
    if [[ -x "${cand}/bin/nvcc" ]]; then
      echo "$cand"
      return 0
    fi
  done
  if command -v nvcc >/dev/null 2>&1; then
    dirname "$(dirname "$(command -v nvcc)")"
    return 0
  fi
  # pip nvidia-cuda-nvcc-cu12 layout
  local pip_nvcc
  pip_nvcc="$("$EPIC_PYTHON" - <<'PY' 2>/dev/null || true
import importlib.util, pathlib
spec = importlib.util.find_spec("nvidia.cuda_nvcc")
if not spec or not spec.submodule_search_locations:
    raise SystemExit(1)
root = pathlib.Path(list(spec.submodule_search_locations)[0])
for p in (root, root / "bin", *root.glob("**/nvcc")):
    pass
nvcc = root / "bin" / "nvcc"
if nvcc.is_file():
    print(root)
PY
)"
  if [[ -n "$pip_nvcc" && -x "${pip_nvcc}/bin/nvcc" ]]; then
    echo "$pip_nvcc"
    return 0
  fi
  return 1
}

ensure_cuda_home() {
  local home=""
  home="$(_find_cuda_home)" && export CUDA_HOME="$home" && return 0

  echo "=== nvcc missing — installing CUDA 12.4 toolkit pieces (Colab often has drivers only) ==="
  if command -v apt-get >/dev/null 2>&1; then
    apt-get update -qq
    # Prefer matching 12.4 (torch cu124). Fall back to generic toolkit meta-package.
    DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
      cuda-nvcc-12-4 cuda-cudart-dev-12-4 cuda-compiler-12-4 \
      2>/dev/null \
      || DEBIAN_FRONTEND=noninteractive apt-get install -y -qq nvidia-cuda-toolkit \
      || true
  fi
  home="$(_find_cuda_home)" && export CUDA_HOME="$home" && return 0

  echo "=== apt nvcc still missing — trying pip nvidia-cuda-nvcc-cu12 ==="
  "$EPIC_PYTHON" -m pip install -q "nvidia-cuda-nvcc-cu12==12.4.*" "nvidia-cuda-runtime-cu12==12.4.*" || true
  home="$(_find_cuda_home)" && export CUDA_HOME="$home" && return 0

  echo "BLOCK: could not obtain nvcc / CUDA_HOME. GPU runtime present but no CUDA toolkit."
  echo "Tried: /usr/local/cuda*, apt cuda-nvcc-12-4, pip nvidia-cuda-nvcc-cu12."
  exit 5
}

ensure_cuda_home
export PATH="${CUDA_HOME}/bin:${PATH}"
export LD_LIBRARY_PATH="${CUDA_HOME}/lib64:${CUDA_HOME}/lib:${LD_LIBRARY_PATH:-}"
echo "=== CUDA_HOME=${CUDA_HOME} ==="
"${CUDA_HOME}/bin/nvcc" --version | tail -1

if [[ -f "$EPIC_DIR/requirements-build.txt" ]]; then
  "$EPIC_PYTHON" -m pip install -r "$EPIC_DIR/requirements-build.txt" || true
fi
if [[ -f "$EPIC_DIR/requirements-common.txt" ]]; then
  "$EPIC_PYTHON" -m pip install -r "$EPIC_DIR/requirements-common.txt" || true
fi
if [[ -f "$EPIC_DIR/requirements-cuda.txt" ]]; then
  "$EPIC_PYTHON" -m pip install -r "$EPIC_DIR/requirements-cuda.txt" || true
fi

echo "=== uninstalling any prior vLLM in this env ==="
"$EPIC_PYTHON" -m pip uninstall -y vllm || true

echo "=== installing EPIC fork editable (no build isolation; long CUDA build) ==="
cd "$EPIC_DIR"
export VLLM_PYTHON_EXECUTABLE="$EPIC_PYTHON"
# Verbose so the next failure is diagnosable on Colab.
if ! "$EPIC_PYTHON" -m pip install -e . --no-build-isolation -v; then
  echo "pip install -e . failed; trying setup.py build fallback…"
  "$EPIC_PYTHON" setup.py build
  SO="$(find build -name '_C*.so' 2>/dev/null | head -1 || true)"
  if [[ -n "$SO" ]]; then
    cp "$SO" vllm/
  fi
  "$EPIC_PYTHON" -m pip install -e . --no-build-isolation
fi

echo "=== verify fork markers ==="
cd "$CW_ROOT"
"$EPIC_PYTHON" scripts/g1_epic_probe.py --json | tee g1_epic_probe.json

cat <<EOF

=== EPIC env ready ===
Activate before benches:
  source ${EPIC_VENV}/bin/activate   # if using the uv venv
  # or:
  export PATH="$(dirname "$EPIC_PYTHON"):\$PATH"

Then:
  export CONTEXTWEAVE_ALLOW_MODEL_LOAD=1
  python scripts/g1_epic_bench.py --json | tee g1_epic.json
EOF
