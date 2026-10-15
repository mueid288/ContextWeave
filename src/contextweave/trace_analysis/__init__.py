"""Trace analysis for Phase 0A demand metrics (Gate G0)."""

from contextweave.trace_analysis.metrics import DemandMetrics, analyze_trace, evaluate_g0
from contextweave.trace_analysis.prefix_cache import PrefixCacheSimulator
from contextweave.trace_analysis.working_set import (
    WorkingSetConfig,
    WorkingSetMetrics,
    simulate_working_set,
)

__all__ = [
    "DemandMetrics",
    "PrefixCacheSimulator",
    "WorkingSetConfig",
    "WorkingSetMetrics",
    "analyze_trace",
    "evaluate_g0",
    "simulate_working_set",
]
