"""Runtime adapters for LMCache / vLLM / SGLang (Phase 3; stub)."""

from contextweave.runtime_adapters.base import BaselineRunner
from contextweave.runtime_adapters.registry import get_runner

__all__ = [
    "BaselineRunner",
    "get_runner",
]
