"""CPU tests for R1 workload + dry collect path."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def test_generate_requests_has_synthesis_and_lookup():
    sys.path.insert(0, str(REPO / "scripts" / "r1"))
    import workload as w

    reqs = w.generate_requests(n=40, seed=7)
    assert len(reqs) == 40
    slices = {r.slice_id for r in reqs}
    assert "lookup" in slices and "synthesis" in slices
    assert w.quality_contains("Karachi BETA-4421", "Karachi BETA-4421") == 1.0
    assert w.quality_contains("nope", "Karachi") == 0.0


def test_collect_dry_workload(tmp_path: Path):
    out = tmp_path / "wl.json"
    r = subprocess.run(
        [
            sys.executable,
            str(REPO / "scripts" / "r1" / "collect_oracle_http.py"),
            "--dry-workload",
            "--n-requests",
            "12",
            "--out",
            str(out),
        ],
        cwd=REPO,
        capture_output=True,
        text=True,
        env={**__import__("os").environ, "PYTHONPATH": str(REPO / "src")},
    )
    assert r.returncode == 0, r.stderr + r.stdout
    rows = json.loads(out.read_text())
    assert len(rows) == 12
    assert all("slice_id" in row for row in rows)


def test_prompt_for_uses_document_chunk_attrs():
    sys.path.insert(0, str(REPO / "scripts" / "r1"))
    import collect_oracle_http as collect
    import workload as w
    from contextweave.product.frequency import FrequencyPrior

    reqs = w.generate_requests(n=2, seed=1, filler_chars=40)
    prior = FrequencyPrior(cold_start_n=0)
    rng = __import__("random").Random(0)
    for mode in ("C0", "C1", "C3"):
        prompt = collect._prompt_for(
            reqs[0], mode=mode, prior=prior, rng=rng, salt="t"
        )
        assert "Question:" in prompt
        assert reqs[0].document_ids[0] in prompt


def test_collect_blocks_without_allow(tmp_path: Path):
    out = tmp_path / "t.jsonl"
    env = {**__import__("os").environ, "PYTHONPATH": str(REPO / "src")}
    env.pop("CONTEXTWEAVE_ALLOW_MODEL_LOAD", None)
    r = subprocess.run(
        [
            sys.executable,
            str(REPO / "scripts" / "r1" / "collect_oracle_http.py"),
            "--n-requests",
            "2",
            "--out",
            str(out),
        ],
        cwd=REPO,
        capture_output=True,
        text=True,
        env=env,
    )
    assert r.returncode != 0
    assert "Refusing" in (r.stderr + r.stdout) or "ModelLoadBlocked" in (
        r.stderr + r.stdout
    )
