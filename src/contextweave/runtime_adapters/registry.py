"""Registry of Phase 0B baseline strategies."""

from __future__ import annotations

from contextweave.runtime_adapters.base import BaselineRunner, NotAvailableOnCpu


def get_runner(strategy: str) -> BaselineRunner:
    key = strategy.lower().replace("-", "_")
    mapping: dict[str, BaselineRunner] = {
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
            "Implement via LMCache CacheBlend path (pins in docs/runtime-pins.md).",
        ),
        "epic": NotAvailableOnCpu(
            "epic",
            "Implement via DerekHJH/epic within a 1-week time-box.",
        ),
        "smoke": NotAvailableOnCpu(
            "smoke",
            "First paid job: load Llama-3.1-8B-Instruct + tiny CacheBlend prompt.",
        ),
    }
    if key not in mapping:
        known = ", ".join(sorted(mapping))
        raise KeyError(f"Unknown strategy '{strategy}'. Known: {known}")
    return mapping[key]


STRATEGIES = ("full_prefill", "prefix_cache", "cacheblend", "epic", "smoke")
