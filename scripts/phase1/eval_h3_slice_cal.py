#!/usr/bin/env python3
"""CPU eval: H3 workload-local slice calibration (leave-one-trial-out).

  python scripts/phase1/eval_h3_slice_cal.py \\
    --inputs artifacts/phase1-oracle-2026-10-23/oracle_trials.jsonl \\
             artifacts/h3-confirm-2026-10-23/h3_confirm_trials.jsonl \\
    --out artifacts/h3-slice-cal-2026-10-23/report.json --json
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

from contextweave.risk.slice_calibration import parse_slice  # noqa: E402


def _load_pairs(path: Path) -> dict[str, dict[str, dict]]:
    by_req: dict[str, dict[str, dict]] = defaultdict(dict)
    for line in path.read_text().splitlines():
        row = json.loads(line)
        if row.get("config") == "C1":
            continue
        if not row.get("feasible", True):
            continue
        by_req[row["request_id"]][row["config"]] = row
    return by_req


def _loo_same_suite(path: Path) -> dict:
    by_req = _load_pairs(path)
    cells: dict[tuple[str, str], list[tuple[str, dict, dict]]] = defaultdict(list)
    for rid, cfgs in by_req.items():
        c0, c3 = cfgs.get("C0"), cfgs.get("C3")
        if not c0 or not c3:
            continue
        parsed = parse_slice(rid)
        if parsed is None:
            continue
        cells[parsed].append((rid, c0, c3))

    tp = fp = tn = fn = 0
    policy_q: list[float] = []
    policy_t: list[float] = []
    c0_t: list[float] = []
    c0_q: list[float] = []
    c3_q: list[float] = []

    for _cell, trials in sorted(cells.items()):
        # Sort for determinism; first trial = train probe, rest = serve.
        trials = sorted(trials, key=lambda x: x[0])
        if len(trials) < 2:
            # Single observation: fail-closed (refuse C3).
            for _rid, c0, c3 in trials:
                actual_fail = c3["quality"] < 1.0
                refuse = True
                if refuse and actual_fail:
                    tp += 1
                elif refuse and not actual_fail:
                    fp += 1
                elif not refuse and not actual_fail:
                    tn += 1
                else:
                    fn += 1
                policy_q.append(float(c0["quality"]))
                policy_t.append(float(c0["ttft_ms"]))
                c0_t.append(float(c0["ttft_ms"]))
                c0_q.append(float(c0["quality"]))
                c3_q.append(float(c3["quality"]))
            continue

        train = trials[0]
        safe = float(train[2]["quality"]) >= 1.0
        for _rid, c0, c3 in trials[1:]:
            actual_fail = c3["quality"] < 1.0
            refuse = not safe
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
    pass_h = prec >= 0.9 and mean_q >= 0.95 and ttft_red >= 0.20
    return {
        "input": str(path),
        "n_eval_requests": n,
        "rule": "loo_train_first_trial_per_cell; refuse_if_train_unsafe_or_singleton",
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
        "pass_heuristic": pass_h,
    }


def _safe_cells(path: Path) -> set[tuple[str, str]]:
    by_req = _load_pairs(path)
    cell_q: dict[tuple[str, str], list[float]] = defaultdict(list)
    for rid, cfgs in by_req.items():
        c3 = cfgs.get("C3")
        if not c3:
            continue
        parsed = parse_slice(rid)
        if parsed is None:
            continue
        cell_q[parsed].append(float(c3["quality"]))
    return {k for k, qs in cell_q.items() if all(q >= 1.0 for q in qs)}


def _cross_suite(train: Path, test: Path) -> dict:
    safe = _safe_cells(train)
    by_req = _load_pairs(test)
    tp = fp = tn = fn = 0
    for rid, cfgs in sorted(by_req.items()):
        c0, c3 = cfgs.get("C0"), cfgs.get("C3")
        if not c0 or not c3:
            continue
        parsed = parse_slice(rid)
        if parsed is None:
            continue
        actual_fail = c3["quality"] < 1.0
        refuse = parsed not in safe
        if refuse and actual_fail:
            tp += 1
        elif refuse and not actual_fail:
            fp += 1
        elif not refuse and not actual_fail:
            tn += 1
        else:
            fn += 1
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec = tp / (tp + fn) if (tp + fn) else 0.0
    return {
        "train": str(train),
        "test": str(test),
        "train_safe_cells": sorted([f"{o}/{f}" for o, f in safe]),
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "precision": prec,
        "recall": rec,
        "note": "Secondary only — not a pass bar. Transfer expected weak.",
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--inputs", type=Path, nargs="+", required=True)
    p.add_argument("--out", type=Path, default=None)
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)

    same = [_loo_same_suite(path) for path in args.inputs]
    all_pass = all(s["pass_heuristic"] for s in same)

    cross = []
    if len(args.inputs) >= 2:
        a, b = args.inputs[0], args.inputs[1]
        cross = [_cross_suite(a, b), _cross_suite(b, a)]

    payload = {
        "pre_reg": "Docs/pre-reg/pre-reg-h3-slice-cal.md",
        "same_suite_loo": same,
        "cross_suite_transfer": cross,
        "pass_heuristic": all_pass,
        "note": (
            "Same-suite LOO is the pass bar. Cross-suite transfer is diagnostic "
            "only (motivates workload-local tables). Not a G2 claim; p95 unused."
        ),
    }
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(payload, indent=2) + "\n")
        print(f"Wrote {args.out}", flush=True)
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"pass={all_pass} suites={len(same)}")
    return 0 if all_pass else 4


if __name__ == "__main__":
    raise SystemExit(main())
