"""Shared helpers for workload generators and trace importers."""

from __future__ import annotations

import math


def _zipf_weights(n: int, alpha: float) -> list[float]:
    weights = [1.0 / ((i + 1) ** alpha) for i in range(n)]
    total = sum(weights)
    return [w / total for w in weights]


zipf_weights = _zipf_weights


def approx_token_count(text: str, chars_per_token: float) -> int:
    if not text:
        return 0
    return max(1, int(math.ceil(len(text) / chars_per_token)))


_approx_token_count = approx_token_count
