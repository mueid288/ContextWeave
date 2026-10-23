"""CPU tests for Gate R helpers + FIX-2 alignment audit."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

REPO = Path(__file__).resolve().parents[2]


def _load(name: str):
    path = REPO / "scripts" / name
    spec = importlib.util.spec_from_file_location(name.replace(".py", ""), path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    # Ensure sibling imports (g1_matched_ttft_bench) resolve for alignment audit.
    sys.path.insert(0, str(REPO / "scripts"))
    spec.loader.exec_module(mod)
    return mod


def test_extract_engagement_from_request_output():
    mod = _load("g1_engagement.py")
    req = SimpleNamespace(num_cached_tokens=9000, num_computed_tokens=12000)
    eng = mod.extract_engagement([req])
    assert eng["num_cached_tokens"] == 9000
    assert eng["source"]


def test_gate_r_fail_closed_unknown():
    mod = _load("g1_engagement.py")
    r = mod.gate_r(cached_or_retrieved_tokens=None, chunk_token_total=3 * 512)
    assert r["gate_r_pass"] is False
    assert r["status"] == "ENGAGEMENT_UNKNOWN"


def test_gate_r_reuse_ok():
    mod = _load("g1_engagement.py")
    r = mod.gate_r(cached_or_retrieved_tokens=1200, chunk_token_total=3 * 512)
    assert r["need_tokens"] == int(0.7 * 1536)
    assert r["gate_r_pass"] is True
    assert r["status"] == "REUSE_OK"


def test_gate_r_engagement_fail():
    mod = _load("g1_engagement.py")
    r = mod.gate_r(cached_or_retrieved_tokens=10, chunk_token_total=3 * 512)
    assert r["gate_r_pass"] is False
    assert r["status"] == "ENGAGEMENT_FAIL"


def test_alignment_audit_fake_tokenizer_passes():
    mod = _load("g1_blend_alignment_audit.py")
    payload = mod.run_audit(mod._FakeTok(), chunk_tokens=512)
    assert payload["pass_all"] is True
    names = {c["name"] for c in payload["checks"]}
    assert "chunk_B_position_invariant" in names
    assert "salt_changes_chunk_hash" in names


def test_alignment_audit_cli():
    result = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "g1_blend_alignment_audit.py"), "--json"],
        capture_output=True,
        text=True,
        cwd=REPO,
    )
    assert result.returncode == 0
    assert '"pass_all": true' in result.stdout
