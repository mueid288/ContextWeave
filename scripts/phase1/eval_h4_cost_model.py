#!/usr/bin/env python3
"""H4: PRD §7.5 prefill_time_s vs banked C0 TTFT (CPU-only).

  python scripts/phase1/eval_h4_cost_model.py \\
    --out artifacts/h4-cost-model-2026-10-24/report.json --json
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

from contextweave.costmodel.breakeven import (  # noqa: E402
    ModelCostParams,
    prefill_flops,
    prefill_time_s,
)

DEFAULT_SUITES: tuple[tuple[str, str], ...] = (
    ("phase1_oracle", "artifacts/phase1-oracle-2026-10-23/oracle_trials.jsonl"),
    ("h3_confirm_seed99", "artifacts/h3-confirm-2026-10-23/h3_confirm_trials.jsonl"),
    ("h3_keydev_seed99", "artifacts/h3-keydev-2026-10-23/h3_keydev_seed99.jsonl"),
    ("h3_keydev_seed100", "artifacts/h3-keydev-2026-10-23/h3_keydev_seed100.jsonl"),
)

MISTRAL_7B = ModelCostParams(
    name="mistral-7b",
    params=7e9,
    num_layers=32,
    d_model=4096,
    num_kv_heads=8,
    head_dim=128,
    bytes_per_scalar=2.0,
    effective_tflops=450.0,
)


def _c0_ttfTs(path: Path) -> tuple[list[float], int | None]:
    times: list[float] = []
    tokens: list[int] = []
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("config") != "C0" or not row.get("feasible", True):
            continue
        times.append(float(row["ttft_ms"]))
        if "prompt_tokens" in row:
            tokens.append(int(row["prompt_tokens"]))
    n_tok = int(sorted(tokens)[len(tokens) // 2]) if tokens else None
    return times, n_tok


def _suite_row(
    name: str,
    path: Path,
    model: ModelCostParams,
    *,
    default_n: int = 12000,
) -> dict:
    times, n_from_file = _c0_ttfTs(path)
    n = n_from_file or default_n
    mean_ms = sum(times) / len(times) if times else float("nan")
    pred_ms = prefill_time_s(n, model) * 1000.0
    rel = abs(pred_ms - mean_ms) / mean_ms if mean_ms > 0 else float("inf")
    return {
        "suite": name,
        "path": str(path),
        "n_c0": len(times),
        "n_tokens": n,
        "measured_mean_c0_ttft_ms": mean_ms,
        "predicted_prefill_ms": pred_ms,
        "rel_abs_error": rel,
        "within_20pct": rel <= 0.20,
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, default=None)
    p.add_argument("--json", action="store_true")
    p.add_argument("--tflops", type=float, default=450.0)
    args = p.parse_args(argv)

    model = ModelCostParams(
        name=MISTRAL_7B.name,
        params=MISTRAL_7B.params,
        num_layers=MISTRAL_7B.num_layers,
        d_model=MISTRAL_7B.d_model,
        num_kv_heads=MISTRAL_7B.num_kv_heads,
        head_dim=MISTRAL_7B.head_dim,
        bytes_per_scalar=MISTRAL_7B.bytes_per_scalar,
        effective_tflops=args.tflops,
    )

    primary = []
    for name, rel in DEFAULT_SUITES:
        path = ROOT / rel
        if not path.exists():
            primary.append(
                {
                    "suite": name,
                    "path": str(path),
                    "error": "missing",
                    "within_20pct": False,
                }
            )
            continue
        primary.append(_suite_row(name, path, model))

    all_pass = bool(primary) and all(r.get("within_20pct") for r in primary)

    # Secondary: calibrate tflops on confirm seed99 → apply to seed100.
    secondary = None
    cal_path = ROOT / "artifacts/h3-confirm-2026-10-23/h3_confirm_trials.jsonl"
    test_path = ROOT / "artifacts/h3-keydev-2026-10-23/h3_keydev_seed100.jsonl"
    if cal_path.exists() and test_path.exists():
        cal_times, cal_n = _c0_ttfTs(cal_path)
        n = cal_n or 12000
        mean_s = (sum(cal_times) / len(cal_times)) / 1000.0
        flops = prefill_flops(n, model)
        cal_tflops = flops / (mean_s * 1e12) if mean_s > 0 else 0.0
        cal_model = ModelCostParams(
            name=model.name,
            params=model.params,
            num_layers=model.num_layers,
            d_model=model.d_model,
            num_kv_heads=model.num_kv_heads,
            head_dim=model.head_dim,
            bytes_per_scalar=model.bytes_per_scalar,
            effective_tflops=cal_tflops,
        )
        test_row = _suite_row("h3_keydev_seed100_calibrated", test_path, cal_model)
        secondary = {
            "calibrate_suite": "h3_confirm_seed99",
            "calibrated_effective_tflops": cal_tflops,
            "test": test_row,
            "note": "Report only — not a pass bar.",
        }

    payload = {
        "pre_reg": "Docs/pre-reg/pre-reg-h4-cost-model.md",
        "model": {
            "name": model.name,
            "params": model.params,
            "effective_tflops": model.effective_tflops,
        },
        "primary": primary,
        "pass_heuristic": all_pass,
        "secondary_calibrated": secondary,
        "note": (
            "H4 primary = default 450 TFLOP/s ±20% vs measured C0. "
            "Not G2; no new GPU."
        ),
    }
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(payload, indent=2) + "\n")
        print(f"Wrote {args.out}", flush=True)
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"pass={all_pass} suites={len(primary)}")
    return 0 if all_pass else 4


if __name__ == "__main__":
    raise SystemExit(main())
