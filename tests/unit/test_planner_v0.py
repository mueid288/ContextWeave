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
from contextweave.provenance.trust import (
    ArtifactLifecycle,
    ProvenanceRecord,
    TrustNamespace,
    TrustNamespaceKind,
)


def _prov() -> tuple[ProvenanceRecord, TrustNamespace]:
    ns = TrustNamespace("ops", TrustNamespaceKind.OPERATOR)
    rec = ProvenanceRecord(
        artifact_id="a1",
        trust_namespace=ns,
        fingerprint_digest="deadbeef",
        build_context_hash="sha256:x",
        built_in_canonical_context=True,
        lifecycle=ArtifactLifecycle.AVAILABLE,
    )
    return rec, ns


def test_prefix_hit_wins():
    d = plan(RequestView(has_exact_prefix=True))
    assert d.chosen == ConfigId.C1_EXACT_PREFIX
    assert ReasonCode.PREFIX_HIT.value in d.reason_codes


def test_h3_confirm_fail_blanket_refuses_c3_even_on_safe_order():
    """Without provenance + quality clear, C3 is refused (order alone insufficient)."""
    d = plan(
        RequestView(
            has_validated_nonprefix_artifacts=True,
            chunk_order="BCA",  # was "safe" on Phase1 suite only
        )
    )
    assert d.chosen == ConfigId.C0_FULL_PREFILL
    assert ConfigId.C3_EPIC.value in d.discarded
    reasons = d.discarded[ConfigId.C3_EPIC.value]
    assert (
        ReasonCode.ARTIFACT_INVALID.value in reasons
        or ReasonCode.QUALITY_RISK_EXCEEDS_POLICY.value in reasons
    )
    assert ConfigId.C4_CACHEBLEND.value in d.discarded


def test_no_artifacts_falls_back():
    d = plan(
        RequestView(
            has_exact_prefix=False,
            has_validated_nonprefix_artifacts=False,
            chunk_order="BCA",
        )
    )
    assert d.chosen == ConfigId.C0_FULL_PREFILL
    assert ConfigId.C3_EPIC.value in d.discarded


def test_safe_fast_blend_would_be_chosen():
    cals = default_calibrations()
    cals[ConfigId.C3_EPIC] = MethodCalibration(
        config=ConfigId.C3_EPIC,
        ttft_vs_prefill=0.50,
        quality_delta_points=0.0,
        supported=False,
    )
    cals[ConfigId.C4_CACHEBLEND] = MethodCalibration(
        config=ConfigId.C4_CACHEBLEND,
        ttft_vs_prefill=0.80,
        quality_delta_points=-1.0,
        supported=True,
    )
    rec, ns = _prov()
    d = plan(
        RequestView(
            has_validated_nonprefix_artifacts=True,
            chunk_order="BCA",
            provenance=rec,
            request_trust=ns,
        ),
        calibrations=cals,
        policy=PlannerPolicy(),
    )
    assert d.chosen == ConfigId.C4_CACHEBLEND


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
        ttft_vs_prefill=0.91,
        quality_delta_points=-0.5,
        supported=True,
    )
    rec, ns = _prov()
    d = plan(
        RequestView(
            has_validated_nonprefix_artifacts=True,
            chunk_order="BCA",
            provenance=rec,
            request_trust=ns,
        ),
        calibrations=cals,
    )
    assert d.chosen == ConfigId.C0_FULL_PREFILL
    assert ReasonCode.LATENCY_NO_WIN_VS_PREFILL.value in d.discarded[ConfigId.C4_CACHEBLEND.value]
