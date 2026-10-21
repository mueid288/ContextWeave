"""CPU-safe tests for G1 bench harnesses (no torch/vllm/model load)."""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO = Path(__file__).resolve().parents[2]


def _load_script(name: str):
    path = REPO / "scripts" / name
    spec = importlib.util.spec_from_file_location(name.replace(".py", ""), path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class _FakeTok:
    """Whitespace tokenizer stand-in — no transformers dependency."""

    bos_token_id = 1

    def encode(self, text: str, add_special_tokens: bool = True):
        ids = [hash(t) % 10_000 for t in text.split() if t]
        if add_special_tokens:
            return [self.bos_token_id, *ids]
        return ids


def test_g1_ttft_build_prefix_pads_to_doc_chars():
    mod = _load_script("g1_ttft_bench.py")
    prefix = mod._build_prefix(2000)
    assert "Document Alpha" in prefix
    assert "Document Beta" in prefix
    assert "Document Gamma" in prefix
    assert "token-fill line" in prefix
    # Three docs × ~2000 chars plus headers/system → well above the old 1500-char bug.
    assert len(prefix) > 5000


def test_g1_ttft_questions_are_three():
    mod = _load_script("g1_ttft_bench.py")
    qs = mod._questions()
    assert len(qs) == 3
    assert all("Answer with only the number" in q for q in qs)


def test_g1_ttft_refuses_without_allow_flag(monkeypatch: pytest.MonkeyPatch):
    mod = _load_script("g1_ttft_bench.py")
    monkeypatch.delenv("CONTEXTWEAVE_ALLOW_MODEL_LOAD", raising=False)
    assert mod.main(["--json"]) == 1


def test_g1_ttft_help():
    result = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "g1_ttft_bench.py"), "--help"],
        capture_output=True,
        text=True,
        cwd=REPO,
    )
    assert result.returncode == 0
    assert "target-prefix-tokens" in result.stdout


def test_g1_cacheblend_fill_and_join_chunks():
    mod = _load_script("g1_cacheblend_bench.py")
    tok = _FakeTok()
    chunk = mod._fill_chunk(tok, "Alpha", 40)
    assert len(chunk) == 40
    sep = [99, 98]
    system = [1, 2, 3]
    joined = mod._join_chunks(
        tok,
        system=system,
        chunks=[chunk, chunk],
        question="What is the id?",
        sep=sep,
    )
    assert joined[:3] == system
    assert sep == joined[3:5]
    assert len(joined) > len(system) + 2 * len(chunk)


def test_g1_cacheblend_refuses_without_allow_flag(monkeypatch: pytest.MonkeyPatch):
    mod = _load_script("g1_cacheblend_bench.py")
    monkeypatch.delenv("CONTEXTWEAVE_ALLOW_MODEL_LOAD", raising=False)
    assert mod.main(["--json"]) == 1


def test_g1_cacheblend_help():
    result = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "g1_cacheblend_bench.py"), "--help"],
        capture_output=True,
        text=True,
        cwd=REPO,
    )
    assert result.returncode == 0
    assert "CacheBlend" in result.stdout or "cacheblend" in result.stdout.lower()


def test_g1_cacheblend_ensure_spawn_sets_env(monkeypatch: pytest.MonkeyPatch):
    mod = _load_script("g1_cacheblend_bench.py")
    monkeypatch.delenv("VLLM_WORKER_MULTIPROC_METHOD", raising=False)
    mod._ensure_spawn()
    assert os.environ.get("VLLM_WORKER_MULTIPROC_METHOD") == "spawn"


def test_g1_cacheblend_patch_helper_exists():
    mod = _load_script("g1_cacheblend_bench.py")
    assert callable(mod._patch_vllm_register_model_for_blend)


def test_g1_quality_scoring_and_docs():
    mod = _load_script("g1_quality_bench.py")
    docs = mod._build_shared_docs(filler_chars=200)
    assert "ALPHA-9173" in docs
    assert "Karachi" in docs
    assert "2019" in docs
    sc = mod._score("The code is ALPHA-9173.\nOkay thinking", "ALPHA-9173")
    assert sc["contains"] is True
    assert mod.main(["--json"]) == 1  # no allow flag


def test_g1_quality_help():
    result = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "g1_quality_bench.py"), "--help"],
        capture_output=True,
        text=True,
        cwd=REPO,
    )
    assert result.returncode == 0
    assert "answer preservation" in result.stdout.lower() or "quality" in result.stdout.lower()
