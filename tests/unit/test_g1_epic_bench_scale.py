"""CPU tests for EPIC bench scale helpers (no model load)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]


def _load():
    path = REPO / "scripts" / "g1_epic_bench.py"
    spec = importlib.util.spec_from_file_location("g1_epic_bench", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class _FakeTok:
    def encode(self, text: str, add_special_tokens: bool = False):
        # ~1 id per 4 chars — deterministic stand-in
        n = max(1, len(text) // 4)
        ids = list(range(n))
        if add_special_tokens:
            return [1, *ids]
        return ids


def test_docs_filler_scales():
    mod = _load()
    short = mod._docs(filler_chars=100, order=("A", "B", "C"))
    long = mod._docs(filler_chars=5000, order=("A", "B", "C"))
    assert all(len(a) < len(b) for a, b in zip(short, long, strict=True))


def test_filler_chars_for_target_grows_toward_budget():
    mod = _load()
    tok = _FakeTok()
    system = "sys"
    question = "Which city?"
    n_lo = mod._filler_chars_for_target(
        tok,
        system=system,
        question=question,
        order=("B", "C", "A"),
        target_context_tokens=200,
    )
    n_hi = mod._filler_chars_for_target(
        tok,
        system=system,
        question=question,
        order=("B", "C", "A"),
        target_context_tokens=2000,
    )
    assert n_hi > n_lo
    docs = mod._docs(filler_chars=n_hi, order=("B", "C", "A"))
    prompt = system + "\n\n" + "\n".join(docs) + "\n" + question
    # Allow some slack — binary search aims near target.
    got = len(tok.encode(prompt, add_special_tokens=True))
    assert got >= 1500


def test_help_lists_target_context_tokens():
    import subprocess
    import sys

    r = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "g1_epic_bench.py"), "--help"],
        capture_output=True,
        text=True,
        cwd=REPO,
    )
    assert r.returncode == 0
    assert "--target-context-tokens" in r.stdout
