"""Shared pytest fixtures for ContextWeave tests."""
import pathlib
import pytest


@pytest.fixture
def repo_root() -> pathlib.Path:
    """Return the repository root directory, independent of cwd."""
    return pathlib.Path(__file__).resolve().parents[1]
