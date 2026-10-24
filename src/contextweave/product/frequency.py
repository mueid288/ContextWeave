"""Rolling document-frequency prior for live canonical order."""

from __future__ import annotations

from threading import Lock
from typing import Iterable, Mapping


class FrequencyPrior:
    """Process-local counters. Thread-safe. Cold start until ``cold_start_n`` observes."""

    def __init__(self, *, cold_start_n: int = 32) -> None:
        self.cold_start_n = max(0, int(cold_start_n))
        self._counts: dict[str, int] = {}
        self._total_observations = 0
        self._lock = Lock()

    def observe(self, document_ids: Iterable[str]) -> None:
        with self._lock:
            for doc_id in document_ids:
                key = str(doc_id)
                self._counts[key] = self._counts.get(key, 0) + 1
                self._total_observations += 1

    @property
    def total_observations(self) -> int:
        with self._lock:
            return self._total_observations

    def snapshot(self) -> dict[str, int]:
        with self._lock:
            return dict(self._counts)

    def is_cold(self) -> bool:
        return self.total_observations < self.cold_start_n

    def as_mapping(self) -> Mapping[str, int]:
        return self.snapshot()
