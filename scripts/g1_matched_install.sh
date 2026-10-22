#!/usr/bin/env bash
# Fresh Colab: pip-match lmcache + a pinned sibling vLLM (NOT leave Colab's 0.32).
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
# Required: do not silently keep Colab's vllm 0.32 against lmcache 0.5.3.
# Override when docs for your image specify a different pair.
VLLM_PIN="${VLLM_PIN:-0.6.6.post1}"

echo "=== installing vllm==${VLLM_PIN} lmcache==${LMCACHE_PIN} (matched-pin Colab) ==="
pip install -U pip
pip install "vllm==${VLLM_PIN}" "lmcache==${LMCACHE_PIN}"

OUT="${G1_MATCHED_ENV_JSON:-g1_matched_env.json}"
python - <<'PY' >"$OUT"
import json
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
