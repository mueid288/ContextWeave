"""Rule-based composition planner v0 (PRD §7.6) — CPU only.

Uses offline calibration from Phase 0 / G1 / H3 measurements. Does **not** load
models or claim correctness guarantees; it selects among C0/C1/C3/C4 with
explicit reason codes.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import Enum
from typing import Any

from contextweave.provenance.trust import (
    ArtifactBuildMode,
    CrossTrustReuseError,
    IllegalBuildModeError,
    ProvenanceRecord,
    TrustNamespace,
    TrustNamespaceKind,
    assert_reuse_allowed,
)
from contextweave.risk.keydev import predict_c3_quality_fail as keydev_refuse
from contextweave.risk.slice_calibration import SliceCalibration


class ConfigId(str, Enum):
    C0_FULL_PREFILL = "C0"
    C1_EXACT_PREFIX = "C1"
    C3_EPIC = "C3"  # EPIC LegoLink (dedicated fork stack)
    C4_CACHEBLEND = "C4"  # CacheBlend-style selective recompute


class ReasonCode(str, Enum):
    PREFIX_HIT = "prefix_hit"
    QUALITY_RISK_EXCEEDS_POLICY = "quality_risk_exceeds_policy"
    LATENCY_NO_WIN_VS_PREFILL = "latency_no_win_vs_prefill"
    METHOD_UNSUPPORTED = "method_unsupported"
    ARTIFACT_INVALID = "artifact_invalid"
    FALLBACK_PREFILL = "fallback_prefill"
    LOWEST_COST_SAFE = "lowest_cost_safe"


@dataclass(frozen=True)
class MethodCalibration:
    """Offline slice calibration (from G1 or later sweeps)."""

    config: ConfigId
    # Predicted relative TTFT vs full prefill (1.0 = same; 0.85 = 15% faster).
    ttft_vs_prefill: float
    # Absolute quality points vs full prefill (negative = worse). None = unknown → refuse.
    quality_delta_points: float | None
    supported: bool = True
    notes: str = ""


@dataclass(frozen=True)
class PlannerPolicy:
    """Quality / latency bars (PRD proposed defaults; owner-ratified)."""

    # Refuse reuse if quality_delta_points < -max_quality_drop.
    max_quality_drop_points: float = 2.0
    # Prefer reuse only if predicted TTFT ≤ this fraction of prefill.
    min_ttft_speedup: float = 0.85  # ≥15% faster
    # If quality unknown for a method, refuse it.
    refuse_unknown_quality: bool = True
    # Non-prefix configs require a passing ProvenanceRecord (FR-13).
    require_provenance_for_nonprefix: bool = True


@dataclass
class RequestView:
    """Minimal request features the v0 planner needs."""

    has_exact_prefix: bool = False
    # Validated non-prefix chunk artifacts available for blend-style reuse.
    has_validated_nonprefix_artifacts: bool = False
    artifacts_valid: bool = True
    # Doc permutation / fact slice for workload-local H3 calibration.
    chunk_order: str | None = None
    fact_type: str | None = None
    # None ⇒ blanket C3 refuse (default). Safe cells only when table present.
    # Prefer runtime keydev when both are set (Stage-1 bailout).
    slice_calibration: SliceCalibration | None = None
    keydev_score: float | None = None
    keydev_threshold: float | None = None
    # FR-13: required for C3/C4 when policy.require_provenance_for_nonprefix.
    provenance: ProvenanceRecord | None = None
    request_trust: TrustNamespace | None = None
    artifact_from_untrusted_content: bool = False


@dataclass
class Decision:
    chosen: ConfigId
    reason_codes: list[str] = field(default_factory=list)
    discarded: dict[str, list[str]] = field(default_factory=dict)
    estimated_ttft_vs_prefill: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "chosen": self.chosen.value,
            "reason_codes": list(self.reason_codes),
            "discarded": {k: list(v) for k, v in self.discarded.items()},
            "estimated_ttft_vs_prefill": self.estimated_ttft_vs_prefill,
        }


# G1-DIAG #2 (2026-10-23) A100 @12k, Qwen3-8B, vLLM 0.18 / lmcache 0.4.2 in-process.
# Gate D bac agree 0.67 ⇒ large quality miss; blend reorder ~1.10× native (not ≥1.15).
G1_CACHEBLEND_A100_12K = MethodCalibration(
    config=ConfigId.C4_CACHEBLEND,
    ttft_vs_prefill=1.0 / 1.10,  # ~0.91 vs native-reorder baseline ≈ modest win
    quality_delta_points=-10.0,  # agree 0.67 vs control — treat as >>2pt policy fail
    supported=True,
    notes=(
        "G1-DIAG #2: bac engagement ~7705 tok / Gate R formal fail; "
        "cba cached≈19; Gate D agree=0.67; Gate E skipped (~1.10×)."
    ),
)

# EPIC: default blanket refuse. C3 only when RequestView.slice_calibration
# marks (order, fact_type) safe (H3 offline slice-cal; see pre-reg-h3-slice-cal).
G1_EPIC_A100_12K = MethodCalibration(
    config=ConfigId.C3_EPIC,
    ttft_vs_prefill=1.0 / 1.9813145219210888,
    quality_delta_points=-50.0,  # no workload table ⇒ refuse
    supported=True,
    notes=(
        "Default refuse C3. Enable per-request via SliceCalibration safe cells "
        "(workload-local; order-only H3 confirm FAIL)."
    ),
)


def default_calibrations() -> dict[ConfigId, MethodCalibration]:
    return {
        ConfigId.C0_FULL_PREFILL: MethodCalibration(
            config=ConfigId.C0_FULL_PREFILL,
            ttft_vs_prefill=1.0,
            quality_delta_points=0.0,
            notes="Reference.",
        ),
        ConfigId.C1_EXACT_PREFIX: MethodCalibration(
            config=ConfigId.C1_EXACT_PREFIX,
            ttft_vs_prefill=1.0 / 2.57,  # G1 step 1 @6k shared
            quality_delta_points=0.0,
            notes="G1 step 1 native prefix ~2.57× at 6k shared tokens.",
        ),
        ConfigId.C3_EPIC: G1_EPIC_A100_12K,
        ConfigId.C4_CACHEBLEND: G1_CACHEBLEND_A100_12K,
    }


def plan(
    request: RequestView,
    *,
    policy: PlannerPolicy | None = None,
    calibrations: dict[ConfigId, MethodCalibration] | None = None,
) -> Decision:
    """PRD §7.6 rule-based planner v0."""
    policy = policy or PlannerPolicy()
    cals = calibrations or default_calibrations()
    discarded: dict[str, list[str]] = {}

    def discard(cfg: ConfigId, *reasons: str) -> None:
        discarded.setdefault(cfg.value, []).extend(reasons)

    if not request.artifacts_valid and request.has_validated_nonprefix_artifacts:
        discard(ConfigId.C3_EPIC, ReasonCode.ARTIFACT_INVALID.value)
        discard(ConfigId.C4_CACHEBLEND, ReasonCode.ARTIFACT_INVALID.value)

    # 1–2: exact prefix wins when present.
    if request.has_exact_prefix:
        cal = cals[ConfigId.C1_EXACT_PREFIX]
        return Decision(
            chosen=ConfigId.C1_EXACT_PREFIX,
            reason_codes=[ReasonCode.PREFIX_HIT.value],
            discarded=discarded,
            estimated_ttft_vs_prefill=cal.ttft_vs_prefill,
        )

    # 3–4: score supported non-prefix methods; drop by quality / latency policy.
    candidates: list[tuple[ConfigId, MethodCalibration]] = []
    for cfg in (ConfigId.C3_EPIC, ConfigId.C4_CACHEBLEND):
        cal = cals.get(cfg)
        if cal is None or not cal.supported:
            discard(cfg, ReasonCode.METHOD_UNSUPPORTED.value)
            continue
        if not request.has_validated_nonprefix_artifacts:
            discard(cfg, ReasonCode.ARTIFACT_INVALID.value)
            continue
        if policy.require_provenance_for_nonprefix:
            if request.provenance is None or request.request_trust is None:
                discard(cfg, ReasonCode.ARTIFACT_INVALID.value)
                continue
            try:
                assert_reuse_allowed(
                    request.provenance.trust_namespace,
                    request.request_trust,
                    artifact_from_untrusted_content=request.artifact_from_untrusted_content,
                    build_mode=request.provenance.build_mode,
                    record=request.provenance,
                )
            except (CrossTrustReuseError, IllegalBuildModeError):
                discard(cfg, ReasonCode.ARTIFACT_INVALID.value)
                continue
        # C3 quality clear: runtime keydev (preferred) or exact-distro slice table.
        if cfg == ConfigId.C3_EPIC:
            cleared = False
            if request.keydev_threshold is not None:
                if keydev_refuse(request.keydev_score, request.keydev_threshold):
                    discard(cfg, ReasonCode.QUALITY_RISK_EXCEEDS_POLICY.value)
                    continue
                cleared = True
                note = "keydev ok"
            else:
                scal = request.slice_calibration
                if scal is None or not scal.is_safe(
                    request.chunk_order, request.fact_type
                ):
                    discard(cfg, ReasonCode.QUALITY_RISK_EXCEEDS_POLICY.value)
                    continue
                cleared = True
                note = "slice_cal safe"
            if cleared:
                cal = replace(
                    cal,
                    quality_delta_points=0.0,
                    notes=(cal.notes + f" | {note}").strip(" |"),
                )
        if cal.quality_delta_points is None and policy.refuse_unknown_quality:
            discard(cfg, ReasonCode.QUALITY_RISK_EXCEEDS_POLICY.value)
            continue
        if (
            cal.quality_delta_points is not None
            and cal.quality_delta_points < -policy.max_quality_drop_points
        ):
            discard(cfg, ReasonCode.QUALITY_RISK_EXCEEDS_POLICY.value)
            continue
        if cal.ttft_vs_prefill > policy.min_ttft_speedup:
            discard(cfg, ReasonCode.LATENCY_NO_WIN_VS_PREFILL.value)
            continue
        candidates.append((cfg, cal))

    # 5: lowest predicted cost among survivors; else C0.
    if not candidates:
        return Decision(
            chosen=ConfigId.C0_FULL_PREFILL,
            reason_codes=[ReasonCode.FALLBACK_PREFILL.value],
            discarded=discarded,
            estimated_ttft_vs_prefill=1.0,
        )

    candidates.sort(key=lambda x: x[1].ttft_vs_prefill)
    best_cfg, best_cal = candidates[0]
    return Decision(
        chosen=best_cfg,
        reason_codes=[ReasonCode.LOWEST_COST_SAFE.value],
        discarded=discarded,
        estimated_ttft_vs_prefill=best_cal.ttft_vs_prefill,
    )
