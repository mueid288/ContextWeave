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
    # Gold on a later line (Qwen-style) must still count.
    sc2 = mod._score("The year is stated as:\n\n2019.\n\nWhat next?", "2019")
    assert sc2["contains"] is True
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


def test_g1_reorder_gap_refuses_without_allow(monkeypatch: pytest.MonkeyPatch):
    mod = _load_script("g1_reorder_gap_bench.py")
    monkeypatch.delenv("CONTEXTWEAVE_ALLOW_MODEL_LOAD", raising=False)
    assert mod.main(["--json"]) == 1


def test_g1_reorder_docs_change_order():
    mod = _load_script("g1_reorder_gap_bench.py")
    filler = "x" * 50
    abc = mod._docs_in_order(filler, ("A", "B", "C"))
    bca = mod._docs_in_order(filler, ("B", "C", "A"))
    assert abc.index("Document Alpha") < abc.index("Document Beta")
    assert bca.index("Document Beta") < bca.index("Document Alpha")
    assert "ALPHA-9173" in abc and "ALPHA-9173" in bca


def test_g1_epic_probe_help_and_no_crash_without_vllm():
    result = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "g1_epic_probe.py"), "--help"],
        capture_output=True,
        text=True,
        cwd=REPO,
    )
    assert result.returncode == 0
    assert "EPIC" in result.stdout or "epic" in result.stdout.lower()


def test_g1_epic_bench_refuses_without_allow(monkeypatch: pytest.MonkeyPatch):
    mod = _load_script("g1_epic_bench.py")
    monkeypatch.delenv("CONTEXTWEAVE_ALLOW_MODEL_LOAD", raising=False)
    assert mod.main(["--json"]) == 1


def test_g1_epic_docs_helper():
    mod = _load_script("g1_epic_bench.py")
    docs = mod._docs(filler_chars=40, order=("B", "C", "A"))
    assert len(docs) == 3
    assert "Karachi" in docs[0]
    assert "ALPHA-9173" in docs[2]


def test_g1_matched_quality_has_enough_cases():
    mod = _load_script("g1_matched_quality_bench.py")
    assert len(mod.CASES) >= 10
    corpus = mod.build_corpus(filler_chars=20)
    assert "DOC-A7" in corpus
    prompt = mod.build_prompt(
        corpus=corpus, order=mod.ORDERS["bac"], question=mod.CASES[0]["q"]
    )
    assert "DOC-B3" in prompt


def test_g1_matched_quality_refuses_without_allow(monkeypatch: pytest.MonkeyPatch):
    mod = _load_script("g1_matched_quality_bench.py")
    monkeypatch.delenv("CONTEXTWEAVE_ALLOW_MODEL_LOAD", raising=False)
    assert mod.main(["--mode", "native", "--json"]) == 1


def test_g1_matched_ttft_scenarios(monkeypatch: pytest.MonkeyPatch):
    mod = _load_script("g1_matched_ttft_bench.py")
    assert set(mod.ORDERS) == {"abc", "bac", "cba"}
    assert mod._percentile([1.0, 2.0, 3.0, 4.0, 5.0], 0.5) == 3.0
    fillers = {"A": "aaa", "B": "bbb", "C": "ccc"}
    abc = mod._docs(("A", "B", "C"), fillers=fillers, head="H\n")
    bac = mod._docs(("B", "A", "C"), fillers=fillers, head="H\n")
    assert abc.index("Document Alpha") < abc.index("Document Beta")
    assert bac.index("Document Beta") < bac.index("Document Alpha")
    assert "aaa" in abc and "bbb" in bac
    monkeypatch.delenv("CONTEXTWEAVE_ALLOW_MODEL_LOAD", raising=False)
    assert mod.main(["--backend", "native_prefix", "--json"]) == 1
