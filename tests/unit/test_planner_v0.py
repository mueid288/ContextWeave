"""CPU tests for rule-based planner v0."""

from __future__ import annotations

from contextweave.planner.v0 import (
    ConfigId,
    MethodCalibration,
    PlannerPolicy,
    ReasonCode,
    RequestView,
    default_calibrations,
    plan,
)


def test_prefix_hit_wins():
    d = plan(RequestView(has_exact_prefix=True))
    assert d.chosen == ConfigId.C1_EXACT_PREFIX
    assert ReasonCode.PREFIX_HIT.value in d.reason_codes


def test_g1_epic_preferred_over_refused_cacheblend():
    """EPIC@12k PASS → C3; CacheBlend G1 still refused on quality."""
    d = plan(
        RequestView(
            has_exact_prefix=False,
            has_validated_nonprefix_artifacts=True,
            artifacts_valid=True,
        )
    )
    assert d.chosen == ConfigId.C3_EPIC
    assert ReasonCode.LOWEST_COST_SAFE.value in d.reason_codes
    assert ConfigId.C4_CACHEBLEND.value in d.discarded
    reasons = d.discarded[ConfigId.C4_CACHEBLEND.value]
    assert ReasonCode.QUALITY_RISK_EXCEEDS_POLICY.value in reasons


def test_no_artifacts_falls_back():
    d = plan(RequestView(has_exact_prefix=False, has_validated_nonprefix_artifacts=False))
    assert d.chosen == ConfigId.C0_FULL_PREFILL
    assert ConfigId.C3_EPIC.value in d.discarded
    assert ConfigId.C4_CACHEBLEND.value in d.discarded


def test_safe_fast_blend_would_be_chosen():
    cals = default_calibrations()
    cals[ConfigId.C3_EPIC] = MethodCalibration(
        config=ConfigId.C3_EPIC,
        ttft_vs_prefill=0.50,
        quality_delta_points=0.0,
        supported=False,  # isolate C4 hypothetical
    )
    cals[ConfigId.C4_CACHEBLEND] = MethodCalibration(
        config=ConfigId.C4_CACHEBLEND,
        ttft_vs_prefill=0.80,
        quality_delta_points=-1.0,
        supported=True,
        notes="hypothetical passing calibration",
    )
    d = plan(
        RequestView(has_validated_nonprefix_artifacts=True),
        calibrations=cals,
        policy=PlannerPolicy(),
    )
    assert d.chosen == ConfigId.C4_CACHEBLEND
    assert ReasonCode.LOWEST_COST_SAFE.value in d.reason_codes


def test_latency_bar_alone_discards_modest_win():
    cals = default_calibrations()
    cals[ConfigId.C3_EPIC] = MethodCalibration(
        config=ConfigId.C3_EPIC,
        ttft_vs_prefill=0.50,
        quality_delta_points=0.0,
        supported=False,
    )
    cals[ConfigId.C4_CACHEBLEND] = MethodCalibration(
        config=ConfigId.C4_CACHEBLEND,
        ttft_vs_prefill=0.91,  # ~1.10× — G1-like
        quality_delta_points=-0.5,  # within 2pt
        supported=True,
    )
    d = plan(
        RequestView(has_validated_nonprefix_artifacts=True),
        calibrations=cals,
    )
    assert d.chosen == ConfigId.C0_FULL_PREFILL
    assert ReasonCode.LATENCY_NO_WIN_VS_PREFILL.value in d.discarded[ConfigId.C4_CACHEBLEND.value]
