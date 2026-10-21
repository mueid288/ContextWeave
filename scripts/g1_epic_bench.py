#!/usr/bin/env python3
"""G1 EPIC (LegoLink) bench — **requires DerekHJH/epic vLLM fork**.

Collects per-chunk KV via EPIC's ``cache_fuse_metadata`` / ``hack_kv``, then
links with ``kvlink-N`` (recompute first N tokens of each non-first chunk).

  # After Docs/g1-epic.md install on a dedicated GPU session:
  export CONTEXTWEAVE_ALLOW_MODEL_LOAD=1
  python scripts/g1_epic_probe.py --json   # must report epic_fork_detected
  python scripts/g1_epic_bench.py --json | tee g1_epic.json

Compares full prefill (``fr``) vs LegoLink-8 on a reordered multi-doc prompt.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def _docs(*, filler_chars: int, order: tuple[str, ...]) -> list[str]:
    blocks = {
        "A": f"### Document Alpha\nSecret code: ALPHA-9173.\n"
        f"{('epic filler. ' * 200)[:filler_chars]}\n",
        "B": f"### Document Beta\nNamed city: Karachi.\n"
        f"{('epic filler. ' * 200)[:filler_chars]}\n",
        "C": f"### Document Gamma\nStated year: 2019.\n"
        f"{('epic filler. ' * 200)[:filler_chars]}\n",
    }
    return [blocks[k] for k in order]


def _get_cache_fuse(llm):
    return llm.llm_engine.model_executor.driver_worker.model_runner.model.model.cache_fuse_metadata


def _get_layers(llm):
    return llm.llm_engine.model_executor.driver_worker.model_runner.model.model.layers


def _set_old_kvs(llm, old_kvs) -> None:
    llm.llm_engine.model_executor.driver_worker.model_runner.model.model.old_kvs = old_kvs


def _collect_and_link(
    llm,
    tokenizer,
    *,
    system: str,
    docs: list[str],
    question: str,
    recomp_num: int,
    max_tokens: int,
) -> tuple[float, str]:
    """EPIC two-pass: collect chunk KV, then generate with kvlink recompute."""
    import torch
    from vllm import SamplingParams

    system_ids = tokenizer.encode(system, add_special_tokens=True)
    if tokenizer.eos_token_id is not None and system_ids and system_ids[-1] == tokenizer.eos_token_id:
        system_ids = system_ids[:-1]
    doc_ids = [tokenizer.encode(d, add_special_tokens=True) for d in docs]
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
    parser.add_argument("--max-tokens", type=int, default=24)
    parser.add_argument("--recomp-num", type=int, default=8, help="LegoLink-N")
    parser.add_argument("--gpu-memory-utilization", type=float, default=0.80)
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

    probe_path = ROOT / "scripts" / "g1_epic_probe.py"
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
            "note": "Run scripts/g1_epic_probe.py / Docs/g1-epic.md first.",
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
    docs_bca = _docs(filler_chars=args.filler_chars, order=("B", "C", "A"))
    question = "Which city is named in Document Beta? Reply with only the city name."
    gold = "Karachi"
    full_prompt = system + "\n\n" + "\n".join(docs_bca) + "\n" + question

    print(f"EPIC bench model={args.model} recomp={args.recomp_num}", flush=True)
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

    print("  [full prefill BCA] …", flush=True)
    fr_ms, fr_text = _full_prefill(llm, full_prompt, max_tokens=args.max_tokens)
    print(f"  [full prefill BCA] {fr_ms:.0f} ms", flush=True)

    print(f"  [kvlink-{args.recomp_num} BCA] …", flush=True)
    link_ms, link_text = _collect_and_link(
        llm,
        tokenizer,
        system=system,
        docs=docs_bca,
        question=question,
        recomp_num=args.recomp_num,
        max_tokens=args.max_tokens,
    )
    print(f"  [kvlink-{args.recomp_num} BCA] {link_ms:.0f} ms", flush=True)

    del llm
    quality_ok = gold.lower() in fr_text.lower() and gold.lower() in link_text.lower()
    # Link should beat full prefill on TTFT for this PIC workload (paper claim).
    latency_ok = link_ms < 0.85 * fr_ms
    payload = {
        "gate": "G1-step4-epic",
        "model": args.model,
        "recomp_num": args.recomp_num,
        "full_prefill_ms": fr_ms,
        "kvlink_ms": link_ms,
        "full_vs_kvlink_speedup": fr_ms / link_ms if link_ms > 0 else None,
        "outputs": {"full_prefill": fr_text, "kvlink": link_text},
        "gold": gold,
        "latency_ok": latency_ok,
        "quality_ok": quality_ok,
        "pass_heuristic": latency_ok and quality_ok,
        "note": (
            "LegoLink-N on EPIC fork. pass ⇒ kvlink ≥15% faster than full AND "
            "both answers contain gold."
        ),
    }
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(
            f"fr={fr_ms:.0f} kvlink={link_ms:.0f} "
            f"speedup={payload['full_vs_kvlink_speedup']:.2f}x "
            f"pass={payload['pass_heuristic']}"
        )
    return 0 if payload["pass_heuristic"] else 4


if __name__ == "__main__":
    sys.exit(main())
