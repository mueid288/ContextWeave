"""Baseline runner interfaces for Phase 0B (GPU). CPU hosts call stubs."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from typing import Any

from contextweave.safety import assert_model_load_allowed


@dataclass
class BaselineRequest:
    request_id: str
    prompt: str
    # Optional pre-tokenized ids when available (research harness).
    token_ids: list[int] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class BaselineResult:
    request_id: str
    strategy: str
    ttft_ms: float | None
    prefill_ms: float | None
    output_text: str | None
    cache_hit_tokens: int | None = None
    recomputed_tokens: int | None = None
    error: str | None = None
    extras: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class BaselineRunner(ABC):
    """Common interface for full prefill / prefix / CacheBlend / EPIC runners."""

    name: str
    _is_setup: bool = False

    def setup(self) -> None:
        """Load model / connect to runtime. Requires GPU + explicit allow."""
        assert_model_load_allowed(f"set up baseline '{self.name}'")
        self._setup_impl()
        self._is_setup = True

    @abstractmethod
    def _setup_impl(self) -> None:
        """Subclass hook after the local-safety gate."""

    @abstractmethod
    def run_one(self, request: BaselineRequest) -> BaselineResult:
        if not self._is_setup:
            raise RuntimeError("setup() must be called before run_one()")

    def teardown(self) -> None:
        return None


class NotAvailableOnCpu(BaselineRunner):
    """Placeholder until a rented GPU environment is provisioned."""

    def __init__(self, name: str, hint: str):
        self.name = name
        self.hint = hint

    def _setup_impl(self) -> None:
        raise RuntimeError(
            f"Baseline '{self.name}' has no local implementation. {self.hint} "
            "See Docs/gpu-runbook.md, Docs/runtime-pins.md, Docs/local-safety.md."
        )

    def run_one(self, request: BaselineRequest) -> BaselineResult:
        if not self._is_setup:
            raise RuntimeError("setup() must be called before run_one()")
        raise RuntimeError(f"Baseline '{self.name}' not available on this machine.")
