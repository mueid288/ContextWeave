#!/usr/bin/env python3
"""H4 redo: measured effective TFLOP/s vs A100 peak × MFU prior (CPU).

  python scripts/phase1/eval_h4_mfu.py \\
    --out artifacts/h4-mfu-2026-10-24/report.json --json
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

from contextweave.costmodel.breakeven import ModelCostParams, prefill_flops  # noqa: E402

# Pre-registered (Docs/pre-reg/pre-reg-h4-mfu.md) — do not edit after first run.
A100_BF16_PEAK_TFLOPS = 312.0
MFU_LOW = 0.40
MFU_HIGH = 0.65

SUITES: tuple[tuple[str, str], ...] = (
    ("phase1_oracle", "artifacts/phase1-oracle-2026-10-23/oracle_trials.jsonl"),
    ("h3_confirm_seed99", "artifacts/h3-confirm-2026-10-23/h3_confirm_trials.jsonl"),
    ("h3_keydev_seed99", "artifacts/h3-keydev-2026-10-23/h3_keydev_seed99.jsonl"),
    ("h3_keydev_seed100", "artifacts/h3-keydev-2026-10-23/h3_keydev_seed100.jsonl"),
)

MISTRAL = ModelCostParams(name="mistral-7b", params=7e9, effective_tflops=A100_BF16_PEAK_TFLOPS)


def _c0_mean_s(path: Path) -> tuple[float, int, int]:
    times: list[float] = []
    tokens: list[int] = []
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("config") != "C0" or not row.get("feasible", True):
            continue
        times.append(float(row["ttft_ms"]) / 1000.0)
        if "prompt_tokens" in row:
            tokens.append(int(row["prompt_tokens"]))
    n_tok = int(sorted(tokens)[len(tokens) // 2]) if tokens else 12000
    mean_s = sum(times) / len(times) if times else float("nan")
    return mean_s, n_tok, len(times)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, default=None)
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)

    band_lo = A100_BF16_PEAK_TFLOPS * MFU_LOW
    band_hi = A100_BF16_PEAK_TFLOPS * MFU_HIGH
    rows = []
    for name, rel in SUITES:
        path = ROOT / rel
        mean_s, n_tok, n_c0 = _c0_mean_s(path)
        flops = prefill_flops(n_tok, MISTRAL)
        eff = flops / (mean_s * 1e12) if mean_s > 0 else float("nan")
        mfu = eff / A100_BF16_PEAK_TFLOPS if A100_BF16_PEAK_TFLOPS > 0 else float("nan")
        in_band = band_lo <= eff <= band_hi
        rows.append(
            {
                "suite": name,
                "n_c0": n_c0,
                "n_tokens": n_tok,
                "measured_mean_c0_s": mean_s,
                "implied_effective_tflops": eff,
                "implied_mfu": mfu,
                "in_mfu_prior": in_band,
            }
        )

    all_pass = bool(rows) and all(r["in_mfu_prior"] for r in rows)
    payload = {
        "pre_reg": "Docs/pre-reg/pre-reg-h4-mfu.md",
        "supersedes": "Docs/pre-reg/pre-reg-h4-cost-model.md",
        "peak_tflops_bf16": A100_BF16_PEAK_TFLOPS,
        "mfu_prior": [MFU_LOW, MFU_HIGH],
        "effective_tflops_band": [band_lo, band_hi],
        "suites": rows,
        "in_band": all_pass,
        "pass_heuristic": all_pass,  # exit code only; report as consistency, not PASS
        "label": "consistent_with_mfu_prior_not_validation",
        "note": (
            "In-band = implied effective TFLOP/s from banked C0 lies in peak×MFU band. "
            "Not a cost-model validation (band post-hoc/wide; C0-only). "
            "Old H4 at 450 TFLOP/s was MISSPECIFIED (above peak)."
        ),
    }
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(payload, indent=2) + "\n")
        print(f"Wrote {args.out}", flush=True)
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"pass={all_pass} band=[{band_lo:.1f},{band_hi:.1f}]")
    return 0 if all_pass else 4


if __name__ == "__main__":
    raise SystemExit(main())
