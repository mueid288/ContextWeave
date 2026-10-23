#!/usr/bin/env python3
"""Fit H3 keydev threshold on train JSONL; score on test JSONL.

  python scripts/phase1/eval_h3_keydev.py \\
    --train h3_keydev_seed99.jsonl --test h3_keydev_seed100.jsonl \\
    --out artifacts/h3-keydev-2026-10-23/report.json --json
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

from contextweave.risk.keydev import fit_threshold, predict_c3_quality_fail  # noqa: E402


def _pairs(path: Path) -> list[tuple[str, dict, dict]]:
    by_req: dict[str, dict[str, dict]] = defaultdict(dict)
    for line in path.read_text().splitlines():
        row = json.loads(line)
        if row.get("config") == "C1":
            continue
        if not row.get("feasible", True):
            continue
        by_req[row["request_id"]][row["config"]] = row
    out = []
    for rid, cfgs in sorted(by_req.items()):
        c0, c3 = cfgs.get("C0"), cfgs.get("C3")
        if not c0 or not c3:
            continue
        out.append((rid, c0, c3))
    return out


def _score_policy(
    pairs: list[tuple[str, dict, dict]],
    threshold: float,
) -> dict:
    tp = fp = tn = fn = 0
    policy_q: list[float] = []
    policy_t: list[float] = []
    c0_t: list[float] = []
    c0_q: list[float] = []
    c3_q: list[float] = []
    for _rid, c0, c3 in pairs:
        score = c3.get("keydev")
        actual_fail = c3["quality"] < 1.0
        refuse = predict_c3_quality_fail(
            None if score is None else float(score), threshold
        )
        if refuse and actual_fail:
            tp += 1
        elif refuse and not actual_fail:
            fp += 1
        elif not refuse and not actual_fail:
            tn += 1
        else:
            fn += 1
        if refuse:
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
    return {
        "n_requests": n,
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
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--train", type=Path, required=True)
    p.add_argument("--test", type=Path, required=True)
    p.add_argument("--out", type=Path, default=None)
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)

    train_pairs = _pairs(args.train)
    fit_rows = [
        (float(c3["keydev"]), c3["quality"] < 1.0)
        for _rid, _c0, c3 in train_pairs
        if c3.get("keydev") is not None
    ]
    fit = fit_threshold(fit_rows)
    test_metrics = _score_policy(_pairs(args.test), fit.threshold)
    pass_h = (
        fit.trainable
        and test_metrics["precision"] >= 0.9
        and test_metrics["policy_mean_quality"] >= 0.95
        and test_metrics["mean_ttft_reduction_vs_c0"] >= 0.20
    )
    payload = {
        "pre_reg": "Docs/pre-reg/pre-reg-h3-keydev.md",
        "train": str(args.train),
        "test": str(args.test),
        "fit": {
            "threshold": fit.threshold,
            "train_precision": fit.train_precision,
            "trainable": fit.trainable,
            "notes": fit.notes,
            "n_train_with_keydev": len(fit_rows),
        },
        "test_metrics": test_metrics,
        "pass_heuristic": pass_h,
        "note": (
            "Fit T on train keydev; apply to test. Not a G2 claim; p95 unused. "
            "Runtime Stage-1 signal (not static slice-cal)."
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
            f"T={fit.threshold:.4f} test_prec={test_metrics['precision']:.3f} "
            f"mean_q={test_metrics['policy_mean_quality']:.3f} pass={pass_h}"
        )
    return 0 if pass_h else 4


if __name__ == "__main__":
    raise SystemExit(main())
