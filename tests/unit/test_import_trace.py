from pathlib import Path

import pytest

from contextweave.trace_analysis.metrics import analyze_trace
from contextweave.workloads.import_trace import (
    TraceImportError,
    import_trace_file,
    normalize_row,
)


def test_partner_v1_hash_chunks_are_stable():
    row = {
        "request_id": "r1",
        "query_type": "lookup",
        "prefix_token_ids": [1, 2],
        "chunks": [{"document_id": "d1", "content_hash": "h1", "token_count": 8}],
        "query_token_ids": [9],
        "segments_canonical": True,
    }
    a, fa = normalize_row(row, format_name="partner_v1")
    b, fb = normalize_row(row, format_name="partner_v1")
    assert fa["token_ids_synthetic"]
    assert a["chunk_token_ids"] == b["chunk_token_ids"]
    assert a["context_length"] == 2 + 8 + 1


def test_prefix_content_hash_shared_across_requests():
    """Same system prompt hash ⇒ identical synthetic prefix tokens (prefix cache)."""
    base = {
        "query_type": "lookup",
        "prefix_token_count": 12,
        "prefix_content_hash": "sha256:same-system-prompt",
        "chunks": [{"document_id": "d1", "content_hash": "h1", "token_count": 8}],
        "query_token_count": 3,
        "segments_canonical": True,
    }
    a, fa = normalize_row({**base, "request_id": "r-aaa"}, format_name="partner_v1")
    b, fb = normalize_row({**base, "request_id": "r-bbb"}, format_name="partner_v1")
    assert a["prefix_token_ids"] == b["prefix_token_ids"]
    assert not fa.get("prefix_identity_unknown")
    assert not fb.get("prefix_identity_unknown")


def test_prefix_without_hash_flags_unknown():
    row = {
        "request_id": "r1",
        "query_type": "lookup",
        "prefix_token_count": 10,
        "chunks": [{"document_id": "d1", "content_hash": "h1", "token_count": 4}],
        "query_token_count": 2,
    }
    _, flags = normalize_row(row, format_name="partner_v1")
    assert flags.get("prefix_identity_unknown") is True


def test_strict_import_raises_on_bad_row(tmp_path: Path):
    path = tmp_path / "in.jsonl"
    path.write_text(
        '{"request_id":"ok","chunks":[{"document_id":"d","content_hash":"h","token_count":4}],'
        '"prefix_token_count":2,"query_token_count":1,"segments_canonical":true}\n'
        '{"request_id":"bad","chunks":[{"document_id":"d"}]}\n',
        encoding="utf-8",
    )
    out = tmp_path / "out.jsonl"
    with pytest.raises(TraceImportError, match="strict"):
        import_trace_file(path, out, format_name="partner_v1", strict=True)


def test_import_sample_and_analyze(tmp_path: Path, repo_root: Path):
    src = repo_root / "benchmarks" / "trace_analysis" / "examples" / "partner_v1_sample.jsonl"
    out = tmp_path / "trace.jsonl"
    stats = import_trace_file(src, out, format_name="partner_v1")
    assert stats.rows_out == 5
    assert stats.synthetic_token_rows == 5
    metrics = analyze_trace(out)
    assert metrics.num_requests == 5
    assert metrics.recurring_non_prefix_tokens > 0


def test_text_approx(tmp_path: Path):
    path = tmp_path / "in.jsonl"
    path.write_text(
        '{"request_id":"t1","prefix_text":"sys","chunks":[{"document_id":"d","text":"'
        + ("word " * 200)
        + '"}],"query_text":"q?"}\n',
        encoding="utf-8",
    )
    out = tmp_path / "out.jsonl"
    stats = import_trace_file(path, out, format_name="text_approx")
    assert stats.rows_out == 1
    assert stats.text_approx_rows == 1
