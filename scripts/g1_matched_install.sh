#!/usr/bin/env bash
# Fresh Colab: pip-match to lmcache/vllm-openai:v0.5.3 era (NOT Docker).
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

LMCACHE_PIN="${LMCACHE_PIN:-0.5.3}"
# Sibling vLLM: leave empty to let lmcache's install pull a compatible wheel,
# or set e.g. VLLM_PIN=0.28.0 if docs for the image tag specify one.
VLLM_PIN="${VLLM_PIN:-}"

echo "=== installing lmcache==${LMCACHE_PIN} (matched-pin Colab) ==="
pip install -U pip
if [[ -n "$VLLM_PIN" ]]; then
  pip install "vllm==${VLLM_PIN}" "lmcache==${LMCACHE_PIN}"
else
  pip install "lmcache==${LMCACHE_PIN}"
  # Ensure vLLM present; do not upgrade past what lmcache 0.5.3 expects if already ok.
  python -c "import vllm" 2>/dev/null || pip install "vllm"
fi

OUT="${G1_MATCHED_ENV_JSON:-g1_matched_env.json}"
python - <<'PY' >"$OUT"
import json, importlib.util
payload = {}
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
echo "Next: bash scripts/g1_matched_smoke.sh"
