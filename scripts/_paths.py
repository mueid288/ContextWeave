"""Repo-root resolution for nested scripts (CPU-safe, no deps)."""

from __future__ import annotations

from pathlib import Path


def repo_root() -> Path:
    here = Path(__file__).resolve().parent
    for cand in (here, *here.parents):
        if (cand / "pyproject.toml").exists():
            return cand
    raise RuntimeError("Could not find repo root (pyproject.toml)")
