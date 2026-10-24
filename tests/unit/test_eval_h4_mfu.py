"""CPU smoke for H4 MFU-prior eval."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "phase1" / "eval_h4_mfu.py"


def test_h4_mfu_runs(tmp_path: Path):
    out = tmp_path / "report.json"
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "--out", str(out), "--json"],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    assert r.returncode in (0, 4), r.stderr
    payload = json.loads(out.read_text())
    assert payload["peak_tflops_bf16"] == 312.0
    assert payload["mfu_prior"] == [0.40, 0.65]
    assert len(payload["suites"]) >= 1
