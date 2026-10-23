#!/usr/bin/env python3
"""CPU: compute Phase 1 oracle upside from measured JSONL trials.

Each line:
  {"request_id":"r1","config":"C0","quality":1.0,"ttft_ms":1000,"feasible":true}

  python scripts/phase1/run_oracle_study.py --input trials.jsonl --json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO_BOOT = Path(__file__).resolve()
for _cand in _REPO_BOOT.parents:
    if (_cand / "pyproject.toml").exists():
        ROOT = _cand
        break
else:
    raise SystemExit("Could not find repo root (pyproject.toml)")
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from contextweave.oracle import ConfigTrial, oracle_upside  # noqa: E402


def _load_trials(path: Path) -> list[ConfigTrial]:
    trials: list[ConfigTrial] = []
    for i, line in enumerate(path.read_text().splitlines(), start=1):
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
            )
        )
    if not trials:
        raise SystemExit(f"No trials in {path}")
    return trials


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--out", type=Path, default=None)
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)

    report = oracle_upside(_load_trials(args.input))
    payload = report.to_dict()
    if args.out:
        args.out.write_text(json.dumps(payload, indent=2) + "\n")
        print(f"Wrote {args.out}", flush=True)
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(
            f"n={report.n_requests} fixed={report.best_fixed_config} "
            f"q_upside_pts={report.quality_upside_points} "
            f"ttft_red={report.ttft_reduction_fraction} "
            f"g2_pass={report.g2_pass}"
        )
    return 0 if report.g2_pass else 4


if __name__ == "__main__":
    raise SystemExit(main())
