"""Smoke: compare_chunk_orders on synthetic fixture rows."""

from __future__ import annotations

import json
from pathlib import Path

from contextweave.trace_analysis.metrics import compare_chunk_orders


def test_compare_chunk_orders_runs(tmp_path: Path):
    # Two multi-doc requests sharing "hot" — frequency order should help prefix hits.
    rows = [
        {
            "request_id": "r0",
            "query_type": "synthesis",
            "document_ids": ["rare", "hot"],
            "chunk_token_ids": [[1, 2, 3], [9, 9, 9]],
            "chunk_lengths": [3, 3],
            "prefix_token_ids": [0],
            "query_token_ids": [7],
            "token_ids": [0, 1, 2, 3, 9, 9, 9, 7],
            "segments_canonical": True,
        },
        {
            "request_id": "r1",
            "query_type": "synthesis",
            "document_ids": ["hot", "other"],
            "chunk_token_ids": [[9, 9, 9], [4, 5, 6]],
            "chunk_lengths": [3, 3],
            "prefix_token_ids": [0],
            "query_token_ids": [7],
            "token_ids": [0, 9, 9, 9, 4, 5, 6, 7],
            "segments_canonical": True,
        },
    ]
    path = tmp_path / "t.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    payload = compare_chunk_orders(path, working_set_cfg=None, prefix_cache_budget_gb=None)
    assert payload["n_requests"] == 2
    assert "by_frequency_desc" in payload["deltas_vs_natural"]
    assert payload["overall"]["natural"]["share_prefix_cached"] >= 0.0
