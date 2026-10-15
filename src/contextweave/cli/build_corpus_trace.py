"""CLI: Path C — corpus folder → partner_v1 JSONL → optional G0."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import yaml

from contextweave.trace_analysis.metrics import (
    DEFAULT_BYTES_PER_TOKEN,
    DEFAULT_PREFIX_CACHE_BUDGET_GB,
)
from contextweave.workloads.corpus_trace import CorpusTraceConfig, write_corpus_trace
from contextweave.workloads.import_trace import import_trace_file


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build a provisional partner_v1 trace from a local .md/.txt corpus (CPU-only). "
            "No model downloads."
        )
    )
    parser.add_argument(
        "--corpus-dir",
        type=Path,
        default=Path("benchmarks/corpora/sample_docs"),
        help="Directory of .md/.txt documents",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/workloads/corpus_replay_default.yaml"),
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="Output dir (default: benchmarks/workloads/<name>)",
    )
    parser.add_argument(
        "--analyze",
        action="store_true",
        help="Import to canonical JSONL and run provisional G0",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("benchmarks/reports/g0_corpus_replay.md"),
    )
    parser.add_argument(
        "--pad-short-docs-for-demo",
        action="store_true",
        help=(
            "Explicitly pad short docs to chunk_chars_min (forces provisional G0). "
            "Off by default so short corpora fail the median-chunk gate honestly."
        ),
    )
    parser.add_argument("--cache-budget-gb", type=float, default=128.0)
    parser.add_argument(
        "--prefix-cache-budget-gb",
        type=float,
        default=DEFAULT_PREFIX_CACHE_BUDGET_GB,
    )
    parser.add_argument(
        "--bytes-per-token",
        type=float,
        default=DEFAULT_BYTES_PER_TOKEN,
    )
    parser.add_argument(
        "--require-working-set",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    args = parser.parse_args(argv)

    if not args.config.is_file():
        raise FileNotFoundError(f"Config file not found: {args.config}")
    raw = yaml.safe_load(args.config.read_text(encoding="utf-8")) or {}
    cfg = CorpusTraceConfig.from_dict(raw)
    if args.pad_short_docs_for_demo:
        cfg.pad_short_docs_for_demo = True
    out_dir = args.out_dir or Path("benchmarks/workloads") / cfg.name

    meta = write_corpus_trace(args.corpus_dir, out_dir, cfg)
    partner_path = Path(meta["partner_trace"])
    print(f"Corpus files: {meta['num_source_files']}, chunks: {meta['num_chunks']}")
    print(f"Wrote partner_v1: {partner_path}")
    print(f"Catalog: {out_dir / 'chunk_catalog.json'}")
    print(f"Meta: {out_dir / 'meta.json'}")
    if cfg.pad_short_docs_for_demo:
        print("WARNING: --pad-short-docs-for-demo enabled; G0 stays provisional.")
    print("Note: Path C — provisional G0 (corpus-backed replay, not a serving log).")

    if not args.analyze:
        return 0

    canonical = out_dir / "trace.jsonl"
    stats = import_trace_file(partner_path, canonical, format_name="partner_v1")
    print(
        f"Imported {stats.rows_out}/{stats.rows_in} "
        f"(synthetic_tokens={stats.synthetic_token_rows})"
    )

    from contextweave.trace_analysis.metrics import (
        analyze_trace,
        evaluate_g0,
        render_report,
    )
    from contextweave.trace_analysis.working_set import WorkingSetConfig

    ws_cfg = (
        WorkingSetConfig.from_gb(args.cache_budget_gb, args.bytes_per_token)
        if args.cache_budget_gb > 0
        else None
    )
    prefix_budget = (
        args.prefix_cache_budget_gb if args.prefix_cache_budget_gb > 0 else None
    )
    metrics = analyze_trace(
        canonical,
        working_set_cfg=ws_cfg,
        prefix_cache_budget_gb=prefix_budget,
        bytes_per_token=args.bytes_per_token,
    )
    g0 = evaluate_g0(
        metrics, provisional=True, require_working_set=args.require_working_set
    )
    report = render_report(
        metrics,
        g0,
        trace_path=canonical,
        title="Phase 0A G0 — Corpus Replay (Path C, provisional)",
    )
    report += (
        "\n## Path C note\n\n"
        "Documents are real local files; the request stream is simulated. "
        "`token_count` uses chars/chars_per_token, not a model tokenizer. "
        "Replace with a serving-log export before treating G0 as final.\n"
    )
    if cfg.pad_short_docs_for_demo:
        report += (
            "\n**Demo padding was enabled** (`pad_short_docs_for_demo`); "
            "median chunk length is not an honest corpus measurement.\n"
        )
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report, encoding="utf-8")
    print(report)
    print(f"Wrote report: {args.report}")
    return 0 if g0.passed else 2


if __name__ == "__main__":
    sys.exit(main())
