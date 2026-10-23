"""CPU tests for H3 order-risk signal."""

from __future__ import annotations

from contextweave.risk.order_signal import predict_c3_quality_fail


def test_unsafe_orders():
    assert predict_c3_quality_fail("ACB") is True
    assert predict_c3_quality_fail("BAC") is True


def test_safe_orders():
    assert predict_c3_quality_fail("ABC") is False
    assert predict_c3_quality_fail("BCA") is False
    assert predict_c3_quality_fail("CAB") is False
    assert predict_c3_quality_fail("CBA") is False


def test_unknown_fail_closed():
    assert predict_c3_quality_fail(None) is True
    assert predict_c3_quality_fail("") is True
    assert predict_c3_quality_fail("AB") is True
