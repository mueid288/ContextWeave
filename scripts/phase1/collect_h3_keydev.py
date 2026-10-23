#!/usr/bin/env python3
"""H3 keydev collect: C0 vs C3 + Layer-0 seam key-deviation (EPIC).

Same Lisbon golds as H3 confirm; records ``keydev`` on each C3 trial for
``eval_h3_keydev.py`` (fit T on seed 99, test seed 100).

  export CONTEXTWEAVE_ALLOW_MODEL_LOAD=1
  python scripts/phase1/collect_h3_keydev.py --n-requests 12 --runs 2 \\
    --filler-seed 99 --out h3_keydev_seed99.jsonl
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import statistics
import sys
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
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

ORDERS: tuple[tuple[str, ...], ...] = (
    ("A", "B", "C"),
    ("B", "C", "A"),
    ("C", "A", "B"),
    ("A", "C", "B"),  # ACB — expected unsafe
    ("B", "A", "C"),  # BAC — expected unsafe
    ("C", "B", "A"),
)

# Distinct from QUALITY_CASES in g1_epic_bench (Karachi/2019/ALPHA-9173).
ALT_CASES: tuple[dict[str, str], ...] = (
    {
        "id": "city",
        "question": "Which city is named in Document Beta? Reply with only the city name.",
        "gold": "Lisbon",
        "B": "### Document Beta\nNamed city: Lisbon.\n",
    },
    {
        "id": "year",
        "question": "Which year is stated in Document Gamma? Reply with only the year.",
        "gold": "2021",
        "C": "### Document Gamma\nStated year: 2021.\n",
    },
    {
        "id": "code",
        "question": "What is the secret code in Document Alpha? Reply with only the code.",
        "gold": "BETA-4242",
        "A": "### Document Alpha\nSecret code: BETA-4242.\n",
    },
)


def _load_epic():
    path = G1_EPIC / "g1_epic_bench.py"
    spec = importlib.util.spec_from_file_location("g1_epic_bench", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _filler(seed: int, n_chars: int) -> str:
    # Deterministic but different from "epic filler. " stock text.
    chunk = f"confirm-{seed}-pad. "
    return (chunk * (n_chars // len(chunk) + 3))[:n_chars]


def _docs_alt(*, filler_chars: int, order: tuple[str, ...], seed: int) -> list[str]:
    fill = _filler(seed, filler_chars)
    blocks = {
        "A": f"### Document Alpha\nSecret code: BETA-4242.\n{fill}\n",
        "B": f"### Document Beta\nNamed city: Lisbon.\n{fill}\n",
        "C": f"### Document Gamma\nStated year: 2021.\n{fill}\n",
    }
    return [blocks[k] for k in order]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--model", default=os.environ.get("SMOKE_MODEL", "mistralai/Mistral-7B-Instruct-v0.2"))
    p.add_argument("--max-model-len", type=int, default=16384)
    p.add_argument("--target-context-tokens", type=int, default=12000)
    p.add_argument("--n-requests", type=int, default=12)
    p.add_argument("--runs", type=int, default=2)
    p.add_argument("--recomp-num", type=int, default=8)
    p.add_argument("--max-tokens", type=int, default=24)
    p.add_argument("--gpu-memory-utilization", type=float, default=0.80)
    p.add_argument("--filler-seed", type=int, default=99)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--runtime-id", default="epic-vllm0.7-overlay-h3keydev")
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)

    if os.environ.get("CONTEXTWEAVE_ALLOW_MODEL_LOAD") != "1":
        print("Refusing: set CONTEXTWEAVE_ALLOW_MODEL_LOAD=1 on the GPU host only.", file=sys.stderr)
        return 1

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
        print(f"warn: XFORMERS ({exc})", flush=True)

    tokenizer = AutoTokenizer.from_pretrained(
        args.model, add_bos_token=True, trust_remote_code=True
    )
    system = (
        "You are a careful assistant. Use only the documents. "
        "Prefer a short answer."
    )
    # Scale filler using longest alt question.
    scale_q = max((c["question"] for c in ALT_CASES), key=len)

    def encode_len(filler_chars: int) -> int:
        docs = _docs_alt(
            filler_chars=filler_chars, order=("B", "C", "A"), seed=args.filler_seed
        )
        prompt = epic._prompt_text(system=system, docs=docs, question=scale_q)
        return len(tokenizer.encode(prompt, add_special_tokens=True))

    lo, hi, best = 64, 2_000_000, 64
    while lo <= hi:
        mid = (lo + hi) // 2
        n = encode_len(mid)
        if n < args.target_context_tokens:
            lo = mid + 1
        else:
            best = mid
            hi = mid - 1
    filler_chars = best
    print(
        f"h3-keydev model={args.model} n={args.n_requests} seed={args.filler_seed} "
        f"filler_chars={filler_chars}",
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
    case_cycle = cycle(ALT_CASES)
    requests: list[dict] = []
    for i in range(args.n_requests):
        order = next(order_cycle)
        case = next(case_cycle)
        docs = _docs_alt(
            filler_chars=filler_chars, order=order, seed=args.filler_seed
        )
        prompt = epic._prompt_text(
            system=system, docs=docs, question=case["question"]
        )
        ntok = len(tokenizer.encode(prompt, add_special_tokens=True))
        requests.append(
            {
                "request_id": f"h{i:02d}_{''.join(order)}_{case['id']}",
                "order": "".join(order),
                "case": case,
                "docs": docs,
                "prompt": prompt,
                "prompt_tokens": ntok,
            }
        )

    print("  [warmup full] discarded", flush=True)
    epic._full_prefill(llm, requests[0]["prompt"], max_tokens=args.max_tokens)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("")

    def emit(row: dict) -> None:
        with args.out.open("a") as f:
            f.write(json.dumps(row) + "\n")

    for req in requests:
        rid = req["request_id"]
        gold = req["case"]["gold"]
        print(f"=== {rid} tokens={req['prompt_tokens']} ===", flush=True)
        emit(
            {
                "request_id": rid,
                "config": "C1",
                "quality": 0.0,
                "ttft_ms": 0.0,
                "feasible": False,
                "runtime_id": args.runtime_id,
                "notes": "prefix N/A on EPIC Path A",
            }
        )
        fr_samples: list[float] = []
        fr_text = ""
        for j in range(args.runs):
            ms, fr_text = epic._full_prefill(
                llm, req["prompt"], max_tokens=args.max_tokens
            )
            fr_samples.append(ms)
            print(f"  [C0] {j + 1}/{args.runs} {ms:.0f} ms", flush=True)
        emit(
            {
                "request_id": rid,
                "config": "C0",
                "quality": 1.0 if epic._contains_gold(fr_text, gold) else 0.0,
                "ttft_ms": statistics.median(fr_samples),
                "feasible": True,
                "runtime_id": args.runtime_id,
                "output": fr_text,
                "gold": gold,
                "chunk_order": req["order"],
            }
        )
        link_samples: list[float] = []
        keydev_samples: list[float] = []
        link_text = ""
        for j in range(args.runs):
            ms, link_text, keydev = epic._collect_and_link(
                llm,
                tokenizer,
                system=system,
                docs=req["docs"],
                question=req["case"]["question"],
                recomp_num=args.recomp_num,
                max_tokens=args.max_tokens,
                return_keydev=True,
            )
            link_samples.append(ms)
            keydev_samples.append(float(keydev))
            print(
                f"  [C3] {j + 1}/{args.runs} {ms:.0f} ms keydev={keydev:.4f}",
                flush=True,
            )
        emit(
            {
                "request_id": rid,
                "config": "C3",
                "quality": 1.0 if epic._contains_gold(link_text, gold) else 0.0,
                "ttft_ms": statistics.median(link_samples),
                "keydev": statistics.median(keydev_samples),
                "feasible": True,
                "runtime_id": args.runtime_id,
                "output": link_text,
                "gold": gold,
                "chunk_order": req["order"],
            }
        )

    try:
        del llm
    except Exception:  # noqa: BLE001
        pass

    meta = {
        "pre_reg": "Docs/pre-reg/pre-reg-h3-keydev.md",
        "filler_seed": args.filler_seed,
        "gold_set": "Lisbon/2021/BETA-4242",
        "n_requests": args.n_requests,
        "trials": str(args.out),
        "signal": "layer0_isolated_seam_discontinuity_mean_1_minus_cos",
        "content_fingerprint": hashlib.sha256(
            (str(args.filler_seed) + "Lisbon2021BETA-4242").encode()
        ).hexdigest()[:16],
    }
    print(json.dumps(meta, indent=2) if args.json else meta)
    print("exiting (hard)", flush=True)
    os._exit(0)


if __name__ == "__main__":
    raise SystemExit(main())
