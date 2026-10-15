"""CLI: generate a synthetic RAG JSONL trace."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import yaml

from contextweave.workloads.synthetic import SyntheticWorkloadConfig, write_trace


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate synthetic RAG workload trace (CPU-only).")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/workloads/synthetic_rag_default.yaml"),
        help="YAML workload config",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="Output directory (default: benchmarks/workloads/<name>)",
    )
    args = parser.parse_args(argv)

    raw = yaml.safe_load(args.config.read_text(encoding="utf-8")) or {}
    cfg = SyntheticWorkloadConfig.from_dict(raw)
    out_dir = args.out_dir or Path("benchmarks/workloads") / cfg.name
    trace_path = write_trace(cfg, out_dir)
    print(f"Wrote trace: {trace_path}")
    print(f"Config: {out_dir / 'config.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
