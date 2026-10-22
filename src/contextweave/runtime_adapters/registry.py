"""Registry of Phase 0B baseline strategies."""

from __future__ import annotations

import os

from contextweave.runtime_adapters.base import BaselineRunner, NotAvailableOnCpu


def _gpu_allowed() -> bool:
    return os.environ.get("CONTEXTWEAVE_ALLOW_MODEL_LOAD") == "1"


def _try_vllm_runners() -> dict[str, BaselineRunner] | None:
    """Return real vLLM runners when allow-flag is set and vllm imports."""
    if not _gpu_allowed():
        return None
    try:
        from contextweave.runtime_adapters import vllm_runners as vr
    except Exception:
        return None
    try:
        import vllm  # noqa: F401
    except ImportError:
        return None
    return {
        "full_prefill": vr.full_prefill_runner(),
        "prefix_cache": vr.prefix_cache_runner(),
        "smoke": vr.smoke_runner(),
    }


def get_runner(strategy: str) -> BaselineRunner:
    key = strategy.lower().replace("-", "_")
    live = _try_vllm_runners() or {}
    stubs: dict[str, BaselineRunner] = {
        "full_prefill": NotAvailableOnCpu(
            "full_prefill",
            "Implement via vLLM with prefix caching disabled.",
        ),
        "prefix_cache": NotAvailableOnCpu(
            "prefix_cache",
            "Implement via vLLM enable_prefix_caching=True.",
        ),
        "cacheblend": NotAvailableOnCpu(
            "cacheblend",
            "Implement via LMCache CacheBlend path (pins in Docs/runtime-pins.md).",
        ),
        "epic": NotAvailableOnCpu(
            "epic",
            "Implement via DerekHJH/epic within a 1-week time-box.",
        ),
        "smoke": NotAvailableOnCpu(
            "smoke",
            "First paid job: load Qwen3-8B / Llama-3.1-8B + tiny generate.",
        ),
    }
    mapping = {**stubs, **live}
    if key not in mapping:
        known = ", ".join(sorted(mapping))
        raise KeyError(f"Unknown strategy '{strategy}'. Known: {known}")
    return mapping[key]


STRATEGIES = ("full_prefill", "prefix_cache", "cacheblend", "epic", "smoke")
