from pathlib import Path

from contextweave.workloads.corpus_trace import (
    CorpusTraceConfig,
    build_corpus_index,
    write_corpus_trace,
)
from contextweave.workloads.import_trace import import_trace_file
from contextweave.trace_analysis.metrics import analyze_trace, evaluate_g0


def test_sample_corpus_chunks(repo_root: Path):
    cfg = CorpusTraceConfig(num_requests=50, seed=1)
    chunks = build_corpus_index(repo_root / "benchmarks" / "corpora" / "sample_docs", cfg)
    assert len(chunks) >= 8
    assert all(c.token_count >= 512 for c in chunks)
    assert all(c.content_hash.startswith("sha256:") for c in chunks)


def test_end_to_end_corpus_g0(tmp_path: Path, repo_root: Path):
    cfg = CorpusTraceConfig(name="unit_corpus", num_requests=80, seed=2)
    meta = write_corpus_trace(repo_root / "benchmarks" / "corpora" / "sample_docs", tmp_path, cfg)
    partner = Path(meta["partner_trace"])
    canonical = tmp_path / "trace.jsonl"
    stats = import_trace_file(partner, canonical, format_name="partner_v1")
    assert stats.rows_out == 80
    metrics = analyze_trace(canonical)
    g0 = evaluate_g0(metrics, provisional=True)
    assert metrics.num_requests == 80
    assert g0.passed, g0.rationale
