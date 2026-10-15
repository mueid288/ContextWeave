"""Synthetic and recorded workload utilities for Phase 0A."""

from contextweave.workloads.corpus_trace import CorpusTraceConfig, write_corpus_trace
from contextweave.workloads.import_trace import import_trace_file
from contextweave.workloads.synthetic import SyntheticWorkloadConfig, generate_trace

__all__ = [
    "SyntheticWorkloadConfig",
    "generate_trace",
    "import_trace_file",
    "CorpusTraceConfig",
    "write_corpus_trace",
]
