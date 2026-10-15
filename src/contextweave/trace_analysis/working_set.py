"""Working-set-constrained chunk cache simulation (PRD v2.1 §G + Gemini_2 §1.1)."""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class WorkingSetConfig:
    budget_bytes: float
    bytes_per_token: float = 131072.0
    policy: str = "lru"

    @classmethod
    def from_gb(cls, budget_gb: float, bytes_per_token: float = 131072.0) -> "WorkingSetConfig":
        return cls(budget_bytes=budget_gb * 1e9, bytes_per_token=bytes_per_token)


@dataclass
class WorkingSetMetrics:
    budget_gb: float
    bytes_per_token: float
    policy: str
    # Same denominator as G0 unconstrained share (includes query + cold prefix).
    post_prefix_prefill_tokens: int = 0
    post_prefix_chunk_tokens: int = 0
    hit_tokens: int = 0
    miss_tokens: int = 0
    admit_tokens: int = 0
    evictions: int = 0
    unique_chunks_touched: int = 0
    peak_bytes: float = 0.0
    final_bytes: float = 0.0

    @property
    def hit_share_of_post_prefix(self) -> float:
        """Decision metric: hits / all post-prefix prefill tokens."""
        if self.post_prefix_prefill_tokens == 0:
            return 0.0
        return self.hit_tokens / self.post_prefix_prefill_tokens

    @property
    def hit_share_of_post_prefix_chunks(self) -> float:
        """Diagnostic: hits / chunk tokens only (excludes query + cold prefix)."""
        if self.post_prefix_chunk_tokens == 0:
            return 0.0
        return self.hit_tokens / self.post_prefix_chunk_tokens

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["hit_share_of_post_prefix"] = self.hit_share_of_post_prefix
        d["hit_share_of_post_prefix_chunks"] = self.hit_share_of_post_prefix_chunks
        return d


class LRUChunkCache:
    def __init__(self, cfg: WorkingSetConfig):
        self.cfg = cfg
        self._order: OrderedDict[str, int] = OrderedDict()
        self.bytes_used = 0.0
        self.peak_bytes = 0.0
        self.evictions = 0

    def _bytes_for(self, n_tokens: int) -> float:
        return n_tokens * self.cfg.bytes_per_token

    def touch_or_admit(self, key: str, n_tokens: int) -> bool:
        if key in self._order:
            self._order.move_to_end(key)
            return True
        need = self._bytes_for(n_tokens)
        if need > self.cfg.budget_bytes:
            return False
        while self.bytes_used + need > self.cfg.budget_bytes and self._order:
            _, old_n = self._order.popitem(last=False)
            self.bytes_used -= self._bytes_for(old_n)
            self.evictions += 1
        self._order[key] = n_tokens
        self.bytes_used += need
        self.peak_bytes = max(self.peak_bytes, self.bytes_used)
        return False


def simulate_working_set(
    events: list[tuple[str, int, int]],
    cfg: WorkingSetConfig,
    *,
    post_prefix_prefill_tokens: int,
) -> WorkingSetMetrics:
    """
    events: (chunk_key, token_count, uncovered_post_prefix_chunk_tokens)
    Decision share uses post_prefix_prefill_tokens as denominator (Gemini_2 §1.1).
    """
    cache = LRUChunkCache(cfg)
    metrics = WorkingSetMetrics(
        budget_gb=cfg.budget_bytes / 1e9,
        bytes_per_token=cfg.bytes_per_token,
        policy=cfg.policy,
        post_prefix_prefill_tokens=post_prefix_prefill_tokens,
    )
    touched: set[str] = set()
    for key, n_tokens, uncovered in events:
        if uncovered <= 0:
            continue
        metrics.post_prefix_chunk_tokens += uncovered
        touched.add(key)
        hit = cache.touch_or_admit(key, n_tokens)
        if hit:
            metrics.hit_tokens += uncovered
        else:
            metrics.miss_tokens += uncovered
            if key in cache._order:
                metrics.admit_tokens += uncovered
    metrics.evictions = cache.evictions
    metrics.unique_chunks_touched = len(touched)
    metrics.peak_bytes = cache.peak_bytes
    metrics.final_bytes = cache.bytes_used
    return metrics
