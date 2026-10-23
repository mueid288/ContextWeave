"""CPU: collect_oracle_epic refuses without allow flag; --help works."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "phase1" / "collect_oracle_epic.py"


def test_help():
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "--help"],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0
    assert "--n-requests" in r.stdout


def test_refuses_without_allow(tmp_path: Path):
    env = {k: v for k, v in os.environ.items() if k != "CONTEXTWEAVE_ALLOW_MODEL_LOAD"}
    r = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--out",
            str(tmp_path / "t.jsonl"),
            "--n-requests",
            "1",
        ],
        cwd=REPO,
        capture_output=True,
        text=True,
        env=env,
    )
    assert r.returncode == 1
