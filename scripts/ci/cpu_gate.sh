#!/usr/bin/env bash
# CPU archive lock — no model load. Run from repo root.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
PY="${ROOT}/.venv/bin/python"
if [[ ! -x "$PY" ]]; then
  PY=python3
fi
"$PY" -m pytest tests/unit -q
"$PY" -m contextweave.cli.plan_demo --json >/dev/null
echo "cpu_gate OK"
