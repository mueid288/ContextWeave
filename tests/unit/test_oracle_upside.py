"""CPU tests for R1 / oracle upside."""

from __future__ import annotations

import json
import os
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


def test_r1_pass_when_oracle_splits_and_c3_fails_a_slice():
    trials: list[ConfigTrial] = []
    # Slice A: C3 quality collapses vs C0 (gate-need evidence)
    for i in range(10):
        rid = f"a{i}"
        trials.append(ConfigTrial(rid, "C0", 1.0, 1000.0, slice_id="synthesis"))
        trials.append(ConfigTrial(rid, "C1", 1.0, 700.0, slice_id="synthesis"))
        trials.append(ConfigTrial(rid, "C3", 0.5, 400.0, slice_id="synthesis"))
    # Slice B: lookup where C3 is fine and fast — oracle picks C3
    for i in range(10):
        rid = f"b{i}"
        trials.append(ConfigTrial(rid, "C0", 1.0, 1000.0, slice_id="lookup"))
        trials.append(ConfigTrial(rid, "C1", 1.0, 800.0, slice_id="lookup"))
        trials.append(ConfigTrial(rid, "C3", 1.0, 400.0, slice_id="lookup"))

    rep = oracle_upside(trials)
    assert rep.r1_gate_need_pass is True
    assert "synthesis" in rep.gate_need_slices
    assert rep.oracle_mean_quality == 1.0
    assert rep.ttft_reduction_fraction is not None
    assert rep.ttft_reduction_fraction >= 0.10
    assert rep.r1_pass is True


def test_r1_fail_without_gate_need_even_if_faster():
    # All arms same quality — no C3 failure slice
    trials: list[ConfigTrial] = []
    for i in range(20):
        rid = f"r{i}"
        trials.append(ConfigTrial(rid, "C0", 1.0, 1000.0, slice_id="all"))
        trials.append(ConfigTrial(rid, "C1", 1.0, 600.0, slice_id="all"))
        trials.append(ConfigTrial(rid, "C3", 1.0, 500.0, slice_id="all"))
    rep = oracle_upside(trials)
    assert rep.r1_gate_need_pass is False
    assert rep.r1_pass is False


def test_cw_r1_oracle_cli(tmp_path: Path):
    path = tmp_path / "t.jsonl"
    lines = []
    for i in range(10):
        rid = f"a{i}"
        lines.append(
            json.dumps(
                {
                    "request_id": rid,
                    "config": "C0",
                    "quality": 1.0,
                    "ttft_ms": 1000,
                    "slice_id": "synthesis",
                }
            )
        )
        lines.append(
            json.dumps(
                {
                    "request_id": rid,
                    "config": "C1",
                    "quality": 1.0,
                    "ttft_ms": 700,
                    "slice_id": "synthesis",
                }
            )
        )
        lines.append(
            json.dumps(
                {
                    "request_id": rid,
                    "config": "C3",
                    "quality": 0.5,
                    "ttft_ms": 400,
                    "slice_id": "synthesis",
                }
            )
        )
    for i in range(10):
        rid = f"b{i}"
        for cfg, q, t in (("C0", 1.0, 1000), ("C1", 1.0, 800), ("C3", 1.0, 400)):
            lines.append(
                json.dumps(
                    {
                        "request_id": rid,
                        "config": cfg,
                        "quality": q,
                        "ttft_ms": t,
                        "slice_id": "lookup",
                    }
                )
            )
    path.write_text("\n".join(lines) + "\n")
    out = tmp_path / "report.json"
    r = subprocess.run(
        [
            sys.executable,
            "-m",
            "contextweave.cli.r1_oracle",
            "--input",
            str(path),
            "--report",
            str(out),
            "--json",
        ],
        cwd=REPO,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": str(REPO / "src")},
    )
    assert r.returncode == 0, r.stderr + r.stdout
    payload = json.loads(out.read_text())
    assert payload["r1_pass"] is True
    assert payload["n_requests"] == 20
