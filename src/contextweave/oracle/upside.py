"""Oracle vs best-fixed upside for scoped config sets (R1 / legacy G2).

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
    slice_id: str = ""  # optional workload slice for gate-need evidence


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
    ttft_reduction_fraction: float | None  # 1 - oracle_p95/fixed_p95
    # Legacy G2 fields (kept for archived trial replay)
    g2_quality_pass: bool
    g2_ttft_pass: bool
    g2_pass: bool
    # Gate R1 (Docs/plans/2026-10-26-r1-oracle-harness.md)
    r1_quality_pass: bool = False
    r1_ttft_pass: bool = False
    r1_gate_need_pass: bool = False
    r1_pass: bool = False
    c0_mean_quality: float | None = None
    oracle_vs_c0_quality_points: float | None = None
    gate_need_slices: list[str] = field(default_factory=list)
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


def _mean_quality_for_config(
    trials: Sequence[ConfigTrial], config: str, request_ids: Sequence[str]
) -> float | None:
    by_id = {
        t.request_id: t
        for t in trials
        if t.config == config and t.feasible
    }
    vals = [by_id[rid].quality for rid in request_ids if rid in by_id]
    if not vals:
        return None
    return sum(vals) / len(vals)


def _gate_need_slices(
    trials: Sequence[ConfigTrial],
    *,
    quality_point_scale: float,
    c0_margin_points: float,
) -> list[str]:
    """Slices where fixed C3 falls > margin below C0 while C0 or C1 stays within margin of C0."""
    by_slice: dict[str, list[ConfigTrial]] = defaultdict(list)
    for t in trials:
        if t.feasible:
            sid = t.slice_id or "_default"
            by_slice[sid].append(t)

    hits: list[str] = []
    for sid, rows in sorted(by_slice.items()):
        rids = sorted({t.request_id for t in rows})
        c0_q = _mean_quality_for_config(rows, "C0", rids)
        c3_q = _mean_quality_for_config(rows, "C3", rids)
        c1_q = _mean_quality_for_config(rows, "C1", rids)
        if c0_q is None or c3_q is None:
            continue
        c3_gap = (c0_q - c3_q) * quality_point_scale
        if c3_gap <= c0_margin_points:
            continue
        c1_ok = c1_q is not None and (c0_q - c1_q) * quality_point_scale <= c0_margin_points
        c0_ok = True  # C0 is the reference
        if c0_ok or c1_ok:
            hits.append(sid)
    return hits


def oracle_upside(
    trials: Sequence[ConfigTrial],
    *,
    quality_point_scale: float = 100.0,
    g2_quality_points: float = 3.0,
    g2_ttft_reduction: float = 0.15,
    r1_quality_points: float = 2.0,
    r1_ttft_reduction: float = 0.10,
    r1_ttft_equal_tol: float = 0.03,
    r1_c0_quality_margin_points: float = 2.0,
) -> OracleReport:
    """Per-request: max quality, then min TTFT among feasible configs.

    Gate R1 (ratified): oracle beats best fixed by ≥2 quality points at equal p95
    TTFT (±3%), or ≥10% lower p95 TTFT with oracle quality within −2 pp of C0;
    plus ≥1 slice where C3 fails that C0 margin but C0/C1 does not.
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

    empty = OracleReport(
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
        notes="Insufficient feasible trials.",
        per_request_oracle=per_oracle,
    )
    if not per_oracle or fixed is None:
        return empty

    fixed_rows = [t for t in trials if t.config == fixed and t.feasible]
    fixed_by_id = {t.request_id: t for t in fixed_rows}
    f_q = [
        fixed_by_id[p["request_id"]].quality
        for p in per_oracle
        if p["request_id"] in fixed_by_id
    ]
    f_t = [
        fixed_by_id[p["request_id"]].ttft_ms
        for p in per_oracle
        if p["request_id"] in fixed_by_id
    ]
    if len(f_q) != len(o_q):
        f_q = [t.quality for t in fixed_rows]
        f_t = [t.ttft_ms for t in fixed_rows]

    o_mean_q = sum(o_q) / len(o_q)
    f_mean_q = sum(f_q) / len(f_q) if f_q else 0.0
    o_p95 = _p95(o_t)
    f_p95 = _p95(f_t) if f_t else 0.0
    q_upside = (o_mean_q - f_mean_q) * quality_point_scale
    ttft_red = (1.0 - (o_p95 / f_p95)) if f_p95 > 0 else None

    rids = [p["request_id"] for p in per_oracle]
    c0_mean = _mean_quality_for_config(list(trials), "C0", rids)
    vs_c0 = (
        (o_mean_q - c0_mean) * quality_point_scale if c0_mean is not None else None
    )

    # Legacy G2 aggregate tolerances
    quality_equal_g2 = abs(o_mean_q - f_mean_q) * quality_point_scale <= 1.0
    ttft_equal_g2 = f_p95 > 0 and abs(o_p95 - f_p95) / f_p95 <= 0.05
    g2_q = q_upside >= g2_quality_points and (ttft_equal_g2 or o_p95 <= f_p95)
    g2_t = (
        ttft_red is not None
        and ttft_red >= g2_ttft_reduction
        and (quality_equal_g2 or o_mean_q >= f_mean_q)
    )

    # R1
    ttft_equal_r1 = f_p95 > 0 and abs(o_p95 - f_p95) / f_p95 <= r1_ttft_equal_tol
    within_c0 = vs_c0 is not None and vs_c0 >= -r1_c0_quality_margin_points
    r1_q = q_upside >= r1_quality_points and (ttft_equal_r1 or o_p95 <= f_p95)
    r1_t = (
        ttft_red is not None
        and ttft_red >= r1_ttft_reduction
        and within_c0
    )
    need_slices = _gate_need_slices(
        list(trials),
        quality_point_scale=quality_point_scale,
        c0_margin_points=r1_c0_quality_margin_points,
    )
    r1_need = len(need_slices) >= 1
    r1_pass = (r1_q or r1_t) and r1_need

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
        r1_quality_pass=r1_q,
        r1_ttft_pass=r1_t,
        r1_gate_need_pass=r1_need,
        r1_pass=r1_pass,
        c0_mean_quality=c0_mean,
        oracle_vs_c0_quality_points=vs_c0,
        gate_need_slices=need_slices,
        per_request_oracle=per_oracle,
        notes=(
            "R1 bars: Docs/plans/2026-10-26-r1-oracle-harness.md. "
            "G2 fields retained for archived EPIC trial replay only."
        ),
    )


def r1_gate(trials: Sequence[ConfigTrial], **kwargs: Any) -> OracleReport:
    """Alias: evaluate Gate R1 on measured trials."""
    return oracle_upside(trials, **kwargs)
