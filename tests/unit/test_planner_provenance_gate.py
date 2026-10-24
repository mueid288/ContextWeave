"""FR-13 provenance must gate non-prefix planner choices (desk pre-reg)."""

from __future__ import annotations

from contextweave.planner.v0 import ConfigId, ReasonCode, RequestView, plan
from contextweave.provenance.trust import (
    ArtifactLifecycle,
    ProvenanceRecord,
    TrustNamespace,
    TrustNamespaceKind,
)
from contextweave.risk.slice_calibration import SliceCalibration


def _ops() -> TrustNamespace:
    return TrustNamespace("ops", TrustNamespaceKind.OPERATOR)


def _available(ns: TrustNamespace | None = None) -> ProvenanceRecord:
    ns = ns or _ops()
    return ProvenanceRecord(
        artifact_id="a1",
        trust_namespace=ns,
        fingerprint_digest="deadbeef",
        build_context_hash="sha256:x",
        built_in_canonical_context=True,
        lifecycle=ArtifactLifecycle.AVAILABLE,
    )


def test_keydev_ok_without_provenance_refuses_c3():
    d = plan(
        RequestView(
            has_validated_nonprefix_artifacts=True,
            keydev_score=0.05,
            keydev_threshold=0.5,
        )
    )
    assert d.chosen == ConfigId.C0_FULL_PREFILL
    assert ReasonCode.ARTIFACT_INVALID.value in d.discarded[ConfigId.C3_EPIC.value]


def test_keydev_ok_quarantined_refuses_c3():
    rec = _available()
    rec.lifecycle = ArtifactLifecycle.QUARANTINED
    d = plan(
        RequestView(
            has_validated_nonprefix_artifacts=True,
            keydev_score=0.05,
            keydev_threshold=0.5,
            provenance=rec,
            request_trust=_ops(),
        )
    )
    assert d.chosen == ConfigId.C0_FULL_PREFILL
    assert ReasonCode.ARTIFACT_INVALID.value in d.discarded[ConfigId.C3_EPIC.value]


def test_keydev_ok_untrusted_refuses_c3():
    bad = TrustNamespace("pool", TrustNamespaceKind.UNTRUSTED)
    d = plan(
        RequestView(
            has_validated_nonprefix_artifacts=True,
            keydev_score=0.05,
            keydev_threshold=0.5,
            provenance=_available(bad),
            request_trust=bad,
        )
    )
    assert d.chosen == ConfigId.C0_FULL_PREFILL
    assert ReasonCode.ARTIFACT_INVALID.value in d.discarded[ConfigId.C3_EPIC.value]


def test_keydev_ok_good_provenance_allows_c3():
    d = plan(
        RequestView(
            has_validated_nonprefix_artifacts=True,
            keydev_score=0.05,
            keydev_threshold=0.5,
            provenance=_available(),
            request_trust=_ops(),
        )
    )
    assert d.chosen == ConfigId.C3_EPIC


def test_keydev_fail_good_provenance_still_c0():
    d = plan(
        RequestView(
            has_validated_nonprefix_artifacts=True,
            keydev_score=0.9,
            keydev_threshold=0.5,
            provenance=_available(),
            request_trust=_ops(),
        )
    )
    assert d.chosen == ConfigId.C0_FULL_PREFILL
    assert (
        ReasonCode.QUALITY_RISK_EXCEEDS_POLICY.value
        in d.discarded[ConfigId.C3_EPIC.value]
    )


def test_slice_cal_also_requires_provenance():
    cal = SliceCalibration.from_c3_observations([("BCA", "year", 1.0)])
    d = plan(
        RequestView(
            has_validated_nonprefix_artifacts=True,
            chunk_order="BCA",
            fact_type="year",
            slice_calibration=cal,
        )
    )
    assert d.chosen == ConfigId.C0_FULL_PREFILL
