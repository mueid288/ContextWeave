"""CPU tests for workload-local H3 slice calibration."""

from __future__ import annotations

from contextweave.planner.v0 import ConfigId, ReasonCode, RequestView, plan
from contextweave.risk.slice_calibration import (
    SliceCalibration,
    SliceKey,
    parse_slice,
)


def test_parse_slice():
    assert parse_slice("h03_ACB_city") == ("ACB", "city")
    assert parse_slice("r00_ABC_year") == ("ABC", "year")
    assert parse_slice("bad") is None


def test_from_observations_marks_unsafe_cells():
    cal = SliceCalibration.from_c3_observations(
        [
            ("ABC", "city", 1.0),
            ("ABC", "city", 1.0),
            ("BAC", "year", 0.0),
            ("BAC", "year", 0.0),
        ]
    )
    assert cal.is_safe("ABC", "city")
    assert not cal.is_safe("BAC", "year")
    assert not cal.is_safe("CAB", "code")  # unknown → refuse
    assert not cal.is_safe(None, "city")


def test_slice_key_from_request_id():
    k = SliceKey.from_request_id("h02_CAB_code")
    assert k is not None
    assert k.chunk_order == "CAB"
    assert k.fact_type == "code"


def test_planner_allows_c3_only_when_slice_calibrated_safe():
    cal = SliceCalibration.from_c3_observations([("BCA", "year", 1.0)])
    d = plan(
        RequestView(
            has_validated_nonprefix_artifacts=True,
            chunk_order="BCA",
            fact_type="year",
            slice_calibration=cal,
        )
    )
    assert d.chosen == ConfigId.C3_EPIC


def test_planner_refuses_c3_on_unknown_or_unsafe_slice():
    cal = SliceCalibration.from_c3_observations([("BCA", "year", 1.0)])
    d_unsafe = plan(
        RequestView(
            has_validated_nonprefix_artifacts=True,
            chunk_order="BAC",
            fact_type="year",
            slice_calibration=cal,
        )
    )
    assert d_unsafe.chosen == ConfigId.C0_FULL_PREFILL
    assert (
        ReasonCode.QUALITY_RISK_EXCEEDS_POLICY.value
        in d_unsafe.discarded[ConfigId.C3_EPIC.value]
    )

    d_none = plan(
        RequestView(
            has_validated_nonprefix_artifacts=True,
            chunk_order="BCA",
            fact_type="year",
            slice_calibration=None,
        )
    )
    assert d_none.chosen == ConfigId.C0_FULL_PREFILL
