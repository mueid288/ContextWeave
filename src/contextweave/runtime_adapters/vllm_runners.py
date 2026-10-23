"""vLLM-backed Tier-1 runners for GPU hosts (G1).

Requires ``CONTEXTWEAVE_ALLOW_MODEL_LOAD=1`` and an installed ``vllm`` package.
Laptop / CPU hosts never import this module from the registry unless allow is set
and vLLM is present — the registry falls back to stubs otherwise.
"""

from __future__ import annotations

import time
from typing import Any

from contextweave.runtime_adapters.base import (
    BaselineRequest,
    BaselineResult,
    BaselineRunner,
)


def _require_vllm():
    try:
        from vllm import LLM, SamplingParams  # noqa: F401
    except ImportError as exc:  # pragma: no cover - GPU-only
        raise RuntimeError(
            "vllm is not installed. Install only on a GPU host "
            "(Docs/runbooks/local-safety.md, Docs/runbooks/runtime-pins.md)."
        ) from exc
    from vllm import LLM, SamplingParams

    return LLM, SamplingParams


class VllmEngineRunner(BaselineRunner):
    """Shared load path for full-prefill and native-prefix strategies."""

    def __init__(
        self,
        name: str,
        *,
        enable_prefix_caching: bool,
        model: str | None = None,
        max_model_len: int = 4096,
        max_tokens: int = 1,
    ) -> None:
        self.name = name
        self.enable_prefix_caching = enable_prefix_caching
        self.model = model or "Qwen/Qwen3-8B"
        self.max_model_len = max_model_len
        self.max_tokens = max_tokens
        self._llm: Any = None
        self._sampling: Any = None

    def _setup_impl(self) -> None:
        LLM, SamplingParams = _require_vllm()
        self._llm = LLM(
            model=self.model,
            max_model_len=self.max_model_len,
            trust_remote_code=True,
            enable_prefix_caching=self.enable_prefix_caching,
        )
        self._sampling = SamplingParams(
            max_tokens=self.max_tokens,
            temperature=0.0,
        )

    def run_one(self, request: BaselineRequest) -> BaselineResult:
        if not self._is_setup or self._llm is None:
            raise RuntimeError("setup() must be called before run_one()")
        t0 = time.perf_counter()
        outs = self._llm.generate([request.prompt], self._sampling)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        text = outs[0].outputs[0].text if outs and outs[0].outputs else ""
        return BaselineResult(
            request_id=request.request_id,
            strategy=self.name,
            ttft_ms=elapsed_ms,  # max_tokens=1 → wall-clock ≈ TTFT
            prefill_ms=elapsed_ms,
            output_text=text,
            extras={
                "enable_prefix_caching": self.enable_prefix_caching,
                "model": self.model,
                "max_model_len": self.max_model_len,
            },
        )

    def teardown(self) -> None:
        self._llm = None
        self._sampling = None
        self._is_setup = False


def full_prefill_runner(**kwargs: Any) -> VllmEngineRunner:
    return VllmEngineRunner("full_prefill", enable_prefix_caching=False, **kwargs)


def prefix_cache_runner(**kwargs: Any) -> VllmEngineRunner:
    return VllmEngineRunner("prefix_cache", enable_prefix_caching=True, **kwargs)


def smoke_runner(**kwargs: Any) -> VllmEngineRunner:
    return VllmEngineRunner("smoke", enable_prefix_caching=True, **kwargs)
