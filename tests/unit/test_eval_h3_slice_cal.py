"""CPU tests for H3 slice-cal eval (LOO + calibrate→serve)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "phase1" / "eval_h3_slice_cal.py"


def _write_trials(path: Path, cells: list[tuple[str, str, float]]) -> None:
    """One request per cell; C0 always quality 1 / 1000ms; C3 quality given."""
    lines = []
    for i, (order, fact, q3) in enumerate(cells):
        rid = f"t{i:02d}_{order}_{fact}"
        lines.append(
            json.dumps(
                {
                    "request_id": rid,
                    "config": "C0",
                    "quality": 1.0,
                    "ttft_ms": 1000.0,
                    "feasible": True,
                }
            )
        )
        lines.append(
            json.dumps(
                {
                    "request_id": rid,
                    "config": "C3",
                    "quality": q3,
                    "ttft_ms": 400.0,
                    "feasible": True,
                    "chunk_order": order,
                }
            )
        )
    path.write_text("\n".join(lines) + "\n")


def test_calibrate_serve_pass(tmp_path: Path):
    cal = tmp_path / "cal.jsonl"
    serve = tmp_path / "serve.jsonl"
    # Train: ABC safe, BAC unsafe
    _write_trials(cal, [("ABC", "city", 1.0), ("BAC", "year", 0.0)])
    # Serve: same pattern
    _write_trials(serve, [("ABC", "city", 1.0), ("BAC", "year", 0.0)])
    out = tmp_path / "report.json"
    r = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--calibrate",
            str(cal),
            "--serve",
            str(serve),
            "--out",
            str(out),
            "--json",
        ],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr
    payload = json.loads(out.read_text())
    assert payload["pass_heuristic"] is True
    assert payload["result"]["precision"] == 1.0
    assert payload["result"]["policy_mean_quality"] == 1.0


def test_calibrate_serve_fail_on_mismatch(tmp_path: Path):
    cal = tmp_path / "cal.jsonl"
    serve = tmp_path / "serve.jsonl"
    _write_trials(cal, [("ABC", "city", 1.0), ("CAB", "code", 1.0)])
    # Serve: CAB now fails — false negative if we trust cal
    _write_trials(serve, [("ABC", "city", 1.0), ("CAB", "code", 0.0)])
    r = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--calibrate",
            str(cal),
            "--serve",
            str(serve),
            "--json",
        ],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    assert r.returncode == 4
    payload = json.loads(r.stdout[r.stdout.index("{") :])
    assert payload["pass_heuristic"] is False
