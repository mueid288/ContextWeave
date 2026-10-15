from pathlib import Path

from contextweave.tokenization.boundaries import (
    ChunkingConfig,
    assemble_prompt_token_ids,
    canonicalize_segment_tokens,
    pad_token_count_to_block,
)
from contextweave.trace_analysis.metrics import analyze_trace, evaluate_g0
from contextweave.trace_analysis.working_set import WorkingSetConfig, simulate_working_set


def test_pad_to_block():
    assert pad_token_count_to_block(15, 16) == 16
    assert pad_token_count_to_block(16, 16) == 16
    assert pad_token_count_to_block(17, 16) == 32


def test_boundary_then_pad_alignment():
    cfg = ChunkingConfig(boundary_token_ids=(7, 7), kv_block_size=4, pad_to_block=True)
    # Boundary appended before pad so segments stay page-aligned when concatenated.
    seg = canonicalize_segment_tokens([10, 11], cfg, append_boundary=True)
    assert seg == [10, 11, 7, 7]
    assert len(seg) % 4 == 0

    out, chunks, prefix = assemble_prompt_token_ids(
        prefix_token_ids=[1, 2],
        chunk_token_ids=[[10, 11], [20]],
        query_token_ids=[99],
        cfg=cfg,
    )
    assert prefix == [1, 2, 7, 7]
    assert all(len(c) % 4 == 0 for c in chunks)
    # Chunk starts must be 0 mod block relative to prompt start.
    assert len(prefix) % 4 == 0
    assert (len(prefix) + len(chunks[0])) % 4 == 0
    assert 99 in out


def test_lru_hit_share_under_tiny_budget():
    cfg = WorkingSetConfig.from_gb(0.15, bytes_per_token=131072)
    events = [
        ("a", 1000, 1000),
        ("b", 1000, 1000),
        ("a", 1000, 1000),
        ("a", 1000, 1000),
    ]
    m = simulate_working_set(events, cfg, post_prefix_prefill_tokens=4000)
    assert m.post_prefix_chunk_tokens == 4000
    assert m.post_prefix_prefill_tokens == 4000
    assert m.hit_tokens < m.post_prefix_chunk_tokens
    assert m.hit_share_of_post_prefix == m.hit_tokens / 4000
    assert m.evictions >= 1


def test_analyze_with_working_set(tmp_path: Path):
    rows = []
    prefix = list(range(10))
    chunk_a = list(range(100, 100 + 512))
    chunk_b = list(range(1000, 1000 + 512))
    import json

    sequences = [
        ([chunk_a], ["a"], "lookup"),
        ([chunk_b, chunk_a], ["b", "a"], "synthesis"),
        ([chunk_a, chunk_b], ["a", "b"], "synthesis"),
        ([chunk_b, chunk_a], ["b", "a"], "synthesis"),
    ]
    for i, (chunks, docs, qtype) in enumerate(sequences):
        toks = prefix + [t for c in chunks for t in c] + [9000 + i]
        rows.append(
            json.dumps(
                {
                    "request_id": f"r{i}",
                    "query_type": qtype,
                    "prefix_token_ids": prefix,
                    "document_ids": docs,
                    "chunk_token_ids": chunks,
                    "chunk_lengths": [len(c) for c in chunks],
                    "query_token_ids": [9000 + i],
                    "token_ids": toks,
                    "segments_canonical": True,
                }
            )
        )
    path = tmp_path / "t.jsonl"
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    ws = WorkingSetConfig.from_gb(128.0)
    metrics = analyze_trace(path, working_set_cfg=ws, prefix_cache_budget_gb=None)
    assert metrics.working_set is not None
    assert metrics.working_set.hit_share_of_post_prefix > 0
    # Cold prefix + chunks + query must equal post_prefix denom.
    accounted = (
        metrics.uncovered_prefix_tokens
        + metrics.recurring_non_prefix_tokens
        + metrics.unique_first_seen_chunk_tokens
        + metrics.query_tokens
    )
    assert accounted == metrics.post_prefix_prefill_tokens
    g0 = evaluate_g0(metrics, provisional=True, require_working_set=True)
    assert g0.working_set_hit_share is not None
    # Decision share cannot exceed unconstrained share of recurring tokens
    # when hits == recurring (no extra credit from query denom shrink).
    assert metrics.working_set.hit_share_of_post_prefix <= (
        metrics.share_recurring_non_prefix + 1e-9
    ) or metrics.working_set.hit_tokens < metrics.recurring_non_prefix_tokens
