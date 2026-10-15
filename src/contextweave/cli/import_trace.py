"""CLI: import partner traces into canonical G0 JSONL."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from contextweave.trace_analysis.metrics import (
    DEFAULT_BYTES_PER_TOKEN,
    DEFAULT_PREFIX_CACHE_BUDGET_GB,
)
from contextweave.workloads.import_trace import import_trace_file


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Import a real/partner JSONL trace into canonical G0 format (CPU-only)."
    )
    parser.add_argument("--input", type=Path, required=True, help="Partner JSONL path")
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("benchmarks/workloads/imported/trace.jsonl"),
        help="Canonical JSONL output",
    )
    parser.add_argument(
        "--format",
        choices=["auto", "canonical", "partner_v1", "text_approx"],
        default="auto",
    )
    parser.add_argument(
        "--chars-per-token",
        type=float,
        default=4.0,
        help="Only for text_approx format",
    )
    parser.add_argument(
        "--analyze",
        action="store_true",
        help="Also run Gate G0 analysis after import",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("benchmarks/reports/g0_imported.md"),
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

    stats = import_trace_file(
        args.input,
        args.out,
        format_name=args.format,
        chars_per_token=args.chars_per_token,
    )
    print(
        f"Imported {stats.rows_out}/{stats.rows_in} rows "
        f"(format={stats.format_name}, synthetic_tokens={stats.synthetic_token_rows}, "
        f"text_approx={stats.text_approx_rows})"
    )
    if stats.errors:
        print(f"Skipped {len(stats.errors)} row(s):")
        for err in stats.errors[:20]:
            print(f"  - {err}")
    print(f"Wrote {args.out}")
    print(f"Meta: {args.out.parent / 'import_meta.json'}")

    if args.analyze:
        from contextweave.trace_analysis.metrics import (
            analyze_trace,
            evaluate_g0,
            render_report,
        )
        from contextweave.trace_analysis.working_set import WorkingSetConfig

        provisional = bool(stats.synthetic_token_rows or stats.text_approx_rows)
        ws_cfg = None
        if args.cache_budget_gb and args.cache_budget_gb > 0:
            ws_cfg = WorkingSetConfig.from_gb(args.cache_budget_gb, args.bytes_per_token)
        prefix_budget = (
            args.prefix_cache_budget_gb if args.prefix_cache_budget_gb > 0 else None
        )
        metrics = analyze_trace(
            args.out,
            working_set_cfg=ws_cfg,
            prefix_cache_budget_gb=prefix_budget,
            bytes_per_token=args.bytes_per_token,
        )
        g0 = evaluate_g0(
            metrics,
            provisional=provisional,
            require_working_set=args.require_working_set,
        )
        report = render_report(
            metrics, g0, trace_path=args.out, title="Phase 0A G0 — Imported Trace"
        )
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(report, encoding="utf-8")
        print(report)
        print(f"Wrote report: {args.report}")
        return 0 if g0.passed else 2

    return 0 if stats.rows_out > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
