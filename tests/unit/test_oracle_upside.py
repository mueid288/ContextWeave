"""CPU tests for Phase 1 oracle upside."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from contextweave.oracle import ConfigTrial, best_fixed_config, oracle_upside

REPO = Path(__file__).resolve().parents[2]


def test_best_fixed_prefers_higher_quality():
    trials = [
        ConfigTrial("r1", "C0", 1.0, 1000),
        ConfigTrial("r2", "C0", 1.0, 1100),
        ConfigTrial("r1", "C3", 0.5, 300),
        ConfigTrial("r2", "C3", 0.5, 300),
    ]
    assert best_fixed_config(trials) == "C0"


def test_oracle_beats_fixed_when_requests_prefer_different_configs():
    # Even → C0 wins; odd → C3 wins. Fixed alone cannot hit mean quality 1.0.
    trials = []
    for i in range(20):
        rid = f"r{i}"
        if i % 2 == 0:
            trials.append(ConfigTrial(rid, "C0", 1.0, 800.0))
            trials.append(ConfigTrial(rid, "C3", 0.5, 800.0))
        else:
            trials.append(ConfigTrial(rid, "C0", 0.5, 800.0))
            trials.append(ConfigTrial(rid, "C3", 1.0, 800.0))
    rep = oracle_upside(trials)
    assert rep.oracle_mean_quality == 1.0
    assert rep.best_fixed_mean_quality is not None
    assert rep.best_fixed_mean_quality < 1.0
    assert rep.quality_upside_points is not None
    assert rep.quality_upside_points >= 3.0
    assert rep.g2_quality_pass is True
    assert rep.g2_pass is True


def test_oracle_cli_jsonl(tmp_path: Path):
    path = tmp_path / "t.jsonl"
    lines = []
    for i in range(10):
        if i % 2 == 0:
            lines.append(
                json.dumps(
                    {"request_id": f"r{i}", "config": "C0", "quality": 1.0, "ttft_ms": 800}
                )
            )
            lines.append(
                json.dumps(
                    {"request_id": f"r{i}", "config": "C3", "quality": 0.5, "ttft_ms": 800}
                )
            )
        else:
            lines.append(
                json.dumps(
                    {"request_id": f"r{i}", "config": "C0", "quality": 0.5, "ttft_ms": 800}
                )
            )
            lines.append(
                json.dumps(
                    {"request_id": f"r{i}", "config": "C3", "quality": 1.0, "ttft_ms": 800}
                )
            )
    path.write_text("\n".join(lines) + "\n")
    out = tmp_path / "report.json"
    r = subprocess.run(
        [
            sys.executable,
            str(REPO / "scripts" / "phase1" / "run_oracle_study.py"),
            "--input",
            str(path),
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
    assert payload["g2_pass"] is True
    assert payload["n_requests"] == 10
