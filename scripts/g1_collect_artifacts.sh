#!/usr/bin/env bash
# Tar G1 matched-session artifacts for download before Colab stop.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
STAMP="${G1_COLLECT_STAMP:-$(date -u +%Y%m%dT%H%M%SZ)}"
OUT="${G1_COLLECT_OUT:-g1_matched_artifacts_${STAMP}.tar.gz}"
FILES=(
  g1_matched_env.json
  g1_matched_control.json
  g1_matched_blend_abc.json
  g1_matched_blend_bac.json
  g1_matched_ttft_native.json
  g1_matched_ttft_blend.json
  g1_ttft_native_fixed.json
  g1_ttft_blend_fixed.json
  g1_ttft_native_12k.json
  g1_ttft_blend_12k.json
  g1_ttft_blend_12k_salted.json
  g1_ttft_native_12k_chunks.json
  g1_ttft_blend_12k_chunks.json
  g1_epic_probe.json
  g1_epic.json
)
EXIST=()
for f in "${FILES[@]}"; do
  [[ -f "$f" ]] && EXIST+=("$f")
done
# Also pick up any other g1_*.json in cwd
while IFS= read -r -d '' f; do
  base=$(basename "$f")
  skip=0
  for e in "${EXIST[@]+"${EXIST[@]}"}"; do
    [[ "$e" == "$base" ]] && skip=1 && break
  done
  [[ $skip -eq 0 ]] && EXIST+=("$base")
done < <(find . -maxdepth 1 -name 'g1_*.json' -print0 2>/dev/null || true)

[[ -f /tmp/lmcache_matched_blend.log ]] && EXIST+=(/tmp/lmcache_matched_blend.log)
[[ -f /tmp/lmcache_blend_server.log ]] && EXIST+=(/tmp/lmcache_blend_server.log)

if [[ ${#EXIST[@]} -eq 0 ]]; then
  echo "No artifacts found to collect."
  exit 1
fi
tar -czf "$OUT" "${EXIST[@]}"
echo "Wrote $OUT ($(du -h "$OUT" | awk '{print $1}'))"
ls -la "$OUT"
