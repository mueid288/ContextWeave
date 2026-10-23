#!/usr/bin/env python3
"""G1 EPIC (LegoLink) bench — **requires DerekHJH/epic vLLM fork**.

Collects per-chunk KV via EPIC's ``cache_fuse_metadata`` / ``hack_kv``, then
links with ``kvlink-N`` (recompute first N tokens of each non-first chunk).

  # After Docs/gates/g1/g1-epic.md install on a dedicated GPU session:
  export CONTEXTWEAVE_ALLOW_MODEL_LOAD=1
  python scripts/g1/epic/g1_epic_probe.py --json   # must report epic_fork_detected
  python scripts/g1/epic/g1_epic_bench.py --json | tee g1_epic.json

Compares full prefill (``fr``) vs LegoLink-8 on a reordered multi-doc prompt.
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


# Multi-fact suite (same docs, different questions) — EPIC quality pre-reg.
QUALITY_CASES: tuple[dict[str, str], ...] = (
    {
        "id": "city",
        "question": "Which city is named in Document Beta? Reply with only the city name.",
        "gold": "Karachi",
    },
    {
        "id": "year",
        "question": "Which year is stated in Document Gamma? Reply with only the year.",
        "gold": "2019",
    },
    {
        "id": "code",
        "question": "What is the secret code in Document Alpha? Reply with only the code.",
        "gold": "ALPHA-9173",
    },
)


def _docs(*, filler_chars: int, order: tuple[str, ...]) -> list[str]:
    fill = ("epic filler. " * max(1, (filler_chars // 12) + 1))[:filler_chars]
    blocks = {
        "A": f"### Document Alpha\nSecret code: ALPHA-9173.\n{fill}\n",
        "B": f"### Document Beta\nNamed city: Karachi.\n{fill}\n",
        "C": f"### Document Gamma\nStated year: 2019.\n{fill}\n",
    }
    return [blocks[k] for k in order]


def _contains_gold(text: str, gold: str) -> bool:
    return gold.lower() in (text or "").lower()


def _p90(samples: list[float]) -> float:
    if not samples:
        return 0.0
    return sorted(samples)[max(0, int(0.9 * (len(samples) - 1)))]


def _prompt_text(*, system: str, docs: list[str], question: str) -> str:
    return system + "\n\n" + "\n".join(docs) + "\n" + question


def _filler_chars_for_target(
    tokenizer,
    *,
    system: str,
    question: str,
    order: tuple[str, ...],
    target_context_tokens: int,
) -> int:
    """Grow per-doc filler chars until full prompt token length ≥ target."""
    lo, hi = 64, 2_000_000
    best: int | None = None
    while lo <= hi:
        mid = (lo + hi) // 2
        docs = _docs(filler_chars=mid, order=order)
        n = len(
            tokenizer.encode(
                _prompt_text(system=system, docs=docs, question=question),
                add_special_tokens=True,
            )
        )
        if n < target_context_tokens:
            lo = mid + 1
        else:
            best = mid
            hi = mid - 1
    if best is None:
        raise ValueError(
            f"Could not reach target_context_tokens={target_context_tokens} "
            f"(max filler search exhausted)"
        )
    return best


def _get_cache_fuse(llm):
    return llm.llm_engine.model_executor.driver_worker.model_runner.model.model.cache_fuse_metadata


def _get_layers(llm):
    return llm.llm_engine.model_executor.driver_worker.model_runner.model.model.layers


def _set_old_kvs(llm, old_kvs) -> None:
    llm.llm_engine.model_executor.driver_worker.model_runner.model.model.old_kvs = old_kvs


def _layer0_seam_keydev(
    llm,
    *,
    token_ids: list[list[int]],
    start_offset: list[int],
    old_kvs: list,
    seam_tokens: int,
) -> float:
    """Mean (1−cos) Layer-0 at doc seams from **isolated** collected keys.

    No extra ``generate`` — joint prefix+seam probes IMA on EPIC Path A when
    ``old_kvs`` is live. Score = mean discontinuity between the token before
    each doc chunk and the first ``seam_tokens`` isolated keys of that chunk.
    """
    del llm  # API symmetry with callers; unused (CPU-side on collected tensors)
    import torch.nn.functional as F

    k_iso = old_kvs[0][0].detach().float()
    diffs: list[float] = []
    n_docs = len(token_ids) - 2
    for doc_i in range(n_docs):
        chunk_idx = doc_i + 1  # skip system
        b = start_offset[chunk_idx]
        if b <= 0 or b >= k_iso.shape[0]:
            continue
        n = min(seam_tokens, len(token_ids[chunk_idx]), k_iso.shape[0] - b)
        if n <= 0:
            continue
        prev = k_iso[b - 1].flatten().unsqueeze(0)
        for t in range(n):
            cur = k_iso[b + t].flatten().unsqueeze(0)
            diffs.append(float(1.0 - F.cosine_similarity(prev, cur).item()))
    if not diffs:
        return 0.0
    return float(sum(diffs) / len(diffs))


def _collect_and_link(
    llm,
    tokenizer,
    *,
    system: str,
    docs: list[str],
    question: str,
    recomp_num: int,
    max_tokens: int,
    return_keydev: bool = False,
) -> tuple[float, str] | tuple[float, str, float]:
    """EPIC two-pass: collect chunk KV, then generate with kvlink recompute.

    If ``return_keydev``, also returns Layer-0 isolated seam discontinuity
    (mean 1−cos) after collect, before LegoLink generate — no extra forwards.
    """
    import torch
    from vllm import SamplingParams

    system_ids = tokenizer.encode(system, add_special_tokens=True)
    if tokenizer.eos_token_id is not None and system_ids and system_ids[-1] == tokenizer.eos_token_id:
        system_ids = system_ids[:-1]
    # Docs must not each start with BOS (would diverge from full-prefill concat).
    doc_ids = [tokenizer.encode(d, add_special_tokens=False) for d in docs]
    q_ids = tokenizer.encode(question, add_special_tokens=False)
    if tokenizer.eos_token_id is not None:
        q_ids = q_ids + [tokenizer.eos_token_id]
    token_ids: list[list[int]] = [system_ids, *doc_ids, q_ids]
    input_ids = [t for chunk in token_ids for t in chunk]

    meta = _get_cache_fuse(llm)
    meta["collect"] = True
    collect_params = SamplingParams(temperature=0.0, max_tokens=1)
    old_kvs: list = []
    for i, chunk in enumerate(token_ids):
        llm.generate(
            sampling_params=collect_params,
            prompt_token_ids=[chunk],
            use_tqdm=False,
        )
        layers = _get_layers(llm)
        for j, layer in enumerate(layers):
            temp_k = layer.self_attn.hack_kv[0].clone()
            temp_v = layer.self_attn.hack_kv[1].clone()
            if i == 0:
                old_kvs.append([temp_k, temp_v])
            else:
                old_kvs[j][0] = torch.cat((old_kvs[j][0], temp_k), dim=0)
                old_kvs[j][1] = torch.cat((old_kvs[j][1], temp_v), dim=0)
        _set_old_kvs(llm, old_kvs)

    start_offset = [0]
    for chunk in token_ids:
        start_offset.append(start_offset[-1] + len(chunk))

    keydev = 0.0
    if return_keydev:
        keydev = _layer0_seam_keydev(
            llm,
            token_ids=token_ids,
            start_offset=start_offset,
            old_kvs=old_kvs,
            seam_tokens=recomp_num,
        )

    # LegoLink: recompute first recomp_num tokens of each non-first chunk;
    # recompute the entire question tail.
    temp: list[int] = []
    for i in range(1, len(start_offset) - 1):
        if i == len(start_offset) - 2:
            temp += list(range(start_offset[i], start_offset[i + 1]))
        else:
            temp += list(range(start_offset[i], start_offset[i] + recomp_num))
    meta["kvlink"] = temp
    meta["check"] = False
    meta["collect"] = False

    gen_params = SamplingParams(temperature=0.0, max_tokens=max_tokens)
    t0 = time.perf_counter()
    outs = llm.generate(
        sampling_params=gen_params,
        prompt_token_ids=[input_ids],
        use_tqdm=False,
    )
    ms = (time.perf_counter() - t0) * 1000.0
    text = outs[0].outputs[0].text.strip() if outs and outs[0].outputs else ""
    if return_keydev:
        return ms, text, keydev
    return ms, text


def _full_prefill(llm, prompt: str, *, max_tokens: int) -> tuple[float, str]:
    from vllm import SamplingParams

    params = SamplingParams(temperature=0.0, max_tokens=max_tokens)
    t0 = time.perf_counter()
    outs = llm.generate([prompt], params, use_tqdm=False)
    ms = (time.perf_counter() - t0) * 1000.0
    text = outs[0].outputs[0].text.strip() if outs and outs[0].outputs else ""
    return ms, text


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default=os.environ.get("SMOKE_MODEL", "Qwen/Qwen3-8B"))
    parser.add_argument("--max-model-len", type=int, default=8192)
    parser.add_argument("--filler-chars", type=int, default=2000)
    parser.add_argument(
        "--target-context-tokens",
        type=int,
        default=None,
        help="If set, ignore --filler-chars and grow docs until prompt ≈ this many tokens.",
    )
    parser.add_argument("--max-tokens", type=int, default=24)
    parser.add_argument("--recomp-num", type=int, default=8, help="LegoLink-N")
    parser.add_argument("--runs", type=int, default=5, help="Timed runs after 1 warmup (PRD G1).")
    parser.add_argument("--gpu-memory-utilization", type=float, default=0.80)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument(
        "--suite",
        choices=("single", "quality"),
        default="single",
        help="single=city gold only; quality=3 facts (city/year/code) for broader quality.",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if os.environ.get("CONTEXTWEAVE_ALLOW_MODEL_LOAD") != "1":
        print(
            "Refusing: set CONTEXTWEAVE_ALLOW_MODEL_LOAD=1 on the GPU host only.",
            file=sys.stderr,
        )
        return 1

    import importlib.util

    import vllm

    probe_path = G1_EPIC / "g1_epic_probe.py"
    spec = importlib.util.spec_from_file_location("g1_epic_probe", probe_path)
    assert spec and spec.loader
    probe = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(probe)
    scan = probe._scan_vllm_tree(Path(vllm.__file__).resolve().parent)
    if not (scan["has_cache_fuse"] and scan["has_hack_kv"]):
        payload = {
            "gate": "G1-step4-epic",
            "error": "EPIC fork not detected",
            "scan": scan,
            "pass_heuristic": False,
            "note": "Run scripts/g1/epic/g1_epic_probe.py / Docs/gates/g1/g1-epic.md first.",
        }
        print(json.dumps(payload, indent=2) if args.json else payload["note"])
        return 3

    from transformers import AutoTokenizer
    from vllm import LLM

    # EPIC demos force XFORMERS; tolerate missing selector on weird pins.
    try:
        from vllm.attention.selector import _Backend, global_force_attn_backend

        global_force_attn_backend(_Backend.XFORMERS)
    except Exception as exc:  # noqa: BLE001 — fork variance
        print(f"warn: could not force XFORMERS ({exc})", flush=True)

    tokenizer = AutoTokenizer.from_pretrained(
        args.model, add_bos_token=True, trust_remote_code=True
    )
    system = (
        "You are a careful assistant. Use only the documents. "
        "Prefer a short answer."
    )
    cases = list(QUALITY_CASES) if args.suite == "quality" else [QUALITY_CASES[0]]
    order = ("B", "C", "A")
    # Scale against the longest question so all suite prompts stay ≥ target.
    scale_question = max((c["question"] for c in cases), key=len)
    filler_chars = args.filler_chars
    if args.target_context_tokens is not None:
        if args.target_context_tokens + args.max_tokens + 8 > args.max_model_len:
            print(
                f"target-context-tokens={args.target_context_tokens} + decode "
                f"exceeds max-model-len={args.max_model_len}",
                file=sys.stderr,
            )
            return 2
        filler_chars = _filler_chars_for_target(
            tokenizer,
            system=system,
            question=scale_question,
            order=order,
            target_context_tokens=args.target_context_tokens,
        )
        print(
            f"  scaled filler_chars={filler_chars} for target≈{args.target_context_tokens}",
            flush=True,
        )
    docs_bca = _docs(filler_chars=filler_chars, order=order)
    prompt_tokens_by_case: dict[str, int] = {}
    for c in cases:
        pt = len(
            tokenizer.encode(
                _prompt_text(system=system, docs=docs_bca, question=c["question"]),
                add_special_tokens=True,
            )
        )
        prompt_tokens_by_case[c["id"]] = pt
    prompt_tokens = min(prompt_tokens_by_case.values())
    print(
        f"EPIC bench model={args.model} suite={args.suite} recomp={args.recomp_num} "
        f"prompt_tokens_min={prompt_tokens} filler_chars={filler_chars}",
        flush=True,
    )
    if max(prompt_tokens_by_case.values()) + args.max_tokens > args.max_model_len:
        print(
            f"prompt_tokens exceed max_model_len={args.max_model_len}: "
            f"{prompt_tokens_by_case}",
            file=sys.stderr,
        )
        return 2
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

    warmup_prompt = _prompt_text(
        system=system, docs=docs_bca, question=cases[0]["question"]
    )
    print("  [warmup full prefill] discarded", flush=True)
    _full_prefill(llm, warmup_prompt, max_tokens=args.max_tokens)

    case_results: list[dict] = []
    for c in cases:
        full_prompt = _prompt_text(system=system, docs=docs_bca, question=c["question"])
        fr_samples: list[float] = []
        fr_text = ""
        for i in range(args.runs):
            print(f"  [{c['id']} full] {i + 1}/{args.runs} …", flush=True)
            fr_ms, fr_text = _full_prefill(llm, full_prompt, max_tokens=args.max_tokens)
            fr_samples.append(fr_ms)
            print(f"  [{c['id']} full] {fr_ms:.0f} ms", flush=True)

        link_samples: list[float] = []
        link_text = ""
        for i in range(args.runs):
            print(f"  [{c['id']} kvlink-{args.recomp_num}] {i + 1}/{args.runs} …", flush=True)
            link_ms, link_text = _collect_and_link(
                llm,
                tokenizer,
                system=system,
                docs=docs_bca,
                question=c["question"],
                recomp_num=args.recomp_num,
                max_tokens=args.max_tokens,
            )
            link_samples.append(link_ms)
            print(f"  [{c['id']} kvlink-{args.recomp_num}] {link_ms:.0f} ms", flush=True)

        fr_med = statistics.median(fr_samples)
        link_med = statistics.median(link_samples)
        case_results.append(
            {
                "id": c["id"],
                "gold": c["gold"],
                "prompt_tokens": prompt_tokens_by_case[c["id"]],
                "full_prefill_ms": fr_med,
                "full_prefill_p90_ms": _p90(fr_samples),
                "kvlink_ms": link_med,
                "kvlink_p90_ms": _p90(link_samples),
                "full_prefill_samples_ms": fr_samples,
                "kvlink_samples_ms": link_samples,
                "full_vs_kvlink_speedup": fr_med / link_med if link_med > 0 else None,
                "outputs": {"full_prefill": fr_text, "kvlink": link_text},
                "full_contains": _contains_gold(fr_text, c["gold"]),
                "kvlink_contains": _contains_gold(link_text, c["gold"]),
                "latency_ok": link_med < 0.85 * fr_med,
            }
        )

    try:
        del llm
    except Exception:  # noqa: BLE001
        pass

    n = len(case_results)
    full_hits = sum(1 for r in case_results if r["full_contains"])
    link_hits = sum(1 for r in case_results if r["kvlink_contains"])
    contains_rate_full = full_hits / n
    contains_rate_kvlink = link_hits / n
    quality_ok = contains_rate_full >= 0.9 and contains_rate_kvlink >= 0.9
    # Latency bar: every case must clear ≥15% (strict; avoids one easy case carrying).
    latency_ok = all(r["latency_ok"] for r in case_results)
    # Headline numbers from city (or sole) case for continuity with EPIC@12k.
    head = case_results[0]
    payload = {
        "gate": "G1-step4-epic",
        "suite": args.suite,
        "pre_reg": (
            "Docs/pre-reg/pre-reg-epic-quality.md"
            if args.suite == "quality"
            else "Docs/pre-reg/pre-reg-epic-12k.md"
        ),
        "model": args.model,
        "recomp_num": args.recomp_num,
        "runs": args.runs,
        "filler_chars": filler_chars,
        "target_context_tokens": args.target_context_tokens,
        "prompt_tokens": head["prompt_tokens"],
        "prompt_tokens_by_case": prompt_tokens_by_case,
        "max_model_len": args.max_model_len,
        "cases": case_results,
        "contains_rate_full": contains_rate_full,
        "contains_rate_kvlink": contains_rate_kvlink,
        "full_prefill_ms": head["full_prefill_ms"],
        "full_prefill_p90_ms": head["full_prefill_p90_ms"],
        "kvlink_ms": head["kvlink_ms"],
        "kvlink_p90_ms": head["kvlink_p90_ms"],
        "full_vs_kvlink_speedup": head["full_vs_kvlink_speedup"],
        "outputs": head["outputs"],
        "gold": head["gold"],
        "latency_ok": latency_ok,
        "quality_ok": quality_ok,
        "pass_heuristic": latency_ok and quality_ok,
        "note": (
            "LegoLink-N on EPIC fork. single: city gold. quality suite: ≥0.9 contains "
            "on both arms across cases AND every case ≥15% TTFT win."
        ),
    }
    if args.out:
        args.out.write_text(json.dumps(payload, indent=2) + "\n")
        print(f"Wrote {args.out}", flush=True)
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(
            f"suite={args.suite} fr={head['full_prefill_ms']:.0f} "
            f"kvlink={head['kvlink_ms']:.0f} "
            f"speedup={head['full_vs_kvlink_speedup']:.2f}x "
            f"contains_kvlink={contains_rate_kvlink:.2f} "
            f"pass={payload['pass_heuristic']}"
        )
    code = 0 if payload["pass_heuristic"] else 4
    print("exiting (hard) to avoid CUDA teardown hang", flush=True)
    os._exit(code)


if __name__ == "__main__":
    sys.exit(main())
