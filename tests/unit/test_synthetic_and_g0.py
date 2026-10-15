from pathlib import Path

from contextweave.trace_analysis.metrics import analyze_trace, evaluate_g0
from contextweave.workloads.synthetic import SyntheticWorkloadConfig, write_trace


def test_synthetic_trace_meets_provisional_g0(tmp_path: Path):
    cfg = SyntheticWorkloadConfig(
        name="unit_g0",
        seed=7,
        num_requests=200,
        corpus_size=40,
        chunk_len_min=512,
        chunk_len_max=2048,
        chunk_len_median_target=768,
        synthesis_fraction=0.5,
        shared_prefix_fraction=0.9,
    )
    trace_path = write_trace(cfg, tmp_path)
    metrics = analyze_trace(trace_path)
    g0 = evaluate_g0(metrics, provisional=True)

    assert metrics.num_requests == 200
    assert metrics.total_prefill_tokens > 0
    assert metrics.share_prefix_cached > 0
    assert metrics.median_chunk_length >= 512
    assert g0.passed, g0.rationale


def test_low_recurrence_fails_g0(tmp_path: Path):
    cfg = SyntheticWorkloadConfig(
        name="unit_g0_fail",
        seed=1,
        num_requests=50,
        corpus_size=50,
        # Force near-uniform unique picks by making corpus == requests and alpha~0
        popularity_alpha=0.01,
        reuse_distance_max=1,
        synthesis_fraction=0.0,
        shared_prefix_fraction=1.0,
        chunk_len_min=64,
        chunk_len_max=128,
        chunk_len_median_target=96,
    )
    trace_path = write_trace(cfg, tmp_path)
    metrics = analyze_trace(trace_path)
    g0 = evaluate_g0(metrics, provisional=True)
    assert not g0.passed
