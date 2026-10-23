"""H3: workload-local offline slice calibration for EPIC/C3 (CPU-only).

Cell key = ``(chunk_order, fact_type)`` parsed from synthetic request ids
(``r00_ABC_city``) or supplied explicitly. A cell is **safe** iff every
observed C3 quality in the calibration set is ≥ 1.0. Unknown cells are
unsafe (fail-closed).

Order-only ACB/BAC does **not** transfer across golds; this module requires
a table built on the **target** workload distribution.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable


def parse_slice(request_id: str) -> tuple[str, str] | None:
    """``r00_ABC_city`` / ``h03_ACB_city`` → ``(\"ABC\", \"city\")``."""
    parts = request_id.split("_")
    if len(parts) < 3:
        return None
    order, fact = parts[1], parts[2]
    if len(order) != 3 or not order.isalpha():
        return None
    return order.upper(), fact.lower()


@dataclass(frozen=True)
class SliceKey:
    chunk_order: str
    fact_type: str

    @classmethod
    def from_request_id(cls, request_id: str) -> SliceKey | None:
        parsed = parse_slice(request_id)
        if parsed is None:
            return None
        return cls(chunk_order=parsed[0], fact_type=parsed[1])


@dataclass
class SliceCalibration:
    """Offline safe-cell table for one workload / gold distribution."""

    safe_cells: frozenset[tuple[str, str]] = field(default_factory=frozenset)
    # Optional: raw mean quality per cell for diagnostics.
    cell_mean_quality: dict[tuple[str, str], float] = field(default_factory=dict)
    notes: str = ""

    def is_safe(
        self,
        chunk_order: str | None,
        fact_type: str | None,
    ) -> bool:
        if not chunk_order or not fact_type:
            return False
        key = (
            "".join(c for c in chunk_order.upper() if c.isalpha()),
            fact_type.lower(),
        )
        if len(key[0]) != 3:
            return False
        return key in self.safe_cells

    @classmethod
    def from_c3_observations(
        cls,
        observations: Iterable[tuple[str, str, float]],
        *,
        notes: str = "",
    ) -> SliceCalibration:
        """Build table from ``(order, fact, c3_quality)`` rows."""
        from collections import defaultdict

        by: dict[tuple[str, str], list[float]] = defaultdict(list)
        for order, fact, quality in observations:
            o = "".join(c for c in order.upper() if c.isalpha())
            f = fact.lower()
            if len(o) != 3:
                continue
            by[(o, f)].append(float(quality))
        means = {k: sum(v) / len(v) for k, v in by.items()}
        safe = frozenset(k for k, qs in by.items() if all(q >= 1.0 for q in qs))
        return cls(safe_cells=safe, cell_mean_quality=means, notes=notes)
