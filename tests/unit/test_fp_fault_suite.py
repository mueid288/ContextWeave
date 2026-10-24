"""CPU smoke for FR fault-injection suite."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "phase1" / "eval_fp_fault_suite.py"


def test_fault_suite_passes(tmp_path: Path):
    out = tmp_path / "report.json"
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "--out", str(out), "--json"],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    payload = json.loads(out.read_text())
    assert payload["pass_heuristic"] is True
    assert payload["refuse_rate"] == 1.0
    assert payload["control_allows_c3"] is True
