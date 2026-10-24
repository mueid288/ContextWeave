"""CPU smoke for shipped-policy plan demo CLI."""

from __future__ import annotations

import json
import subprocess
import sys

from contextweave.cli.plan_demo import main


def test_plan_demo_all_json(capsys):
    assert main(["--json", "--scenario", "all"]) == 0
    payload = json.loads(capsys.readouterr().out)
    names = {s["scenario"] for s in payload["scenarios"]}
    assert "exact_prefix" in names
    by = {s["scenario"]: s["chosen"] for s in payload["scenarios"]}
    assert by["exact_prefix"] == "C1"
    assert by["no_reuse_signals"] == "C0"
    assert by["c3_blocked_no_provenance"] == "C0"
    assert by["c3_blocked_build_hash_mismatch"] == "C0"
    assert by["c3_allowed_demo_only"] == "C3"


def test_entry_help():
    r = subprocess.run(
        [sys.executable, "-m", "contextweave.cli.plan_demo", "--help"],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0
