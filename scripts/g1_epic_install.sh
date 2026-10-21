#!/usr/bin/env bash
# Install DerekHJH/epic (vLLM ~0.7 fork) for G1 step 4.
# DESTROYS the stock vLLM 0.32 Colab pin — use a **fresh** GPU session only.
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

echo "=== cloning EPIC fork into $EPIC_DIR ==="
if [[ ! -d "$EPIC_DIR/.git" ]]; then
  git clone --depth 1 "$EPIC_REPO" "$EPIC_DIR"
else
  git -C "$EPIC_DIR" pull --ff-only || true
fi

echo "=== uninstalling stock vLLM (if any) ==="
pip uninstall -y vllm || true

echo "=== installing EPIC fork editable (long: CUDA extension build) ==="
cd "$EPIC_DIR"
pip install -U pip setuptools wheel ninja cmake packaging
# Match fork pyproject pin when possible; Colab may already have a torch —
# prefer the fork's declared torch if CUDA build demands it.
pip install -e . || {
  echo "pip install -e . failed; trying setup.py build fallback…"
  python setup.py build
  # Copy built _C.so next to package if present (see EPIC benchmarks_ours README).
  SO="$(find build -name '_C*.so' 2>/dev/null | head -1 || true)"
  if [[ -n "$SO" ]]; then
    cp "$SO" vllm/
  fi
  pip install -e . --no-build-isolation
}

echo "=== verify fork markers ==="
cd /content/ContextWeave 2>/dev/null || cd "$(dirname "$0")/.."
python scripts/g1_epic_probe.py --json | tee g1_epic_probe.json
echo "If epic_fork_detected is true, run: python scripts/g1_epic_bench.py --json | tee g1_epic.json"
