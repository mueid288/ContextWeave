"""CLI: PRD §7.5 cost / break-even table (CPU-only)."""

from __future__ import annotations

import argparse
from pathlib import Path
import json
import sys

from contextweave.costmodel.breakeven import (
    ModelCostParams,
    evaluate_lengths,
    render_markdown,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compute KV size / prefill / break-even bandwidth (no GPU)."
    )
    parser.add_argument(
        "--lengths",
        type=str,
        default="10000,32000,100000",
        help="Comma-separated context lengths N",
    )
    parser.add_argument("--repair-fraction", type=float, default=0.15)
    parser.add_argument("--tflops", type=float, default=450.0)
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("benchmarks/reports/cost_model_8b.md"),
    )
    parser.add_argument(
        "--json",
        type=Path,
        default=Path("benchmarks/reports/cost_model_8b.json"),
    )
    args = parser.parse_args(argv)

    lengths = [int(x.strip()) for x in args.lengths.split(",") if x.strip()]
    model = ModelCostParams(effective_tflops=args.tflops)
    rows = evaluate_lengths(lengths, model, repair_fraction=args.repair_fraction)
    md = render_markdown(rows, model)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(md, encoding="utf-8")
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(
        json.dumps(
            {"model": model.__dict__, "rows": [r.to_dict() for r in rows]},
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(md)
    print(f"\nWrote {args.report}")
    print(f"Wrote {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
