"""Trace analysis for Phase 0A demand metrics (Gate G0)."""

from contextweave.trace_analysis.chunk_order import (
    CHUNK_ORDER_MODES,
    build_doc_frequency,
    natural_doc_key,
    reorder_chunks,
)
from contextweave.trace_analysis.metrics import (
    DemandMetrics,
    analyze_rows,
    analyze_trace,
    compare_chunk_orders,
    evaluate_g0,
)
from contextweave.trace_analysis.prefix_cache import PrefixCacheSimulator
from contextweave.trace_analysis.working_set import (
    WorkingSetConfig,
    WorkingSetMetrics,
    simulate_working_set,
)

__all__ = [
    "CHUNK_ORDER_MODES",
    "DemandMetrics",
    "PrefixCacheSimulator",
    "WorkingSetConfig",
    "WorkingSetMetrics",
    "analyze_rows",
    "analyze_trace",
    "build_doc_frequency",
    "compare_chunk_orders",
    "evaluate_g0",
    "natural_doc_key",
    "reorder_chunks",
    "simulate_working_set",
]
