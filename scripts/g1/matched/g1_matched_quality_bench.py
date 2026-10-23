#!/usr/bin/env python3
"""G1 matched-pin quality bench — control vs blend (GPU).

Uses CacheBlend chunk+separator ``prompt_token_ids`` (``" # # "``). Each case:
  reset → seed ABC once → measure the requested order + that case's question.
So cases 2..N are not exact prefix hits on case 1's body.

Modes:
  native  — no LMCache (sanity)
  control — LMCacheMPConnector, default engine
  blend   — in-process ``LMCacheConnectorV1`` + register_model (#4131)

  export CONTEXTWEAVE_ALLOW_MODEL_LOAD=1
  python scripts/g1/matched/g1_matched_quality_bench.py --mode control --json | tee g1_matched_control.json
  python scripts/g1/matched/g1_matched_quality_bench.py --mode blend --order bac \\
    --control-json g1_matched_control.json --json | tee g1_matched_blend_bac.json
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
import time
from pathlib import Path

_REPO_BOOT = Path(__file__).resolve()
for _cand in _REPO_BOOT.parents:
    if (_cand / "pyproject.toml").exists():
        ROOT = _cand
        break
else:
    raise SystemExit("Could not find repo root (pyproject.toml)")
SRC = ROOT / "src"
G1_COMMON = ROOT / "scripts" / "g1" / "common"
G1_EPIC = ROOT / "scripts" / "g1" / "epic"
G1_CACHEBLEND = ROOT / "scripts" / "g1" / "cacheblend"
for _p in (SRC, G1_COMMON):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

DEFAULT_BLEND_SPECIAL = " # # "
CHUNK_BLOCK = 256
BLEND_PATH = "inprocess"


def _load_scoring():
    path = G1_COMMON / "g1_scoring.py"
    spec = importlib.util.spec_from_file_location("g1_scoring", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# Distinct DOC ids + extractable golds. Multi-hop cases need ≥2 docs.
CASES: list[dict] = [
    {"id": "code_a7", "doc": "DOC-A7", "fact": "Secret code: CODE-A7-441.", "q": "What is the secret code in DOC-A7? Reply with only the code.", "gold": "CODE-A7-441", "hop": 1},
    {"id": "city_b3", "doc": "DOC-B3", "fact": "Named city: Karachi.", "q": "Which city is named in DOC-B3? Reply with only the city name.", "gold": "Karachi", "hop": 1},
    {"id": "year_c9", "doc": "DOC-C9", "fact": "Stated year: 2019.", "q": "What year is stated in DOC-C9? Reply with only the year.", "gold": "2019", "hop": 1},
    {"id": "id_d2", "doc": "DOC-D2", "fact": "Document id token: DOC-D2.", "q": "What is the document id token in DOC-D2? Reply with only the id.", "gold": "DOC-D2", "hop": 1},
    {"id": "port_e1", "doc": "DOC-E1", "fact": "Harbor port code: PRT-188.", "q": "What is the harbor port code in DOC-E1? Reply with only the code.", "gold": "PRT-188", "hop": 1},
    {"id": "metal_f4", "doc": "DOC-F4", "fact": "Element name: Cobalt.", "q": "Which element is named in DOC-F4? Reply with only the element.", "gold": "Cobalt", "hop": 1},
    {"id": "color_g5", "doc": "DOC-G5", "fact": "Signal color: Amber.", "q": "What signal color is in DOC-G5? Reply with only the color.", "gold": "Amber", "hop": 1},
    {"id": "river_h6", "doc": "DOC-H6", "fact": "River name: Indus.", "q": "Which river is named in DOC-H6? Reply with only the river.", "gold": "Indus", "hop": 1},
    {"id": "id_i8", "doc": "DOC-I8", "fact": "Badge id: BADGE-908.", "q": "What is the badge id in DOC-I8? Reply with only the id.", "gold": "BADGE-908", "hop": 1},
    {"id": "planet_j0", "doc": "DOC-J0", "fact": "Planet name: Kepler.", "q": "Which planet is named in DOC-J0? Reply with only the name.", "gold": "Kepler", "hop": 1},
    {
        "id": "hop_city_year",
        "doc": "DOC-B3",
        "fact": "",
        "q": (
            "Using DOC-B3 and DOC-C9 only: reply with the city then the year "
            "as CITY-YEAR (example Karachi-2019)."
        ),
        "gold": "Karachi-2019",
        "hop": 2,
    },
    {
        "id": "hop_code_port",
        "doc": "DOC-A7",
        "fact": "",
        "q": (
            "Using DOC-A7 and DOC-E1 only: reply with the secret code then the "
            "port code as CODE/PORT."
        ),
        "gold": "CODE-A7-441/PRT-188",
        "hop": 2,
    },
]

DOC_ORDER_KEYS = (
    "DOC-A7",
    "DOC-B3",
    "DOC-C9",
    "DOC-D2",
    "DOC-E1",
    "DOC-F4",
    "DOC-G5",
    "DOC-H6",
    "DOC-I8",
    "DOC-J0",
    "DOC-K1",
    "DOC-L2",
)

# Extra docs so ABC corpus stays 12 chunks even with hop-only cases.
EXTRA_DOCS = {
    "DOC-K1": "Vault code: VX-7731.",
    "DOC-L2": "Named city: Lahore.",
}

ORDERS = {
    "abc": DOC_ORDER_KEYS,
    "bac": (
        "DOC-B3",
        "DOC-A7",
        "DOC-C9",
        "DOC-E1",
        "DOC-D2",
        "DOC-F4",
        "DOC-H6",
        "DOC-G5",
        "DOC-J0",
        "DOC-I8",
        "DOC-L2",
        "DOC-K1",
    ),
    "cba": (
        "DOC-C9",
        "DOC-B3",
        "DOC-A7",
        "DOC-F4",
        "DOC-E1",
        "DOC-D2",
        "DOC-J0",
        "DOC-I8",
        "DOC-H6",
        "DOC-G5",
        "DOC-L2",
        "DOC-K1",
    ),
}


def _prepare_blend_worker(*, blend_special_str: str) -> None:
    from g1_blend_hooks import prepare_blend_worker

    prepare_blend_worker(blend_special_str=blend_special_str)


def _setup_blend_client_env(*, blend_special_str: str) -> None:
    """Backward-compatible alias → ``_prepare_blend_worker``."""
    _prepare_blend_worker(blend_special_str=blend_special_str)


def _align_chunk_tokens(n: int, block: int = CHUNK_BLOCK) -> int:
    return max(block, (n // block) * block)


def _fill_doc_chunk(tokenizer, doc_id: str, fact: str, target_tokens: int) -> list[int]:
    line = f"{doc_id}. {fact} quality-filler for matched Gate C/D. "
    ids: list[int] = []
    piece = tokenizer.encode(line, add_special_tokens=False)
    while len(ids) < target_tokens:
        ids.extend(piece)
    return ids[:target_tokens]


def _sep_ids(tokenizer, blend_special_str: str) -> list[int]:
    sep = tokenizer.encode(blend_special_str, add_special_tokens=False)
    if sep and getattr(tokenizer, "bos_token_id", None) is not None:
        if sep[0] == tokenizer.bos_token_id and len(sep) > 1:
            sep = sep[1:]
    return sep


def _join(
    *,
    system: list[int],
    chunks: list[list[int]],
    question_ids: list[int],
    sep: list[int],
) -> list[int]:
    out = list(system)
    for ch in chunks:
        out.extend(sep)
        out.extend(ch)
    out.extend(sep)
    out.extend(question_ids)
    return out


def _reset_prefix_cache(llm) -> None:
    fn = getattr(llm, "reset_prefix_cache", None)
    if callable(fn):
        try:
            fn()
            return
        except TypeError:
            try:
                fn(reset_running_requests=True)
            except Exception:  # noqa: BLE001
                pass
        except Exception:  # noqa: BLE001
            pass


def _kv_transfer_config(host: str, port: int):
    import importlib.util

    from vllm.config import KVTransferConfig

    # heartbeat_interval also caps PING wait; 10s falsely marks busy blend servers
    # unhealthy → KV load failure_policy=fail (empty 6ms cases).
    # lmcache 0.4.x has no lmcache_mp_connector — omit path so vLLM uses built-in.
    extra = {
        "lmcache.mp.host": f"tcp://{host}",
        "lmcache.mp.port": port,
        "lmcache.mp.mq_timeout": float(os.environ.get("LMCACHE_MP_MQ_TIMEOUT", "300")),
        "lmcache.mp.heartbeat_interval": float(
            os.environ.get("LMCACHE_MP_HEARTBEAT_INTERVAL", "60")
        ),
        "lmcache.mp.mp_transfer_mode": os.environ.get(
            "LMCACHE_MP_TRANSFER_MODE", "lmcache_driven"
        ),
    }
    kwargs: dict = {
        "kv_connector": "LMCacheMPConnector",
        "kv_role": "kv_both",
        "kv_connector_extra_config": extra,
    }
    mp_mod = "lmcache.integration.vllm.lmcache_mp_connector"
    if importlib.util.find_spec(mp_mod) is not None:
        kwargs["kv_connector_module_path"] = mp_mod
    return KVTransferConfig(**kwargs)


def main(argv: list[str] | None = None) -> int:
    scoring = _load_scoring()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default=os.environ.get("SMOKE_MODEL", "Qwen/Qwen3-8B"))
    parser.add_argument("--mode", choices=("native", "control", "blend"), required=True)
    parser.add_argument("--order", choices=tuple(ORDERS), default="abc")
    parser.add_argument("--max-model-len", type=int, default=8192)
    parser.add_argument("--max-tokens", type=int, default=96)
    parser.add_argument(
        "--chunk-tokens",
        type=int,
        default=512,
        help="Tokens per doc chunk (rounded down to multiple of 256).",
    )
    parser.add_argument("--blend-special-str", default=DEFAULT_BLEND_SPECIAL)
    parser.add_argument("--gpu-memory-utilization", type=float, default=0.75)
    parser.add_argument("--control-json", type=Path, default=None)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if os.environ.get("CONTEXTWEAVE_ALLOW_MODEL_LOAD") != "1":
        print(
            "Refusing: set CONTEXTWEAVE_ALLOW_MODEL_LOAD=1 on the GPU host only.",
            file=sys.stderr,
        )
        return 1

    if args.mode == "blend":
        _prepare_blend_worker(blend_special_str=args.blend_special_str)

    host = os.environ.get("LMCACHE_MP_HOST", "127.0.0.1")
    port = int(os.environ.get("LMCACHE_MP_PORT", "5555"))
    order = ORDERS[args.order]

    from transformers import AutoTokenizer
    from vllm import LLM, SamplingParams

    tokenizer = AutoTokenizer.from_pretrained(args.model, trust_remote_code=True)
    sep = _sep_ids(tokenizer, args.blend_special_str)
    system = tokenizer.encode(
        "You are a careful assistant. Use only the documents below. "
        "Reply with ONLY the requested value on the first line. /no_think",
        add_special_tokens=True,
    )
    chunk_tokens = _align_chunk_tokens(args.chunk_tokens)

    fact_by_doc = {c["doc"]: c["fact"] for c in CASES if c.get("fact")}
    fact_by_doc.update(EXTRA_DOCS)
    chunk_map = {
        doc_id: _fill_doc_chunk(
            tokenizer, doc_id, fact_by_doc.get(doc_id, f"{doc_id}."), chunk_tokens
        )
        for doc_id in DOC_ORDER_KEYS
    }

    seed_q = tokenizer.encode(
        "Acknowledge documents only. Reply with OK.\n/no_think",
        add_special_tokens=False,
    )
    seed_abc = _join(
        system=system,
        chunks=[chunk_map[d] for d in ORDERS["abc"]],
        question_ids=seed_q,
        sep=sep,
    )

    kwargs: dict = {
        "model": args.model,
        "max_model_len": args.max_model_len,
        "gpu_memory_utilization": args.gpu_memory_utilization,
        "trust_remote_code": True,
        "enforce_eager": True,
        "enable_prefix_caching": args.mode == "native",
    }
    if args.mode == "control":
        kwargs["enable_prefix_caching"] = False
        kwargs["kv_transfer_config"] = _kv_transfer_config(host, port)
    elif args.mode == "blend":
        from g1_blend_hooks import blend_kv_transfer_config

        kwargs["enable_prefix_caching"] = False
        kwargs["kv_transfer_config"] = blend_kv_transfer_config()

    print(
        f"matched quality mode={args.mode} blend_path={BLEND_PATH if args.mode == 'blend' else 'n/a'} "
        f"order={args.order} n={len(CASES)} chunk_tokens={chunk_tokens} format=chunk_sep",
        flush=True,
    )
    llm = LLM(**kwargs)
    sp_kwargs: dict = {"temperature": 0.0, "max_tokens": args.max_tokens}
    try:
        params = SamplingParams(**sp_kwargs, extra_args={"enable_thinking": False})
    except TypeError:
        params = SamplingParams(**sp_kwargs)

    times_ms: list[float] = []
    texts: list[str] = []
    for i, case in enumerate(CASES):
        print(f"  case {i + 1}/{len(CASES)} {case['id']} hop={case.get('hop', 1)} …", flush=True)
        _reset_prefix_cache(llm)
        # Seed ABC (discard) so reorder is a true non-prefix probe, not a bac self-hit.
        llm.generate(
            prompts={"prompt_token_ids": seed_abc},
            sampling_params=SamplingParams(temperature=0.0, max_tokens=1),
            use_tqdm=False,
        )
        q_ids = tokenizer.encode(case["q"] + "\n/no_think", add_special_tokens=False)
        prompt_ids = _join(
            system=system,
            chunks=[chunk_map[d] for d in order],
            question_ids=q_ids,
            sep=sep,
        )
        if len(prompt_ids) + args.max_tokens > args.max_model_len:
            print(f"prompt too long for case {case['id']}", file=sys.stderr)
            return 3
        t0 = time.perf_counter()
        outs = llm.generate(
            prompts={"prompt_token_ids": prompt_ids},
            sampling_params=params,
            use_tqdm=False,
        )
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
                "hop": case.get("hop", 1),
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
    agree_vals = [
        c["agrees_with_control"] for c in cases_out if c["agrees_with_control"] is not None
    ]
    agree_rate = (sum(agree_vals) / len(agree_vals)) if agree_vals else None

    gate_c = contains_rate >= 0.9 and garbage_rate <= 0.05
    gate_d = (
        agree_rate is not None
        and agree_rate >= 0.9
        and contains_rate >= 0.9
        and garbage_rate <= 0.05
    )
    # Blend without control-json (e.g. abc seed pass): quality bars only, not Gate D.
    if args.mode == "blend":
        pass_h = gate_d if agree_rate is not None else gate_c
    elif args.mode == "control":
        pass_h = gate_c
    else:
        pass_h = contains_rate >= 0.9

    payload = {
        "gate": f"G1-matched-quality-{args.mode}",
        "mode": args.mode,
        "order": args.order,
        "model": args.model,
        "prompt_format": "chunk_sep",
        "blend_path": BLEND_PATH if args.mode == "blend" else None,
        "blend_special_str": args.blend_special_str,
        "chunk_tokens": chunk_tokens,
        "protocol": "per_case: reset → seed_abc → measure order+question",
        "lmcache_mp": {"host": host, "port": port} if args.mode == "control" else None,
        "blend_client_env": args.mode == "blend",
        "n_cases": n,
        "cases": cases_out,
        "summary": {
            "contains_rate": contains_rate,
            "garbage_rate": garbage_rate,
            "agree_with_control_rate": agree_rate,
        },
        "gate_c_pass": gate_c if args.mode == "control" else None,
        "gate_d_pass": gate_d if args.mode == "blend" else None,
        "pass_heuristic": pass_h,
        "note": (
            "Gate C (control): contains≥0.9 garbage≤0.05. "
            "Gate D (blend): inprocess LMCacheConnectorV1 + register_model; "
            "+ agree_with_control≥0.9 when --control-json set. "
            "chunk_sep + per-case ABC seed required for real blend/reorder probe."
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
    code = 0 if payload["pass_heuristic"] else 4
    # vLLM/LMCache CUDA IPC teardown often hangs after the last generate; results
    # are already on disk — hard-exit so the shell can start the next order.
    try:
        del llm
    except Exception:  # noqa: BLE001
        pass
    print("exiting (hard) to avoid CUDA teardown hang", flush=True)
    os._exit(code)


if __name__ == "__main__":
    sys.exit(main())
