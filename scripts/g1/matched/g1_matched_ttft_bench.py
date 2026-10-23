#!/usr/bin/env python3
"""G1 matched-pin TTFT bench (GPU) — CacheBlend chunk+separator format.

Both backends use the same token-id prompts: fixed chunks joined by
``blend_special_str`` (``" # # "``), matching ``g1_cacheblend_mp_bench.py``.
Markdown-concat prompts do not preserve LMCache chunk ids under reorder.

Native prefix protocol:
  1. Seed ABC once (discarded)
  2. Measure warm_abc × N  (exact repeat → prefix hit)
  3. Each reorder trial: reset_prefix_cache → seed ABC → measure BAC/CBA
  4. Cold ABC × N (unique leading nonce tokens)

Blend: same, plus unique chunk-body salt per reorder trial so LMCache cannot
BAC/CBA self-hit when ``reset_prefix_cache`` fails.

  export CONTEXTWEAVE_ALLOW_MODEL_LOAD=1
  python scripts/g1/matched/g1_matched_ttft_bench.py --backend native_prefix --runs 10 \\
    --max-model-len 16384 --target-prefix-tokens 12000 --out g1_ttft_native_12k_chunks.json
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
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

ORDERS = {
    "abc": ("A", "B", "C"),
    "bac": ("B", "A", "C"),
    "cba": ("C", "B", "A"),
}

CHUNK_FACTS = {
    "A": "Document Alpha. Secret code: ALPHA-9173.",
    "B": "Document Beta. Named city: Karachi.",
    "C": "Document Gamma. Stated year: 2019.",
}

DEFAULT_BLEND_SPECIAL = " # # "
# G1-DIAG re-run: in-process connector + register_model (not MP-only).
BLEND_PATH = "inprocess"
QUESTION = (
    "Which city is named in Document Beta? Reply with only the city name.\n/no_think"
)
SYSTEM_TEXT = (
    "You are a careful assistant. Prefer a short answer. "
    "Reply with only the requested value."
)


def _fill_chunk(
    tokenizer,
    key: str,
    target_tokens: int,
    *,
    salt: str = "",
) -> list[int]:
    """Fixed-length token chunk; ``salt`` changes LMCache ids across trials."""
    fact = CHUNK_FACTS[key]
    name = {"A": "Alpha", "B": "Beta", "C": "Gamma"}[key]
    line = f"{salt}{fact} Document {name} token-fill for matched TTFT. "
    ids: list[int] = []
    piece = tokenizer.encode(line, add_special_tokens=False)
    if not piece:
        raise SystemExit(f"empty encode for chunk {key}")
    while len(ids) < target_tokens:
        ids.extend(piece)
    return ids[:target_tokens]


def _sep_ids(tokenizer, blend_special_str: str) -> list[int]:
    sep = tokenizer.encode(blend_special_str, add_special_tokens=False)
    if sep and getattr(tokenizer, "bos_token_id", None) is not None:
        if sep[0] == tokenizer.bos_token_id and len(sep) > 1:
            sep = sep[1:]
    return sep


def _join_chunks(
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


def _prompt_for_order(
    order: tuple[str, ...],
    *,
    chunk_map: dict[str, list[int]],
    system: list[int],
    question_ids: list[int],
    sep: list[int],
) -> list[int]:
    return _join_chunks(
        system=system,
        chunks=[chunk_map[k] for k in order],
        question_ids=question_ids,
        sep=sep,
    )


def _align_down(n: int, block: int = 256) -> int:
    return max(block, (n // block) * block)


def _chunk_tokens_for_target(
    *,
    target_prefix_tokens: int,
    max_model_len: int,
    max_tokens: int,
    system_len: int,
    question_len: int,
    sep_len: int,
) -> int:
    """Per-chunk size so ABC ≈ target; each chunk length is a multiple of 256."""
    overhead = system_len + question_len + 4 * sep_len + 8
    prefix_cap = max_model_len - max_tokens - 8
    want = min(target_prefix_tokens, prefix_cap)
    usable = want - overhead
    if usable < 3 * 256:
        raise SystemExit(
            f"target/max_model_len too small for 3 chunks "
            f"(want={want}, overhead={overhead})"
        )
    return _align_down(usable // 3, 256)


def _prepare_blend_worker(*, blend_special_str: str) -> None:
    """In-process LMCBlender: env + VLLMModelTracker.register_model (#4131)."""
    from g1_blend_hooks import prepare_blend_worker

    prepare_blend_worker(blend_special_str=blend_special_str)


def _setup_blend_client_env(*, blend_special_str: str) -> None:
    """Backward-compatible alias → ``_prepare_blend_worker``."""
    _prepare_blend_worker(blend_special_str=blend_special_str)


def _cv(samples: list[float]) -> float | None:
    if len(samples) < 2:
        return None
    mu = statistics.mean(samples)
    if mu <= 0:
        return None
    return statistics.stdev(samples) / mu


def _reorder_series_polluted(samples: list[float]) -> bool:
    """True when trial-1 looks like a miss but p50 collapsed to later self-hits."""
    if len(samples) < 3:
        return False
    first = samples[0]
    rest_p50 = statistics.median(samples[1:])
    return first >= 1.15 * rest_p50


def _percentile(xs: list[float], p: float) -> float:
    if not xs:
        return float("nan")
    ys = sorted(xs)
    if len(ys) == 1:
        return ys[0]
    k = (len(ys) - 1) * p
    f = int(k)
    c = min(f + 1, len(ys) - 1)
    if f == c:
        return ys[f]
    return ys[f] + (ys[c] - ys[f]) * (k - f)


def _ttft_ms(llm, prompt_ids: list[int], sampling) -> tuple[float, str, str, dict]:
    """Wall-clock generate on prompt_token_ids (CacheBlend MP style)."""
    # Local import keeps laptop imports of this module free of path hacks in tests.
    from g1_engagement import extract_engagement

    t0 = time.perf_counter()
    outs = llm.generate(
        prompts={"prompt_token_ids": prompt_ids},
        sampling_params=sampling,
        use_tqdm=False,
    )
    wall = (time.perf_counter() - t0) * 1000.0
    text = outs[0].outputs[0].text.strip() if outs and outs[0].outputs else ""
    eng = extract_engagement(outs)
    return wall, text, "wall_clock_generate_token_ids", eng


def _reset_prefix_cache(llm) -> bool:
    """Clear automatic prefix cache so the next reorder is a real miss."""
    fn = getattr(llm, "reset_prefix_cache", None)
    if callable(fn):
        try:
            fn()
            return True
        except TypeError:
            try:
                fn(reset_running_requests=True)
                return True
            except Exception:  # noqa: BLE001
                pass
        except Exception:  # noqa: BLE001
            pass
    engine = getattr(llm, "llm_engine", None)
    if engine is not None:
        fn2 = getattr(engine, "reset_prefix_cache", None)
        if callable(fn2):
            try:
                fn2()
                return True
            except Exception:  # noqa: BLE001
                pass
    return False


def _measure(llm, prompt_ids: list[int], sampling, *, n: int, label: str) -> tuple[dict, str]:
    samples: list[float] = []
    engagement_trials: list[dict] = []
    last_text = ""
    method = "unknown"
    for i in range(n):
        ms, text, method, eng = _ttft_ms(llm, prompt_ids, sampling)
        samples.append(ms)
        engagement_trials.append(eng)
        last_text = text
        cached = eng.get("num_cached_tokens")
        extra = f" cached={cached}" if cached is not None else ""
        print(f"  {label} {i + 1}/{n} {ms:.0f} ms{extra}", flush=True)
    from g1_engagement import summarize_trial_engagement

    return {
        "n": len(samples),
        "p50_ms": statistics.median(samples),
        "p90_ms": _percentile(samples, 0.9),
        "cv": _cv(samples),
        "samples_ms": samples,
        "last_output": last_text,
        "engagement": summarize_trial_engagement(engagement_trials),
    }, method


def _measure_reorder_after_abc(
    llm,
    *,
    abc_ids: list[int],
    reorder_ids: list[int],
    sampling,
    n: int,
    label: str,
    prompt_pair_fn=None,
) -> tuple[dict, str, bool]:
    """Each trial: clear cache → seed ABC → measure reorder once."""
    samples: list[float] = []
    engagement_trials: list[dict] = []
    last_text = ""
    method = "unknown"
    cleared = True
    for i in range(n):
        if prompt_pair_fn is not None:
            abc_i, reorder_i = prompt_pair_fn(i)
        else:
            abc_i, reorder_i = abc_ids, reorder_ids
        if not _reset_prefix_cache(llm):
            cleared = False
        _ttft_ms(llm, abc_i, sampling)
        ms, text, method, eng = _ttft_ms(llm, reorder_i, sampling)
        samples.append(ms)
        engagement_trials.append(eng)
        last_text = text
        cached = eng.get("num_cached_tokens")
        extra = f" cached={cached}" if cached is not None else ""
        print(f"  {label} {i + 1}/{n} {ms:.0f} ms{extra}", flush=True)
    polluted = _reorder_series_polluted(samples)
    if polluted:
        print(
            f"  WARN {label}: first={samples[0]:.0f} ms vs later p50="
            f"{statistics.median(samples[1:]):.0f} ms — self-hit pollution",
            flush=True,
        )
    from g1_engagement import summarize_trial_engagement

    return (
        {
            "n": len(samples),
            "p50_ms": statistics.median(samples),
            "p90_ms": _percentile(samples, 0.9),
            "cv": _cv(samples),
            "first_ms": samples[0] if samples else float("nan"),
            "samples_ms": samples,
            "series_polluted": polluted,
            "last_output": last_text,
            "engagement": summarize_trial_engagement(engagement_trials),
        },
        method,
        cleared and not polluted,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default=os.environ.get("SMOKE_MODEL", "Qwen/Qwen3-8B"))
    parser.add_argument("--backend", choices=("native_prefix", "blend"), required=True)
    parser.add_argument("--runs", type=int, default=10)
    parser.add_argument("--max-model-len", type=int, default=8192)
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=1,
        help="TTFT: use 1 (wall-clock ≈ first token). Avoid decode contamination.",
    )
    parser.add_argument(
        "--target-prefix-tokens",
        type=int,
        default=6000,
        help="Approximate ABC prompt tokens (3 equal chunks + separators).",
    )
    parser.add_argument(
        "--chunk-tokens",
        type=int,
        default=None,
        help="If set, fixed tokens per chunk (skip auto-size from target).",
    )
    parser.add_argument(
        "--blend-special-str",
        default=DEFAULT_BLEND_SPECIAL,
        help="CacheBlend separator between chunks (must match LMCache docs).",
    )
    parser.add_argument("--gpu-memory-utilization", type=float, default=0.75)
    parser.add_argument(
        "--enforce-eager",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Applied to BOTH backends so Gate E is apples-to-apples (default True).",
    )
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if os.environ.get("CONTEXTWEAVE_ALLOW_MODEL_LOAD") != "1":
        print(
            "Refusing: set CONTEXTWEAVE_ALLOW_MODEL_LOAD=1 on the GPU host only.",
            file=sys.stderr,
        )
        return 1

    if args.backend == "blend":
        _prepare_blend_worker(blend_special_str=args.blend_special_str)

    from transformers import AutoTokenizer
    from vllm import LLM, SamplingParams

    tokenizer = AutoTokenizer.from_pretrained(args.model, trust_remote_code=True)
    sep = _sep_ids(tokenizer, args.blend_special_str)
    system = tokenizer.encode(SYSTEM_TEXT, add_special_tokens=True)
    question_ids = tokenizer.encode(QUESTION, add_special_tokens=False)

    if args.chunk_tokens is not None:
        chunk_tokens = _align_down(args.chunk_tokens, 256)
    else:
        chunk_tokens = _chunk_tokens_for_target(
            target_prefix_tokens=args.target_prefix_tokens,
            max_model_len=args.max_model_len,
            max_tokens=args.max_tokens,
            system_len=len(system),
            question_len=len(question_ids),
            sep_len=len(sep),
        )
    if chunk_tokens % 256 != 0:
        raise SystemExit(f"chunk_tokens={chunk_tokens} must be a multiple of 256")

    chunk_map = {
        k: _fill_chunk(tokenizer, k, chunk_tokens) for k in ("A", "B", "C")
    }
    prompts = {
        key: _prompt_for_order(
            order,
            chunk_map=chunk_map,
            system=system,
            question_ids=question_ids,
            sep=sep,
        )
        for key, order in ORDERS.items()
    }
    prompt_tokens = len(prompts["abc"])
    print(
        f"  chunk_tokens={chunk_tokens} ABC_len={prompt_tokens} "
        f"sep_len={len(sep)} format=chunk_sep",
        flush=True,
    )
    if prompt_tokens + args.max_tokens > args.max_model_len:
        print(
            f"ABC prompt too long ({prompt_tokens}) for max_model_len="
            f"{args.max_model_len}",
            file=sys.stderr,
        )
        return 3

    def _blend_prompt_pair(order_key: str):
        def _fn(i: int) -> tuple[list[int], list[int]]:
            salt = f"t{i}-{order_key}-"
            cmap = {
                k: _fill_chunk(tokenizer, k, chunk_tokens, salt=salt)
                for k in ("A", "B", "C")
            }
            abc = _prompt_for_order(
                ORDERS["abc"],
                chunk_map=cmap,
                system=system,
                question_ids=question_ids,
                sep=sep,
            )
            reo = _prompt_for_order(
                ORDERS[order_key],
                chunk_map=cmap,
                system=system,
                question_ids=question_ids,
                sep=sep,
            )
            return abc, reo

        return _fn

    kwargs: dict = {
        "model": args.model,
        "max_model_len": args.max_model_len,
        "gpu_memory_utilization": args.gpu_memory_utilization,
        "trust_remote_code": True,
        # Same eager setting on both arms (CRIT-3 asymmetry fix).
        "enforce_eager": bool(args.enforce_eager),
    }
    enforce_eager_used = bool(args.enforce_eager)
    if args.backend == "native_prefix":
        kwargs["enable_prefix_caching"] = True
    else:
        from g1_blend_hooks import blend_kv_transfer_config

        kwargs["enable_prefix_caching"] = False
        kwargs["kv_transfer_config"] = blend_kv_transfer_config()

    print(
        f"matched TTFT backend={args.backend} blend_path={BLEND_PATH} "
        f"runs={args.runs} target_tokens={args.target_prefix_tokens} "
        f"chunk_tokens={chunk_tokens}",
        flush=True,
    )
    llm = LLM(**kwargs)
    sampling = SamplingParams(temperature=0.0, max_tokens=args.max_tokens)

    print("  [seed abc] discarded", flush=True)
    _ttft_ms(llm, prompts["abc"], sampling)

    results: dict[str, dict] = {}
    ttft_method = "wall_clock_generate_token_ids"

    warm_abc, ttft_method = _measure(
        llm, prompts["abc"], sampling, n=args.runs, label="warm_abc"
    )
    results["warm_abc"] = warm_abc

    blend_pairs = args.backend == "blend"
    warm_bac, ttft_method, cleared_bac = _measure_reorder_after_abc(
        llm,
        abc_ids=prompts["abc"],
        reorder_ids=prompts["bac"],
        sampling=sampling,
        n=args.runs,
        label="warm_bac",
        prompt_pair_fn=_blend_prompt_pair("bac") if blend_pairs else None,
    )
    results["warm_bac"] = warm_bac

    warm_cba, ttft_method, cleared_cba = _measure_reorder_after_abc(
        llm,
        abc_ids=prompts["abc"],
        reorder_ids=prompts["cba"],
        sampling=sampling,
        n=args.runs,
        label="warm_cba",
        prompt_pair_fn=_blend_prompt_pair("cba") if blend_pairs else None,
    )
    results["warm_cba"] = warm_cba
    reorder_polluted = bool(
        results["warm_bac"].get("series_polluted")
        or results["warm_cba"].get("series_polluted")
    )
    prefix_cache_reset_ok = cleared_bac and cleared_cba and not reorder_polluted
    if not prefix_cache_reset_ok:
        print(
            "WARN: reorder series may be polluted "
            "(reset failed and/or first≫later p50 self-hits)",
            flush=True,
        )

    cold_samples: list[float] = []
    cold_text = ""
    for i in range(args.runs):
        _reset_prefix_cache(llm)
        # Insert nonce *after* BOS so we do not duplicate BOS / change layout.
        nonce = tokenizer.encode(
            f"[cold-nonce-{i}-{time.time_ns()}]",
            add_special_tokens=False,
        )
        # Keep total length == warm ABC: shrink chunk A by len(nonce).
        shrink = len(nonce)
        if shrink >= chunk_tokens:
            nonce = nonce[: max(1, chunk_tokens // 8)]
            shrink = len(nonce)
        cold_map = {
            "A": chunk_map["A"][shrink:],
            "B": chunk_map["B"],
            "C": chunk_map["C"],
        }
        cold_system = system[:1] + nonce + system[1:] if system else nonce
        cold_ids = _prompt_for_order(
            ORDERS["abc"],
            chunk_map=cold_map,
            system=cold_system,
            question_ids=question_ids,
            sep=sep,
        )
        # Pad/truncate to exact warm length for fair cold vs warm.
        target_len = len(prompts["abc"])
        if len(cold_ids) > target_len:
            cold_ids = cold_ids[:target_len]
        elif len(cold_ids) < target_len:
            cold_ids = cold_ids + [question_ids[-1] if question_ids else 0] * (
                target_len - len(cold_ids)
            )
        ms, text, ttft_method, _eng = _ttft_ms(llm, cold_ids, sampling)
        cold_samples.append(ms)
        cold_text = text
        print(f"  cold_abc {i + 1}/{args.runs} {ms:.0f} ms", flush=True)
    results["cold_abc"] = {
        "n": len(cold_samples),
        "p50_ms": statistics.median(cold_samples),
        "p90_ms": _percentile(cold_samples, 0.9),
        "cv": _cv(cold_samples),
        "samples_ms": cold_samples,
        "last_output": cold_text,
    }

    del llm

    warm_abc_p50 = results["warm_abc"]["p50_ms"]
    warm_reorder_p50 = statistics.median(
        [results["warm_bac"]["p50_ms"], results["warm_cba"]["p50_ms"]]
    )
    reorder_gap = warm_reorder_p50 / warm_abc_p50 if warm_abc_p50 > 0 else None
    cold_vs_warm = (
        results["cold_abc"]["p50_ms"] / warm_abc_p50 if warm_abc_p50 > 0 else None
    )
    harness_reorder_gap_ok = reorder_gap is not None and reorder_gap >= 1.15

    # Gate R: reuse proven on blend reorder (fail closed if metric missing).
    gate_r_payload = None
    if args.backend == "blend":
        from g1_engagement import gate_r

        chunk_token_total = 3 * chunk_tokens
        eng_sum = results["warm_bac"].get("engagement") or {}
        got = eng_sum.get("cached_tokens_p50")
        gate_r_payload = gate_r(
            cached_or_retrieved_tokens=got,
            chunk_token_total=chunk_token_total,
            ttft_ms=warm_reorder_p50,
            native_reorder_p50_ms=None,  # filled by chunk_e.sh vs native JSON
            require_ttft_win=False,
        )
        print(
            f"GATE_R: {gate_r_payload['status']} "
            f"got={gate_r_payload['got_tokens']} need>={gate_r_payload['need_tokens']}",
            flush=True,
        )

    payload = {
        "gate": "G1-matched-ttft",
        "backend": args.backend,
        "model": args.model,
        "runs": args.runs,
        "prompt_format": "chunk_sep",
        "blend_path": BLEND_PATH if args.backend == "blend" else None,
        "blend_special_str": args.blend_special_str,
        "chunk_tokens": chunk_tokens,
        "chunk_tokens_aligned_256": chunk_tokens % 256 == 0,
        "chunk_token_total": 3 * chunk_tokens,
        "target_prefix_tokens": args.target_prefix_tokens,
        "abc_prompt_tokens": prompt_tokens,
        "ttft_method": ttft_method,
        "max_tokens": args.max_tokens,
        "enforce_eager": enforce_eager_used,
        "blend_client_env": args.backend == "blend",
        "warm_abc_cv": results["warm_abc"].get("cv"),
        "warm_reorder_cv": _cv(
            results["warm_bac"]["samples_ms"] + results["warm_cba"]["samples_ms"]
        ),
        "protocol": (
            "chunk_sep prompts → seed_abc → warm_abc×N → "
            "for reorder: reset_prefix_cache → seed abc → measure bac/cba ×N "
            "(blend: unique chunk salt per trial) → "
            "cold_abc×N (reset + leading nonce tokens)"
        ),
        "prefix_cache_reset_ok": prefix_cache_reset_ok,
        "reorder_series_polluted": reorder_polluted,
        "scenarios": results,
        "warm_abc_p50_ms": warm_abc_p50,
        "warm_reorder_p50_ms": warm_reorder_p50,
        "warm_reorder_first_ms": statistics.median(
            [
                results["warm_bac"].get("first_ms", float("nan")),
                results["warm_cba"].get("first_ms", float("nan")),
            ]
        ),
        "reorder_vs_warm_abc": reorder_gap,
        "cold_vs_warm_abc": cold_vs_warm,
        "harness_reorder_gap_ok": harness_reorder_gap_ok and prefix_cache_reset_ok,
        "gate_r": gate_r_payload,
        "note": (
            "blend_path=inprocess (LMCacheConnectorV1 + register_model). "
            "prompt_format=chunk_sep required for CacheBlend chunk-id reuse. "
            "harness_reorder_gap_ok requires reorder ≥1.15× warm ABC and no "
            "self-hit pollution. "
            "Gate R (blend): cached/retrieved ≥0.7× chunk_token_total on reorder; "
            "if ENGAGEMENT_FAIL/UNKNOWN do not interpret Gate D/E. "
            "Gate E: blend warm_reorder ≤ 0.85 × native warm_reorder. "
            "Do not cite gate_e if reorder_series_polluted."
        ),
    }
    if args.out:
        args.out.write_text(json.dumps(payload, indent=2) + "\n")
        print(f"Wrote {args.out}", flush=True)
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        for scen, r in results.items():
            print(f"{scen}: p50={r['p50_ms']:.0f} p90={r['p90_ms']:.0f} n={r['n']}")
        print(
            f"reorder_vs_warm_abc={reorder_gap} cold_vs_warm={cold_vs_warm} "
            f"harness_ok={payload['harness_reorder_gap_ok']}"
        )
    try:
        del llm
    except Exception:  # noqa: BLE001
        pass
    print("exiting (hard) to avoid CUDA teardown hang", flush=True)
    os._exit(0)


if __name__ == "__main__":
    sys.exit(main())
