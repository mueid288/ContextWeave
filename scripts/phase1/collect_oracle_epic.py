#!/usr/bin/env python3
"""Phase 1 GPU collect on EPIC fork → JSONL trials for oracle upside.

Measures **C0** (full prefill) and **C3** (LegoLink-8) per request.
**C1** is recorded as ``feasible=false`` on this stack (EPIC demos run with
prefix caching off; do not fake prefix — see pre-reg).

  export CONTEXTWEAVE_ALLOW_MODEL_LOAD=1
  python scripts/phase1/collect_oracle_epic.py \\
    --n-requests 20 --runs 3 --target-context-tokens 12000 \\
    --out oracle_trials.jsonl --report oracle_report.json
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import statistics
import sys
import time
from itertools import cycle
from pathlib import Path

_REPO_BOOT = Path(__file__).resolve()
for _cand in _REPO_BOOT.parents:
    if (_cand / "pyproject.toml").exists():
        ROOT = _cand
        break
else:
    raise SystemExit("Could not find repo root (pyproject.toml)")
SRC = ROOT / "src"
G1_EPIC = ROOT / "scripts" / "g1" / "epic"
for _p in (SRC,):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))


def _load_epic():
    path = G1_EPIC / "g1_epic_bench.py"
    spec = importlib.util.spec_from_file_location("g1_epic_bench", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


ORDERS: tuple[tuple[str, ...], ...] = (
    ("A", "B", "C"),
    ("B", "C", "A"),
    ("C", "A", "B"),
    ("A", "C", "B"),
    ("B", "A", "C"),
    ("C", "B", "A"),
)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--model", default=os.environ.get("SMOKE_MODEL", "mistralai/Mistral-7B-Instruct-v0.2"))
    p.add_argument("--max-model-len", type=int, default=16384)
    p.add_argument("--target-context-tokens", type=int, default=12000)
    p.add_argument("--n-requests", type=int, default=20)
    p.add_argument("--runs", type=int, default=3, help="Timed runs per config after 1 warmup.")
    p.add_argument("--recomp-num", type=int, default=8)
    p.add_argument("--max-tokens", type=int, default=24)
    p.add_argument("--gpu-memory-utilization", type=float, default=0.80)
    p.add_argument("--out", type=Path, required=True, help="JSONL trials path")
    p.add_argument("--report", type=Path, default=None, help="Oracle report JSON")
    p.add_argument("--runtime-id", default="epic-vllm0.7-overlay")
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)

    if os.environ.get("CONTEXTWEAVE_ALLOW_MODEL_LOAD") != "1":
        print("Refusing: set CONTEXTWEAVE_ALLOW_MODEL_LOAD=1 on the GPU host only.", file=sys.stderr)
        return 1
    if args.n_requests < 1:
        print("--n-requests must be ≥1", file=sys.stderr)
        return 2

    epic = _load_epic()
    import vllm
    from transformers import AutoTokenizer
    from vllm import LLM

    probe_path = G1_EPIC / "g1_epic_probe.py"
    spec = importlib.util.spec_from_file_location("g1_epic_probe", probe_path)
    assert spec and spec.loader
    probe = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(probe)
    scan = probe._scan_vllm_tree(Path(vllm.__file__).resolve().parent)
    if not (scan["has_cache_fuse"] and scan["has_hack_kv"]):
        print(json.dumps({"error": "EPIC fork not detected", "scan": scan}, indent=2))
        return 3

    try:
        from vllm.attention.selector import _Backend, global_force_attn_backend

        global_force_attn_backend(_Backend.XFORMERS)
    except Exception as exc:  # noqa: BLE001
        print(f"warn: could not force XFORMERS ({exc})", flush=True)

    tokenizer = AutoTokenizer.from_pretrained(
        args.model, add_bos_token=True, trust_remote_code=True
    )
    system = (
        "You are a careful assistant. Use only the documents. "
        "Prefer a short answer."
    )
    cases = list(epic.QUALITY_CASES)
    scale_q = max((c["question"] for c in cases), key=len)
    filler_chars = epic._filler_chars_for_target(
        tokenizer,
        system=system,
        question=scale_q,
        order=("B", "C", "A"),
        target_context_tokens=args.target_context_tokens,
    )
    print(
        f"oracle collect model={args.model} n={args.n_requests} runs={args.runs} "
        f"filler_chars={filler_chars} target≈{args.target_context_tokens}",
        flush=True,
    )

    print("=== loading EPIC-fork LLM ===", flush=True)
    llm = LLM(
        model=args.model,
        gpu_memory_utilization=args.gpu_memory_utilization,
        trust_remote_code=True,
        enforce_eager=True,
        max_model_len=args.max_model_len,
    )
    if hasattr(llm, "set_tokenizer"):
        llm.set_tokenizer(tokenizer)

    order_cycle = cycle(ORDERS)
    case_cycle = cycle(cases)
    requests: list[dict] = []
    for i in range(args.n_requests):
        order = next(order_cycle)
        case = next(case_cycle)
        docs = epic._docs(filler_chars=filler_chars, order=order)
        prompt = epic._prompt_text(system=system, docs=docs, question=case["question"])
        ntok = len(tokenizer.encode(prompt, add_special_tokens=True))
        if ntok + args.max_tokens > args.max_model_len:
            print(f"request {i} prompt_tokens={ntok} exceeds max_model_len", file=sys.stderr)
            return 2
        requests.append(
            {
                "request_id": f"r{i:02d}_{''.join(order)}_{case['id']}",
                "order": order,
                "case": case,
                "docs": docs,
                "prompt": prompt,
                "prompt_tokens": ntok,
            }
        )

    # One warmup on first request (full).
    print("  [warmup full] discarded", flush=True)
    epic._full_prefill(llm, requests[0]["prompt"], max_tokens=args.max_tokens)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    # Truncate / create
    args.out.write_text("")

    def emit(row: dict) -> None:
        with args.out.open("a") as f:
            f.write(json.dumps(row) + "\n")

    for req in requests:
        rid = req["request_id"]
        gold = req["case"]["gold"]
        print(f"=== {rid} prompt_tokens={req['prompt_tokens']} ===", flush=True)

        # C1: not feasible on EPIC demo stack (prefix caching off).
        emit(
            {
                "request_id": rid,
                "config": "C1",
                "quality": 0.0,
                "ttft_ms": 0.0,
                "feasible": False,
                "runtime_id": args.runtime_id,
                "notes": "EPIC overlay runs without usable exact-prefix path; skipped.",
            }
        )

        # C0 full prefill
        fr_samples: list[float] = []
        fr_text = ""
        for j in range(args.runs):
            ms, fr_text = epic._full_prefill(
                llm, req["prompt"], max_tokens=args.max_tokens
            )
            fr_samples.append(ms)
            print(f"  [C0] {j + 1}/{args.runs} {ms:.0f} ms", flush=True)
        fr_med = statistics.median(fr_samples)
        emit(
            {
                "request_id": rid,
                "config": "C0",
                "quality": 1.0 if epic._contains_gold(fr_text, gold) else 0.0,
                "ttft_ms": fr_med,
                "feasible": True,
                "runtime_id": args.runtime_id,
                "samples_ms": fr_samples,
                "output": fr_text,
                "gold": gold,
            }
        )

        # C3 kvlink
        link_samples: list[float] = []
        link_text = ""
        for j in range(args.runs):
            ms, link_text = epic._collect_and_link(
                llm,
                tokenizer,
                system=system,
                docs=req["docs"],
                question=req["case"]["question"],
                recomp_num=args.recomp_num,
                max_tokens=args.max_tokens,
            )
            link_samples.append(ms)
            print(f"  [C3] {j + 1}/{args.runs} {ms:.0f} ms", flush=True)
        link_med = statistics.median(link_samples)
        emit(
            {
                "request_id": rid,
                "config": "C3",
                "quality": 1.0 if epic._contains_gold(link_text, gold) else 0.0,
                "ttft_ms": link_med,
                "feasible": True,
                "runtime_id": args.runtime_id,
                "samples_ms": link_samples,
                "output": link_text,
                "gold": gold,
            }
        )

    try:
        del llm
    except Exception:  # noqa: BLE001
        pass

    from contextweave.oracle import ConfigTrial, oracle_upside

    trials: list[ConfigTrial] = []
    for line in args.out.read_text().splitlines():
        row = json.loads(line)
        trials.append(
            ConfigTrial(
                request_id=row["request_id"],
                config=row["config"],
                quality=float(row["quality"]),
                ttft_ms=float(row["ttft_ms"]),
                feasible=bool(row.get("feasible", True)),
                runtime_id=str(row.get("runtime_id", "")),
                notes=str(row.get("notes", "")),
            )
        )
    report = oracle_upside(trials)
    payload = report.to_dict()
    payload["pre_reg"] = "Docs/pre-reg/pre-reg-phase1-oracle.md"
    payload["model"] = args.model
    payload["n_requests"] = args.n_requests
    payload["runs"] = args.runs
    payload["target_context_tokens"] = args.target_context_tokens
    payload["trials_path"] = str(args.out)
    payload["c1_note"] = "C1 infeasible on EPIC Path A; oracle over {C0,C3}."

    report_path = args.report or args.out.with_suffix(".report.json")
    report_path.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"Wrote {args.out} and {report_path}", flush=True)
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(
            f"g2_pass={payload['g2_pass']} fixed={payload['best_fixed_config']} "
            f"q_upside={payload['quality_upside_points']} "
            f"ttft_red={payload['ttft_reduction_fraction']}",
            flush=True,
        )
    code = 0 if payload["g2_pass"] else 4
    print("exiting (hard) to avoid CUDA teardown hang", flush=True)
    os._exit(code)


if __name__ == "__main__":
    raise SystemExit(main())
