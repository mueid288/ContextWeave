"""CPU smoke for live TTFT harness."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "product" / "eval_order_ttft.py"


def test_dry_build():
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "--base-url", "http://x", "--dry-build"],
        cwd=REPO,
        capture_output=True,
        text=True,
        env={**dict(__import__("os").environ), "PYTHONPATH": str(REPO / "src")},
    )
    assert r.returncode == 0, r.stderr
    payload = json.loads(r.stdout)
    assert "frequency" in payload["dry_build"]
    assert "shuffled" in payload["dry_build"]
    assert "Karachi" in payload["dry_build"]["frequency"] or "doc-beta" in payload["dry_build"]["frequency"]
