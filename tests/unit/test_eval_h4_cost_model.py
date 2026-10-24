"""CPU smoke for H4 cost-model eval CLI."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "phase1" / "eval_h4_cost_model.py"


def test_help():
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "--help"],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0


def test_runs_on_banked_artifacts(tmp_path: Path):
    out = tmp_path / "report.json"
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "--out", str(out), "--json"],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    # Expected FAIL on default 450 TFLOP vs ~1s A100 C0 — exit 4 is OK.
    assert r.returncode in (0, 4), r.stderr
    payload = json.loads(out.read_text())
    assert payload["pre_reg"].endswith("pre-reg-h4-cost-model.md")
    assert len(payload["primary"]) >= 1
    assert "pass_heuristic" in payload
