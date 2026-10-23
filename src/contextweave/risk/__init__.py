"""Cheap risk signals for planner refusal (H3)."""

from contextweave.risk.order_signal import (
    UNSAFE_EPIC_ORDERS,
    predict_c3_quality_fail,
)
from contextweave.risk.slice_calibration import (
    SliceCalibration,
    SliceKey,
    parse_slice,
)

__all__ = [
    "UNSAFE_EPIC_ORDERS",
    "predict_c3_quality_fail",
    "SliceCalibration",
    "SliceKey",
    "parse_slice",
]
