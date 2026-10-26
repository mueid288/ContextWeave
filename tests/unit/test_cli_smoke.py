"""Smoke tests for ContextWeave C1 / field CLI entry points."""
from pathlib import Path
import subprocess
import sys

from contextweave.cli import (
    analyze_trace,
    build_corpus_trace,
    generate_workload,
    import_trace,
)


def _help_ok(module: str) -> None:
    result = subprocess.run(
        [sys.executable, "-m", module, "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "usage" in result.stdout.lower() or "usage" in result.stderr.lower()


def test_analyze_trace_help():
    _help_ok("contextweave.cli.analyze_trace")


def test_generate_workload_help():
    _help_ok("contextweave.cli.generate_workload")


def test_import_trace_help():
    _help_ok("contextweave.cli.import_trace")


def test_build_corpus_trace_help():
    _help_ok("contextweave.cli.build_corpus_trace")


def test_serve_order_help():
    _help_ok("contextweave.cli.serve_order")


def test_field_g0_help():
    _help_ok("contextweave.cli.cw_field_g0")


def test_generate_workload_arg_parsing(tmp_path: Path, repo_root: Path):
    out_dir = tmp_path / "workload_out"
    code = generate_workload.main(
        [
            "--config",
            str(repo_root / "configs" / "workloads" / "synthetic_rag_default.yaml"),
            "--out-dir",
            str(out_dir),
        ]
    )
    assert code == 0
    assert (out_dir / "trace.jsonl").exists()
    assert (out_dir / "config.json").exists()


def test_import_trace_arg_parsing(tmp_path: Path, repo_root: Path):
    out_file = tmp_path / "imported.jsonl"
    code = import_trace.main(
        [
            "--input",
            str(
                repo_root
                / "benchmarks"
                / "trace_analysis"
                / "examples"
                / "partner_v1_sample.jsonl"
            ),
            "--out",
            str(out_file),
            "--format",
            "partner_v1",
        ]
    )
    assert code == 0
    assert out_file.exists()


def test_analyze_trace_arg_parsing(tmp_path: Path, repo_root: Path):
    trace_file = tmp_path / "imported_for_analysis.jsonl"
    import_trace.main(
        [
            "--input",
            str(
                repo_root
                / "benchmarks"
                / "trace_analysis"
                / "examples"
                / "partner_v1_sample.jsonl"
            ),
            "--out",
            str(trace_file),
            "--format",
            "partner_v1",
        ]
    )
    report_file = tmp_path / "g0_analysis.md"
    metrics_file = tmp_path / "metrics.json"
    code = analyze_trace.main(
        [
            "--trace",
            str(trace_file),
            "--report",
            str(report_file),
            "--metrics-json",
            str(metrics_file),
            "--require-working-set",
        ]
    )
    assert code == 0
    assert report_file.exists()
    assert metrics_file.exists()


def test_build_corpus_trace_arg_parsing(tmp_path: Path, repo_root: Path):
    out_dir = tmp_path / "corpus_out"
    code = build_corpus_trace.main(
        [
            "--corpus-dir",
            str(repo_root / "benchmarks" / "corpora" / "sample_docs"),
            "--config",
            str(repo_root / "configs" / "workloads" / "corpus_replay_default.yaml"),
            "--out-dir",
            str(out_dir),
        ]
    )
    assert code == 0
    assert out_dir.exists()
