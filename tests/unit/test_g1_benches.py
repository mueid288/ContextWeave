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
    """Deterministic tokenizer stand-in — no transformers dependency."""

    bos_token_id = 1

    def encode(self, text: str, add_special_tokens: bool = False):
        ids = [ord(c) % 97 + 2 for c in text]
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
    assert "DOC-A7" in mod.DOC_ORDER_KEYS
    assert "DOC-B3" in mod.ORDERS["bac"]
    assert any(c.get("hop") == 2 for c in mod.CASES)
    tok = _FakeTok()
    sep = mod._sep_ids(tok, " # # ")
    ch = mod._fill_doc_chunk(tok, "DOC-A7", "Secret code: CODE-A7-441.", 256)
    assert len(ch) == 256
    system = tok.encode("sys", add_special_tokens=True)
    q = tok.encode("q?", add_special_tokens=False)
    ids = mod._join(system=system, chunks=[ch, ch], question_ids=q, sep=sep)
    assert sep[0] in ids


def test_g1_matched_quality_refuses_without_allow(monkeypatch: pytest.MonkeyPatch):
    mod = _load_script("g1_matched_quality_bench.py")
    monkeypatch.delenv("CONTEXTWEAVE_ALLOW_MODEL_LOAD", raising=False)
    assert mod.main(["--mode", "native", "--json"]) == 1


def test_g1_matched_ttft_scenarios(monkeypatch: pytest.MonkeyPatch):
    mod = _load_script("g1_matched_ttft_bench.py")
    assert set(mod.ORDERS) == {"abc", "bac", "cba"}
    assert mod._percentile([1.0, 2.0, 3.0, 4.0, 5.0], 0.5) == 3.0
    assert mod._reorder_series_polluted([1400.0, 800.0, 801.0, 799.0, 802.0])
    assert not mod._reorder_series_polluted([1050.0, 1054.0, 1052.0, 1056.0])

    tok = _FakeTok()
    sep = mod._sep_ids(tok, " # # ")
    assert sep  # non-empty separator token ids
    a = mod._fill_chunk(tok, "A", 256)
    b = mod._fill_chunk(tok, "B", 256)
    c = mod._fill_chunk(tok, "C", 256)
    assert len(a) == len(b) == len(c) == 256
    a_salt = mod._fill_chunk(tok, "A", 256, salt="t0-bac-")
    assert a_salt != a

    system = tok.encode("sys", add_special_tokens=True)
    q = tok.encode("q?", add_special_tokens=False)
    cmap = {"A": a, "B": b, "C": c}
    abc = mod._prompt_for_order(
        ("A", "B", "C"), chunk_map=cmap, system=system, question_ids=q, sep=sep
    )
    bac = mod._prompt_for_order(
        ("B", "A", "C"), chunk_map=cmap, system=system, question_ids=q, sep=sep
    )
    assert abc != bac
    assert len(abc) == len(bac)
    assert sep[0] in abc
    ct = mod._chunk_tokens_for_target(
        target_prefix_tokens=6000,
        max_model_len=8192,
        max_tokens=1,
        system_len=10,
        question_len=20,
        sep_len=3,
    )
    assert ct >= 256 and ct % 256 == 0
    assert mod._align_down(3981, 256) == 3840

    assert callable(mod._reset_prefix_cache)
    assert callable(mod._measure_reorder_after_abc)
    monkeypatch.delenv("CONTEXTWEAVE_ALLOW_MODEL_LOAD", raising=False)
    assert mod.main(["--backend", "native_prefix", "--json"]) == 1


def test_g1_matched_quality_helpers(monkeypatch: pytest.MonkeyPatch):
    mod = _load_script("g1_matched_quality_bench.py")
    assert mod._align_chunk_tokens(500) == 256
    assert mod._align_chunk_tokens(512) == 512
    assert any(c.get("hop") == 2 for c in mod.CASES)
    monkeypatch.delenv("CONTEXTWEAVE_ALLOW_MODEL_LOAD", raising=False)
    assert mod.main(["--mode", "control", "--json"]) == 1


def test_g1_blend_hooks_prepare_disables_v1_mp(monkeypatch: pytest.MonkeyPatch):
    """G1-DIAG #1: MP+ENABLE_BLENDING without register_model → got=0 reuse."""
    hooks = _load_script("g1_blend_hooks.py")
    monkeypatch.delenv("VLLM_ENABLE_V1_MULTIPROCESSING", raising=False)
    hooks.prepare_blend_worker(blend_special_str=" # # ")
    assert os.environ.get("VLLM_ENABLE_V1_MULTIPROCESSING") == "0"
    assert os.environ.get("LMCACHE_ENABLE_BLENDING") == "True"
    assert os.environ.get("LMCACHE_BLEND_SPECIAL_STR") == " # # "
    assert os.environ.get("LMCACHE_USE_LAYERWISE") == "True"
    assert callable(hooks.patch_vllm_register_model_for_blend)
    assert hooks.BLEND_KV_CONNECTOR == "LMCacheConnectorV1"


def test_g1_blend_hooks_attention_shim_aliases_moved_class(monkeypatch: pytest.MonkeyPatch):
    """lmcache 0.4.2 imports vllm.attention; vLLM 0.18 moved Attention."""
    import sys
    import types

    hooks = _load_script("g1_blend_hooks.py")

    class _Attention:
        marker = "shim-ok"

    # Tear down any prior vllm.attention; install only the new path.
    monkeypatch.delitem(sys.modules, "vllm.attention", raising=False)
    parents = [
        "vllm",
        "vllm.model_executor",
        "vllm.model_executor.layers",
        "vllm.model_executor.layers.attention",
    ]
    for name in parents:
        if name not in sys.modules:
            monkeypatch.setitem(sys.modules, name, types.ModuleType(name))
    new = types.ModuleType("vllm.model_executor.layers.attention.attention")
    new.Attention = _Attention
    monkeypatch.setitem(
        sys.modules, "vllm.model_executor.layers.attention.attention", new
    )

    assert hooks.ensure_vllm_attention_compat() is True
    from vllm.attention import Attention as Attn

    assert Attn.marker == "shim-ok"


def test_g1_blend_hooks_flashinfer_sparse_symbol_shim(monkeypatch: pytest.MonkeyPatch):
    """lmcache 0.4.2 eagerly imports a flashinfer sparse helper this wheel lacks."""
    import sys
    import types

    hooks = _load_script("g1_blend_hooks.py")
    name = "block_sparse_indices_to_vector_sparse_offsets"

    fi = types.ModuleType("flashinfer")
    page = types.ModuleType("flashinfer.page")
    monkeypatch.setitem(sys.modules, "flashinfer", fi)
    monkeypatch.setitem(sys.modules, "flashinfer.page", page)
    assert not hasattr(page, name)

    assert hooks.ensure_flashinfer_sparse_compat() is True
    assert callable(getattr(page, name))


def test_g1_blend_hooks_constant_list_lookup_patch():
    """LMCache #2946: msgspec cannot encode vLLM ConstantList token ids."""
    hooks = _load_script("g1_blend_hooks.py")
    assert callable(hooks.patch_lmcache_constant_list_tokens)


def test_g1_matched_benches_use_inprocess_blend_hooks():
    ttft = _load_script("g1_matched_ttft_bench.py")
    quality = _load_script("g1_matched_quality_bench.py")
    assert ttft.BLEND_PATH == "inprocess"
    assert quality.BLEND_PATH == "inprocess"
    assert callable(ttft._prepare_blend_worker)
    assert callable(quality._prepare_blend_worker)
