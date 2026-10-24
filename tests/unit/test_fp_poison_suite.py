"""CPU smoke for build-context poison suite."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "phase1" / "eval_fp_poison_suite.py"


def test_poison_suite_passes(tmp_path: Path):
    out = tmp_path / "report.json"
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "--out", str(out), "--json"],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr
    payload = json.loads(out.read_text())
    assert payload["pass_heuristic"] is True
    assert payload["refuse_rate"] == 1.0
    assert payload["n_cases"] >= 8
