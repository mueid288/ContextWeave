"""CLI: analyze a trace for Section 2.2 / Gate G0 metrics."""

from __future__ import annotations

import argparse
from pathlib import Path
import json
import sys

from contextweave.trace_analysis.metrics import (
    DEFAULT_BYTES_PER_TOKEN,
    DEFAULT_PREFIX_CACHE_BUDGET_GB,
    analyze_trace,
    evaluate_g0,
    render_report,
)
from contextweave.trace_analysis.working_set import WorkingSetConfig


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Analyze workload trace for Gate G0 (CPU-only).")
    parser.add_argument("--trace", type=Path, required=True, help="JSONL trace path")
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("benchmarks/reports/g0_report.md"),
        help="Markdown report output path",
    )
    parser.add_argument(
        "--metrics-json",
        type=Path,
        default=None,
        help="Optional JSON metrics dump path",
    )
    parser.add_argument("--threshold-share", type=float, default=0.30)
    parser.add_argument("--threshold-median-chunk", type=float, default=512.0)
    parser.add_argument(
        "--cache-budget-gb",
        type=float,
        default=128.0,
        help="LRU KV storage budget in GB for working-set simulation (v2.1). Use 0 to disable.",
    )
    parser.add_argument(
        "--prefix-cache-budget-gb",
        type=float,
        default=DEFAULT_PREFIX_CACHE_BUDGET_GB,
        help="Native prefix-cache HBM budget in GB (Gemini_3 trap 3). Use 0 for unbounded.",
    )
    parser.add_argument(
        "--bytes-per-token",
        type=float,
        default=DEFAULT_BYTES_PER_TOKEN,
        help="KV bytes per token for working-set sizing (default 8B bf16 GQA)",
    )
    parser.add_argument(
        "--require-working-set",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Fail G0 unless LRU hit share under budget also meets --threshold-share (default on)",
    )
    parser.add_argument(
        "--final",
        action="store_true",
        help="Mark G0 as final (real trace). Default is provisional.",
    )
    args = parser.parse_args(argv)

    if args.cache_budget_gb and args.cache_budget_gb > 0:
        ws_cfg: WorkingSetConfig | None = WorkingSetConfig.from_gb(
            args.cache_budget_gb, args.bytes_per_token
        )
    else:
        ws_cfg = None  # explicit disable

    prefix_budget = args.prefix_cache_budget_gb if args.prefix_cache_budget_gb > 0 else None

    metrics = analyze_trace(
        args.trace,
        working_set_cfg=ws_cfg,
        prefix_cache_budget_gb=prefix_budget,
        bytes_per_token=args.bytes_per_token,
    )
    g0 = evaluate_g0(
        metrics,
        threshold_share=args.threshold_share,
        threshold_median_chunk=args.threshold_median_chunk,
        provisional=not args.final,
        require_working_set=args.require_working_set,
        threshold_working_set_share=args.threshold_share,
    )
    report = render_report(metrics, g0, trace_path=args.trace)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report, encoding="utf-8")
    print(report)
    print(f"\nWrote report: {args.report}")

    if args.metrics_json:
        payload = {
            "metrics": metrics.to_dict(),
            "g0": g0.to_dict(),
        }
        for key in ("chunk_lengths", "context_lengths", "reuse_distances"):
            payload["metrics"].pop(key, None)
        args.metrics_json.parent.mkdir(parents=True, exist_ok=True)
        args.metrics_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote metrics: {args.metrics_json}")

    return 0 if g0.passed else 2


if __name__ == "__main__":
    sys.exit(main())
