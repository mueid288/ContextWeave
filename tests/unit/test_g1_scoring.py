"""CPU tests for G1 answer scoring helpers."""

from __future__ import annotations

import importlib.util
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def _load():
    path = REPO / "scripts" / "g1_scoring.py"
    spec = importlib.util.spec_from_file_location("g1_scoring", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_strip_think_and_extract():
    s = _load()
    raw = "<think>long reasoning</think>\nKarachi\n"
    assert "think" not in s.strip_think(raw).lower()
    assert s.extract_answer(raw) == "Karachi"


def test_score_contains_gold_mid_text():
    s = _load()
    sc = s.score_output("The year is stated as:\n\n2019.\n\nok", "2019")
    assert sc["contains"] is True
    assert sc["garbage"] is False


def test_garbage_empty_and_hash_echo():
    s = _load()
    assert s.is_garbage("", "Karachi") is True
    assert s.is_garbage("# #  What is the id of Document Alpha?  # #", "Alpha") is True
    assert s.is_garbage("##", "Karachi") is True
    sc = s.score_output("# #", "Karachi")
    assert sc["garbage"] is True
    assert sc["contains"] is False


def test_non_garbage_with_gold():
    s = _load()
    assert s.is_garbage("The city is Karachi.", "Karachi") is False
