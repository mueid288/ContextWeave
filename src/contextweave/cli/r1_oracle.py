"""CPU: Gate R1 oracle upside from measured JSONL trials (no model load)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from contextweave.oracle import ConfigTrial, oracle_upside


def _load_trials(path: Path) -> list[ConfigTrial]:
    trials: list[ConfigTrial] = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        row = json.loads(line)
        trials.append(
            ConfigTrial(
                request_id=str(row["request_id"]),
                config=str(row["config"]),
                quality=float(row["quality"]),
                ttft_ms=float(row["ttft_ms"]),
                feasible=bool(row.get("feasible", True)),
                runtime_id=str(row.get("runtime_id", "")),
                notes=str(row.get("notes", "")),
                slice_id=str(row.get("slice_id", "")),
            )
        )
    if not trials:
        raise SystemExit(f"No trials in {path}")
    return trials


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Analyze banked R1 oracle trials (CPU). See Docs/plans/2026-10-26-r1-oracle-harness.md"
    )
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--report", type=Path, default=None, help="Write JSON report")
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)

    report = oracle_upside(_load_trials(args.input))
    payload = report.to_dict()
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(payload, indent=2) + "\n")
        print(f"Wrote {args.report}", flush=True)
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(
            f"n={report.n_requests} fixed={report.best_fixed_config} "
            f"q_upside_pts={report.quality_upside_points} "
            f"ttft_red={report.ttft_reduction_fraction} "
            f"r1_pass={report.r1_pass} gate_need={report.r1_gate_need_pass} "
            f"slices={report.gate_need_slices}"
        )
    return 0 if report.r1_pass else 4


if __name__ == "__main__":
    raise SystemExit(main())
