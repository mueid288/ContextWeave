"""Oracle vs best-fixed upside for a scoped config set (PRD §8.2 / G2).

Input is already-measured trials — this module does not load models.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass, field
from statistics import median
from typing import Any, Iterable, Sequence


@dataclass(frozen=True)
class ConfigTrial:
    request_id: str
    config: str  # e.g. C0, C1, C3
    quality: float  # 0..1 (e.g. contains rate)
    ttft_ms: float
    feasible: bool = True
    runtime_id: str = ""
    notes: str = ""


@dataclass
class OracleReport:
    n_requests: int
    configs_seen: list[str]
    best_fixed_config: str | None
    best_fixed_mean_quality: float | None
    best_fixed_p95_ttft_ms: float | None
    oracle_mean_quality: float | None
    oracle_p95_ttft_ms: float | None
    quality_upside_points: float | None  # oracle - fixed, in percentage points (0..100)
    ttft_reduction_fraction: float | None  # 1 - oracle_p95/fixed_p95; ≥0.15 ⇒ 15% lower
    g2_quality_pass: bool
    g2_ttft_pass: bool
    g2_pass: bool
    per_request_oracle: list[dict[str, Any]] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _p95(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = max(0, int(round(0.95 * (len(ordered) - 1))))
    return ordered[idx]


def best_fixed_config(
    trials: Iterable[ConfigTrial],
    *,
    min_quality: float | None = None,
) -> str | None:
    """Pick one config maximizing mean quality, then lower median TTFT (feasible only)."""
    by_cfg: dict[str, list[ConfigTrial]] = defaultdict(list)
    for t in trials:
        if t.feasible:
            by_cfg[t.config].append(t)
    if not by_cfg:
        return None

    def key(cfg: str) -> tuple[float, float]:
        rows = by_cfg[cfg]
        q = sum(r.quality for r in rows) / len(rows)
        if min_quality is not None and q < min_quality:
            return (-1.0, 0.0)
        ttft = median([r.ttft_ms for r in rows])
        return (q, -ttft)

    return max(by_cfg.keys(), key=key)


def oracle_upside(
    trials: Sequence[ConfigTrial],
    *,
    quality_point_scale: float = 100.0,
    g2_quality_points: float = 3.0,
    g2_ttft_reduction: float = 0.15,
) -> OracleReport:
    """Per-request: max quality, then min TTFT among feasible configs.

    G2 (ratified): oracle beats best fixed by ≥3 quality points at equal p95 TTFT,
    or ≥15% lower p95 TTFT at equal quality. We report both axes from the same
    selections (simplified equal-quality / equal-TTFT checks on aggregate means/p95).
    """
    by_req: dict[str, list[ConfigTrial]] = defaultdict(list)
    for t in trials:
        by_req[t.request_id].append(t)

    configs_seen = sorted({t.config for t in trials})
    fixed = best_fixed_config(trials)
    per_oracle: list[dict[str, Any]] = []
    o_q: list[float] = []
    o_t: list[float] = []

    for rid, rows in sorted(by_req.items()):
        feasible = [r for r in rows if r.feasible]
        if not feasible:
            continue
        # Prefer higher quality; break ties with lower TTFT.
        best = max(feasible, key=lambda r: (r.quality, -r.ttft_ms))
        per_oracle.append(
            {
                "request_id": rid,
                "config": best.config,
                "quality": best.quality,
                "ttft_ms": best.ttft_ms,
            }
        )
        o_q.append(best.quality)
        o_t.append(best.ttft_ms)

    if not per_oracle or fixed is None:
        return OracleReport(
            n_requests=len(per_oracle),
            configs_seen=configs_seen,
            best_fixed_config=fixed,
            best_fixed_mean_quality=None,
            best_fixed_p95_ttft_ms=None,
            oracle_mean_quality=None,
            oracle_p95_ttft_ms=None,
            quality_upside_points=None,
            ttft_reduction_fraction=None,
            g2_quality_pass=False,
            g2_ttft_pass=False,
            g2_pass=False,
            per_request_oracle=per_oracle,
            notes="Insufficient feasible trials.",
        )

    fixed_rows = [t for t in trials if t.config == fixed and t.feasible]
    # Align fixed metrics to the same request ids as oracle.
    fixed_by_id = {t.request_id: t for t in fixed_rows}
    f_q = [fixed_by_id[p["request_id"]].quality for p in per_oracle if p["request_id"] in fixed_by_id]
    f_t = [fixed_by_id[p["request_id"]].ttft_ms for p in per_oracle if p["request_id"] in fixed_by_id]
    if len(f_q) != len(o_q):
        # Fixed config missing some requests — use all fixed rows as fallback.
        f_q = [t.quality for t in fixed_rows]
        f_t = [t.ttft_ms for t in fixed_rows]

    o_mean_q = sum(o_q) / len(o_q)
    f_mean_q = sum(f_q) / len(f_q) if f_q else 0.0
    o_p95 = _p95(o_t)
    f_p95 = _p95(f_t) if f_t else 0.0
    q_upside = (o_mean_q - f_mean_q) * quality_point_scale
    ttft_red = (1.0 - (o_p95 / f_p95)) if f_p95 > 0 else None

    # Equal-quality / equal-TTFT approximate gates on aggregates.
    quality_equal = abs(o_mean_q - f_mean_q) * quality_point_scale <= 1.0
    ttft_equal = f_p95 > 0 and abs(o_p95 - f_p95) / f_p95 <= 0.05
    g2_q = q_upside >= g2_quality_points and (ttft_equal or o_p95 <= f_p95)
    g2_t = (
        ttft_red is not None
        and ttft_red >= g2_ttft_reduction
        and (quality_equal or o_mean_q >= f_mean_q)
    )

    return OracleReport(
        n_requests=len(per_oracle),
        configs_seen=configs_seen,
        best_fixed_config=fixed,
        best_fixed_mean_quality=f_mean_q,
        best_fixed_p95_ttft_ms=f_p95,
        oracle_mean_quality=o_mean_q,
        oracle_p95_ttft_ms=o_p95,
        quality_upside_points=q_upside,
        ttft_reduction_fraction=ttft_red,
        g2_quality_pass=g2_q,
        g2_ttft_pass=g2_t,
        g2_pass=g2_q or g2_t,
        per_request_oracle=per_oracle,
        notes=(
            "G2 uses ratified bars from Docs/status/phase1-go-memo.md. "
            "Equal quality/TTFT checks are aggregate tolerances (±1pt / ±5% p95)."
        ),
    )
