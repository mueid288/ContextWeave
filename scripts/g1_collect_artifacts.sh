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
  g1_epic_probe.json
)
EXIST=()
for f in "${FILES[@]}"; do
  [[ -f "$f" ]] && EXIST+=("$f")
done
# Include recent lmcache logs if present
[[ -f /tmp/lmcache_matched_blend.log ]] && EXIST+=(/tmp/lmcache_matched_blend.log)
[[ -f /tmp/lmcache_blend_server.log ]] && EXIST+=(/tmp/lmcache_blend_server.log)

if [[ ${#EXIST[@]} -eq 0 ]]; then
  echo "No artifacts found to collect."
  exit 1
fi
tar -czf "$OUT" "${EXIST[@]}"
echo "Wrote $OUT ($(du -h "$OUT" | awk '{print $1}'))"
ls -la "$OUT"
