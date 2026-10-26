#!/usr/bin/env bash
# CPU product gate — no model load. Run from repo root.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
PY="${ROOT}/.venv/bin/python"
if [[ ! -x "$PY" ]]; then
  PY=python3
fi
"$PY" -m pytest tests -q
"$PY" -m contextweave.cli.serve_order --help >/dev/null
"$PY" -m contextweave.cli.analyze_trace --help >/dev/null
"$PY" -m contextweave.cli.cw_field_g0 --help >/dev/null
echo "cpu_gate OK"
