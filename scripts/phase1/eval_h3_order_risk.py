#!/usr/bin/env python3
"""CPU replay of H3 order-risk policy on banked Phase 1 oracle JSONL.

  python scripts/phase1/eval_h3_order_risk.py \\
    --input artifacts/phase1-oracle-2026-10-23/oracle_trials.jsonl \\
    --out artifacts/h3-order-risk-2026-10-23/report.json --json
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
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

from contextweave.risk.order_signal import predict_c3_quality_fail  # noqa: E402


def _order_from_rid(rid: str) -> str:
    # r00_ABC_city or h00_ABC_city → ABC; prefer explicit chunk_order in JSON if present
    parts = rid.split("_")
    return parts[1] if len(parts) >= 3 else ""


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--out", type=Path, default=None)
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)

    by_req: dict[str, dict[str, dict]] = defaultdict(dict)
    for line in args.input.read_text().splitlines():
        row = json.loads(line)
        if row.get("config") == "C1":
            continue
        if not row.get("feasible", True):
            continue
        by_req[row["request_id"]][row["config"]] = row

    tp = fp = tn = fn = 0
    policy_q: list[float] = []
    policy_t: list[float] = []
    c0_t: list[float] = []
    c0_q: list[float] = []
    c3_q: list[float] = []

    for rid, cfgs in sorted(by_req.items()):
        c0, c3 = cfgs.get("C0"), cfgs.get("C3")
        if not c0 or not c3:
            continue
        order = str(c3.get("chunk_order") or c0.get("chunk_order") or _order_from_rid(rid))
        actual_fail = c3["quality"] < 1.0
        pred_fail = predict_c3_quality_fail(order)
        if pred_fail and actual_fail:
            tp += 1
        elif pred_fail and not actual_fail:
            fp += 1
        elif not pred_fail and not actual_fail:
            tn += 1
        else:
            fn += 1

        if pred_fail:
            policy_q.append(float(c0["quality"]))
            policy_t.append(float(c0["ttft_ms"]))
        else:
            policy_q.append(float(c3["quality"]))
            policy_t.append(float(c3["ttft_ms"]))
        c0_t.append(float(c0["ttft_ms"]))
        c0_q.append(float(c0["quality"]))
        c3_q.append(float(c3["quality"]))

    n = len(policy_q)
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec = tp / (tp + fn) if (tp + fn) else 0.0
    mean_q = sum(policy_q) / n if n else 0.0
    mean_t = sum(policy_t) / n if n else 0.0
    mean_c0_t = sum(c0_t) / n if n else 0.0
    ttft_red = (1.0 - mean_t / mean_c0_t) if mean_c0_t > 0 else 0.0
    pass_h3 = prec >= 0.9 and mean_q >= 0.95 and ttft_red >= 0.20

    payload = {
        "pre_reg": "Docs/pre-reg/pre-reg-h3-order-risk.md",
        "input": str(args.input),
        "n_requests": n,
        "rule": "refuse_C3_if_order_in_{ACB,BAC}_else_C3; unknown→refuse",
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "precision": prec,
        "recall": rec,
        "policy_mean_quality": mean_q,
        "policy_mean_ttft_ms": mean_t,
        "always_c0_mean_ttft_ms": mean_c0_t,
        "always_c0_mean_quality": sum(c0_q) / n if n else 0.0,
        "always_c3_mean_quality": sum(c3_q) / n if n else 0.0,
        "mean_ttft_reduction_vs_c0": ttft_red,
        "pass_heuristic": pass_h3,
        "note": (
            "In-sample replay on Phase1 oracle suite; pattern is deterministic "
            "here. Not a G2 claim; p95 not used."
        ),
    }
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(payload, indent=2) + "\n")
        print(f"Wrote {args.out}", flush=True)
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(
            f"precision={prec:.3f} mean_q={mean_q:.3f} "
            f"ttft_red={ttft_red:.3f} pass={pass_h3}"
        )
    return 0 if pass_h3 else 4


if __name__ == "__main__":
    raise SystemExit(main())
