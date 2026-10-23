#!/usr/bin/env bash
# Fast EPIC path: prebuilt vllm==0.7.0 CUDA wheel + overlay DerekHJH/epic Python patches.
# Avoids the multi-hour nvcc build of `pip install -e /content/epic`.
#
# EPIC's LegoLink hooks (cache_fuse_metadata / hack_kv / kvlink) live in Python;
# README diffs against vLLM 0.7.0. If probe fails after overlay, fall back to
# scripts/g1/epic/g1_epic_install.sh (full source build) or a high-CPU host.
set -euo pipefail

if [[ "${CONTEXTWEAVE_ALLOW_MODEL_LOAD:-}" != "1" ]]; then
  echo "Refusing: set CONTEXTWEAVE_ALLOW_MODEL_LOAD=1 on the GPU host only."
  exit 1
fi
if [[ "${CONTEXTWEAVE_ALLOW_EPIC_REINSTALL:-}" != "1" ]]; then
  echo "Refusing: set CONTEXTWEAVE_ALLOW_EPIC_REINSTALL=1 on a dedicated session."
  exit 1
fi

EPIC_DIR="${EPIC_DIR:-/content/epic}"
EPIC_REPO="${EPIC_REPO:-https://github.com/DerekHJH/epic.git}"
EPIC_VENV="${EPIC_VENV:-/content/epic-venv}"
EPIC_PY_TARGET="${EPIC_PY_TARGET:-3.11}"
VLLM_WHEEL_PIN="${VLLM_WHEEL_PIN:-0.7.0}"
CW_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
[[ -d /content/ContextWeave ]] && CW_ROOT=/content/ContextWeave

_py_minor() {
  "$1" - <<'PY'
import sys
print(f"{sys.version_info.major}.{sys.version_info.minor}")
PY
}

ensure_epic_python() {
  local minor
  minor="$(python - <<'PY'
import sys
print(f"{sys.version_info.major}.{sys.version_info.minor}")
PY
)"
  case "$minor" in
    3.10|3.11|3.12)
      EPIC_PYTHON="$(command -v python)"
      return 0
      ;;
  esac
  if [[ -x "${EPIC_VENV}/bin/python" ]]; then
    case "$(_py_minor "${EPIC_VENV}/bin/python")" in
      3.10|3.11|3.12)
        # shellcheck disable=SC1091
        source "${EPIC_VENV}/bin/activate"
        EPIC_PYTHON="${EPIC_VENV}/bin/python"
        return 0
        ;;
    esac
  fi
  if ! command -v uv >/dev/null 2>&1; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="${HOME}/.local/bin:${PATH}"
  fi
  uv python install "$EPIC_PY_TARGET"
  uv venv "$EPIC_VENV" --python "$EPIC_PY_TARGET" --seed
  # shellcheck disable=SC1091
  source "${EPIC_VENV}/bin/activate"
  EPIC_PYTHON="${EPIC_VENV}/bin/python"
}

ensure_epic_python
export PATH="$(dirname "$EPIC_PYTHON"):${PATH}"

echo "=== fast EPIC: torch 2.5.1 + vllm==${VLLM_WHEEL_PIN} wheel (no source CUDA build) ==="
"$EPIC_PYTHON" -m pip install -U pip setuptools wheel
"$EPIC_PYTHON" -m pip install \
  "torch==2.5.1" "torchvision==0.20.1" \
  --index-url https://download.pytorch.org/whl/cu124
"$EPIC_PYTHON" -m pip uninstall -y vllm || true
"$EPIC_PYTHON" -m pip install "vllm==${VLLM_WHEEL_PIN}"
# Newer transformers (2026) require torch>=2.6 and break vLLM 0.7 tokenizer helpers.
"$EPIC_PYTHON" -m pip install \
  "transformers>=4.45.2,<4.50" "tokenizers>=0.19.1,<0.21" "huggingface-hub<1"

echo "=== cloning EPIC for Python overlay ==="
if [[ ! -d "$EPIC_DIR/.git" ]]; then
  git clone --depth 1 "$EPIC_REPO" "$EPIC_DIR"
else
  git -C "$EPIC_DIR" pull --ff-only || true
fi

# Resolve site-packages/vllm without importing vllm (import prints INFO logs that
# pollute capture and make rsync treat the line as a remote host).
SITE_VLLM="$("$EPIC_PYTHON" - <<'PY' 2>/dev/null
import pathlib, site
cands = []
try:
    cands.extend(site.getsitepackages())
except Exception:
    pass
try:
    u = site.getusersitepackages()
    if u:
        cands.append(u)
except Exception:
    pass
cands.append(str(pathlib.Path.cwd()))
for sp in cands:
    p = pathlib.Path(sp) / "vllm"
    if (p / "__init__.py").is_file():
        print(p.resolve())
        raise SystemExit(0)
raise SystemExit("vllm package dir not found under site-packages")
PY
)"
if [[ -z "$SITE_VLLM" || ! -d "$SITE_VLLM" ]]; then
  echo "BLOCK: could not locate installed vllm package directory."
  exit 7
fi
echo "=== overlaying EPIC *.py onto ${SITE_VLLM} (keeping wheel .so) ==="
# Local recursive copy of *.py only — avoid rsync remote-path parsing.
(
  cd "${EPIC_DIR}/vllm"
  find . -type f -name '*.py' -print0 \
    | tar --null -T - -cf - \
    | tar -C "${SITE_VLLM}" -xf -
)

echo "=== verify fork markers ==="
cd "$CW_ROOT"
# Write clean JSON to --out; import INFO/warnings go to stderr and must not pollute the file.
if ! "$EPIC_PYTHON" scripts/g1/epic/g1_epic_probe.py --out g1_epic_probe.json; then
  echo "FAST PATH FAILED: probe did not see EPIC markers after overlay."
  echo "Next: high-CPU full build (scripts/g1/epic/g1_epic_install.sh) or skip EPIC."
  exit 6
fi
"$EPIC_PYTHON" - <<'PY'
import json
p = json.load(open("g1_epic_probe.json"))
print("epic_fork_detected:", p.get("epic_fork_detected"), "path:", p.get("vllm_path"))
raise SystemExit(0 if p.get("epic_fork_detected") else 6)
PY

cat <<EOF

=== fast EPIC ready ===
  source ${EPIC_VENV}/bin/activate
  export CONTEXTWEAVE_ALLOW_MODEL_LOAD=1
  # Paper default model (llama-family hooks). Qwen3 is NOT patched in the demo fork.
  export SMOKE_MODEL=mistralai/Mistral-7B-Instruct-v0.2
  python scripts/g1/epic/g1_epic_bench.py --json | tee g1_epic.json
EOF
