#!/usr/bin/env python3
"""G1 matched-pin quality bench — control vs blend (GPU).

Modes:
  native  — no LMCache (sanity)
  control — LMCacheMPConnector, blend server should be default engine (no blend)
  blend   — LMCacheMPConnector against ``lmcache server --engine-type blend``

  export CONTEXTWEAVE_ALLOW_MODEL_LOAD=1
  python scripts/g1_matched_quality_bench.py --mode control --json | tee g1_matched_control.json
  python scripts/g1_matched_quality_bench.py --mode blend --order bac --json | tee g1_matched_blend_bac.json
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def _load_scoring():
    path = ROOT / "scripts" / "g1_scoring.py"
    spec = importlib.util.spec_from_file_location("g1_scoring", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# Distinct DOC ids + short extractable golds (≥10 cases).
CASES: list[dict] = [
    {"id": "code_a7", "doc": "DOC-A7", "fact": "Secret code: CODE-A7-441.", "q": "What is the secret code in DOC-A7? Reply with only the code.", "gold": "CODE-A7-441"},
    {"id": "city_b3", "doc": "DOC-B3", "fact": "Named city: Karachi.", "q": "Which city is named in DOC-B3? Reply with only the city name.", "gold": "Karachi"},
    {"id": "year_c9", "doc": "DOC-C9", "fact": "Stated year: 2019.", "q": "What year is stated in DOC-C9? Reply with only the year.", "gold": "2019"},
    {"id": "id_d2", "doc": "DOC-D2", "fact": "Document id token: DOC-D2.", "q": "What is the document id token in DOC-D2? Reply with only the id.", "gold": "DOC-D2"},
    {"id": "port_e1", "doc": "DOC-E1", "fact": "Harbor port code: PRT-188.", "q": "What is the harbor port code in DOC-E1? Reply with only the code.", "gold": "PRT-188"},
    {"id": "metal_f4", "doc": "DOC-F4", "fact": "Element name: Cobalt.", "q": "Which element is named in DOC-F4? Reply with only the element.", "gold": "Cobalt"},
    {"id": "color_g5", "doc": "DOC-G5", "fact": "Signal color: Amber.", "q": "What signal color is in DOC-G5? Reply with only the color.", "gold": "Amber"},
    {"id": "river_h6", "doc": "DOC-H6", "fact": "River name: Indus.", "q": "Which river is named in DOC-H6? Reply with only the river.", "gold": "Indus"},
    {"id": "id_i8", "doc": "DOC-I8", "fact": "Badge id: BADGE-908.", "q": "What is the badge id in DOC-I8? Reply with only the id.", "gold": "BADGE-908"},
    {"id": "planet_j0", "doc": "DOC-J0", "fact": "Planet name: Kepler.", "q": "Which planet is named in DOC-J0? Reply with only the name.", "gold": "Kepler"},
    {"id": "code_k1", "doc": "DOC-K1", "fact": "Vault code: VX-7731.", "q": "What is the vault code in DOC-K1? Reply with only the code.", "gold": "VX-7731"},
    {"id": "city_l2", "doc": "DOC-L2", "fact": "Named city: Lahore.", "q": "Which city is named in DOC-L2? Reply with only the city name.", "gold": "Lahore"},
]

ORDERS = {
    "abc": ("DOC-A7", "DOC-B3", "DOC-C9", "DOC-D2", "DOC-E1", "DOC-F4", "DOC-G5", "DOC-H6", "DOC-I8", "DOC-J0", "DOC-K1", "DOC-L2"),
    "bac": ("DOC-B3", "DOC-A7", "DOC-C9", "DOC-E1", "DOC-D2", "DOC-F4", "DOC-H6", "DOC-G5", "DOC-J0", "DOC-I8", "DOC-L2", "DOC-K1"),
    "cba": ("DOC-C9", "DOC-B3", "DOC-A7", "DOC-F4", "DOC-E1", "DOC-D2", "DOC-J0", "DOC-I8", "DOC-H6", "DOC-G5", "DOC-L2", "DOC-K1"),
}


def _doc_block(case: dict, filler: str) -> str:
    return f"### {case['doc']}\n{case['fact']}\n{filler}\n"


def build_corpus(*, filler_chars: int) -> dict[str, str]:
    filler = ("matched quality filler sentence. " * 80)[:filler_chars]
    return {c["doc"]: _doc_block(c, filler) for c in CASES}


def build_prompt(
    *,
    corpus: dict[str, str],
    order: tuple[str, ...],
    question: str,
) -> str:
    head = (
        "You are a careful assistant. Use only the documents. "
        "Prefer a short answer with only the requested value.\n\n"
    )
    body = "\n".join(corpus[d] for d in order if d in corpus)
    return head + body + "\n" + question


def _kv_transfer_config(host: str, port: int):
    from vllm.config import KVTransferConfig

    return KVTransferConfig(
        kv_connector="LMCacheMPConnector",
        kv_connector_module_path="lmcache.integration.vllm.lmcache_mp_connector",
        kv_role="kv_both",
        kv_connector_extra_config={
            "lmcache.mp.host": f"tcp://{host}",
            "lmcache.mp.port": port,
        },
    )


def main(argv: list[str] | None = None) -> int:
    scoring = _load_scoring()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default=os.environ.get("SMOKE_MODEL", "Qwen/Qwen3-8B"))
    parser.add_argument("--mode", choices=("native", "control", "blend"), required=True)
    parser.add_argument("--order", choices=tuple(ORDERS), default="abc")
    parser.add_argument("--max-model-len", type=int, default=8192)
    parser.add_argument("--max-tokens", type=int, default=32)
    parser.add_argument("--filler-chars", type=int, default=400)
    parser.add_argument("--gpu-memory-utilization", type=float, default=0.75)
    parser.add_argument("--control-json", type=Path, default=None, help="Prior control JSON for agree_with_control")
    parser.add_argument("--out", type=Path, default=None, help="Write clean JSON payload here")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if os.environ.get("CONTEXTWEAVE_ALLOW_MODEL_LOAD") != "1":
        print(
            "Refusing: set CONTEXTWEAVE_ALLOW_MODEL_LOAD=1 on the GPU host only.",
            file=sys.stderr,
        )
        return 1

    host = os.environ.get("LMCACHE_MP_HOST", "127.0.0.1")
    port = int(os.environ.get("LMCACHE_MP_PORT", "5555"))
    order = ORDERS[args.order]
    corpus = build_corpus(filler_chars=args.filler_chars)
    prompts = [
        build_prompt(corpus=corpus, order=order, question=c["q"]) for c in CASES
    ]

    from vllm import LLM, SamplingParams

    kwargs: dict = {
        "model": args.model,
        "max_model_len": args.max_model_len,
        "gpu_memory_utilization": args.gpu_memory_utilization,
        "trust_remote_code": True,
        "enforce_eager": True,
        "enable_prefix_caching": args.mode == "native",
    }
    if args.mode in ("control", "blend"):
        kwargs["enable_prefix_caching"] = False
        kwargs["kv_transfer_config"] = _kv_transfer_config(host, port)

    print(
        f"matched quality mode={args.mode} order={args.order} "
        f"n={len(CASES)} model={args.model}",
        flush=True,
    )
    llm = LLM(**kwargs)
    params = SamplingParams(temperature=0.0, max_tokens=args.max_tokens)

    times_ms: list[float] = []
    texts: list[str] = []
    for i, prompt in enumerate(prompts):
        print(f"  case {i + 1}/{len(prompts)} {CASES[i]['id']} …", flush=True)
        t0 = time.perf_counter()
        outs = llm.generate([prompt], params)
        dt = (time.perf_counter() - t0) * 1000.0
        times_ms.append(dt)
        texts.append(outs[0].outputs[0].text if outs and outs[0].outputs else "")
        print(f"  case {i + 1} {dt:.0f} ms", flush=True)
    del llm

    control_extracted: dict[str, str] = {}
    if args.control_json and args.control_json.exists():
        prior = json.loads(args.control_json.read_text())
        for c in prior.get("cases", []):
            control_extracted[c["id"]] = c.get("extracted", "")

    cases_out = []
    for i, case in enumerate(CASES):
        sc = scoring.score_output(texts[i], case["gold"])
        agree = None
        if case["id"] in control_extracted:
            agree = scoring.normalize(sc["extracted"]) == scoring.normalize(
                control_extracted[case["id"]]
            )
        cases_out.append(
            {
                "id": case["id"],
                "order": args.order,
                "gold": case["gold"],
                "raw": sc["raw"],
                "extracted": sc["extracted"],
                "contains": sc["contains"],
                "exact": sc["exact"],
                "garbage": sc["garbage"],
                "agrees_with_control": agree,
                "latency_ms": times_ms[i],
            }
        )

    n = len(cases_out)
    contains_rate = sum(c["contains"] for c in cases_out) / n
    garbage_rate = sum(c["garbage"] for c in cases_out) / n
    agree_vals = [c["agrees_with_control"] for c in cases_out if c["agrees_with_control"] is not None]
    agree_rate = (sum(agree_vals) / len(agree_vals)) if agree_vals else None

    gate_c = contains_rate >= 0.9 and garbage_rate <= 0.05
    gate_d = (
        agree_rate is not None
        and agree_rate >= 0.9
        and contains_rate >= 0.9
        and garbage_rate <= 0.05
    )
    payload = {
        "gate": f"G1-matched-quality-{args.mode}",
        "mode": args.mode,
        "order": args.order,
        "model": args.model,
        "lmcache_mp": {"host": host, "port": port} if args.mode != "native" else None,
        "n_cases": n,
        "cases": cases_out,
        "summary": {
            "contains_rate": contains_rate,
            "garbage_rate": garbage_rate,
            "agree_with_control_rate": agree_rate,
        },
        "gate_c_pass": gate_c if args.mode == "control" else None,
        "gate_d_pass": gate_d if args.mode == "blend" else None,
        "pass_heuristic": gate_d if args.mode == "blend" else gate_c if args.mode == "control" else contains_rate >= 0.9,
        "note": (
            "Gate C (control): contains≥0.9 garbage≈0. "
            "Gate D (blend): + agree_with_control≥0.9. Never cite latency if quality fails."
        ),
    }
    if args.out:
        args.out.write_text(json.dumps(payload, indent=2) + "\n")
        print(f"Wrote {args.out}", flush=True)
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(
            f"contains={contains_rate:.2f} garbage={garbage_rate:.2f} "
            f"agree={agree_rate} pass={payload['pass_heuristic']}"
        )
    return 0 if payload["pass_heuristic"] else 4


if __name__ == "__main__":
    sys.exit(main())
