#!/usr/bin/env python3
"""Gate R1 GPU collect via OpenAI-compatible HTTP (vLLM + optional LMCache C3).

Runs **only** when CONTEXTWEAVE_ALLOW_MODEL_LOAD=1 (rented GPU / Colab).
Does not import torch/vllm locally — talks HTTP to a running server.

Configs per request:
  C0 — natural/shuffled doc order; unique salt so prefix cache cannot help
  C1 — frequency-stable order; shared prefix can hit (prefix caching ON)
  C3 — same prompt as C1 against --c3-base-url (LMCache CacheBlend server);
       if omitted, C3 rows are written with feasible=false

  export CONTEXTWEAVE_ALLOW_MODEL_LOAD=1
  python scripts/r1/collect_oracle_http.py \\
    --base-url http://127.0.0.1:8000 \\
    --model Qwen/Qwen2.5-7B-Instruct \\
    --n-requests 40 --runs 3 \\
    --out artifacts/r1-oracle-WIP/oracle_trials.jsonl
"""

from __future__ import annotations

import argparse
import json
import random
import statistics
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

_REPO_BOOT = Path(__file__).resolve()
for _cand in _REPO_BOOT.parents:
    if (_cand / "pyproject.toml").exists():
        ROOT = _cand
        break
else:
    raise SystemExit("Could not find repo root (pyproject.toml)")
SRC = ROOT / "src"
SCRIPTS_R1 = ROOT / "scripts" / "r1"
for _p in (SRC, str(SCRIPTS_R1)):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from contextweave.product.frequency import FrequencyPrior  # noqa: E402
from contextweave.product.live_order import reorder_documents  # noqa: E402
from contextweave.safety import assert_model_load_allowed  # noqa: E402

import workload as r1_workload  # noqa: E402


def _chat(
    *,
    base_url: str,
    model: str,
    prompt: str,
    max_tokens: int,
    timeout: float,
    extra_body: dict | None = None,
) -> tuple[float, str]:
    url = base_url.rstrip("/") + "/v1/chat/completions"
    payload: dict = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.0,
    }
    if extra_body:
        payload.update(extra_body)
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as e:
        raise RuntimeError(
            f"HTTP {e.code}: {e.read().decode('utf-8', errors='replace')}"
        ) from e
    ms = (t0 and (time.perf_counter() - t0) * 1000.0)
    body = json.loads(raw.decode("utf-8"))
    text = ((body.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
    return ms, str(text)


def _timed_median(
    *,
    base_url: str,
    model: str,
    prompt: str,
    max_tokens: int,
    timeout: float,
    runs: int,
    warmup: bool,
) -> tuple[float, str]:
    last_text = ""
    times: list[float] = []
    rounds = runs + (1 if warmup else 0)
    for i in range(rounds):
        ms, text = _chat(
            base_url=base_url,
            model=model,
            prompt=prompt,
            max_tokens=max_tokens,
            timeout=timeout,
        )
        last_text = text
        if warmup and i == 0:
            continue
        times.append(ms)
    return float(statistics.median(times)), last_text


def _prompt_for(
    req: r1_workload.R1Request,
    *,
    mode: str,
    prior: FrequencyPrior,
    rng: random.Random,
    salt: str,
    blend_special_str: str = " # # ",
) -> str:
    docs = [
        {"document_id": d, "content": req.bodies[d]} for d in req.document_ids
    ]
    if mode == "C0":
        order = list(req.document_ids)
        rng.shuffle(order)
        chunks = reorder_documents(
            [{"document_id": d, "content": req.bodies[d]} for d in order],
            "natural",
            prior=None,
            observe=False,
        )
        ordered = [c.document_id for c in chunks]
        body = r1_workload.format_prompt(req, ordered)
        # Break prefix match so C0 cannot ride the warm cache.
        return f"[salt:{salt}]\n\n{body}"
    if mode == "C1":
        chunks = reorder_documents(
            docs, "by_frequency_desc", prior=prior, observe=True
        )
        ordered = [c.document_id for c in chunks]
        return r1_workload.format_prompt(req, ordered)
    if mode == "C3":
        # Frequency order + blend separators so LMCache can split/reuse chunks.
        chunks = reorder_documents(
            docs, "by_frequency_desc", prior=prior, observe=False
        )
        ordered = [c.document_id for c in chunks]
        return r1_workload.format_prompt(
            req, ordered, blend_special_str=blend_special_str
        )
    raise ValueError(mode)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--base-url", default="http://127.0.0.1:8000")
    p.add_argument(
        "--c3-base-url",
        default="",
        help="LMCache CacheBlend OpenAI server; empty → C3 feasible=false",
    )
    p.add_argument("--model", default="Qwen/Qwen2.5-7B-Instruct")
    p.add_argument("--n-requests", type=int, default=40)
    p.add_argument("--runs", type=int, default=3)
    p.add_argument("--filler-chars", type=int, default=1800)
    p.add_argument("--max-tokens", type=int, default=32)
    p.add_argument("--timeout", type=float, default=180.0)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--cold-start-n", type=int, default=0)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--report", type=Path, default=None)
    p.add_argument("--runtime-id", default="vllm-prefix+optional-lmcache")
    p.add_argument("--json", action="store_true")
    p.add_argument(
        "--dry-workload",
        action="store_true",
        help="CPU only: write workload JSON and exit (no HTTP)",
    )
    p.add_argument(
        "--only-configs",
        default="",
        help="Comma list to measure (e.g. C3). Default: C0,C1,C3",
    )
    p.add_argument(
        "--blend-special-str",
        default=" # # ",
        help="Separator inserted between docs for C3 CacheBlend prompts",
    )
    args = p.parse_args(argv)
    only = {
        c.strip().upper()
        for c in (args.only_configs or "").split(",")
        if c.strip()
    }
    configs = [c for c in ("C0", "C1", "C3") if not only or c in only]

    if args.dry_workload:
        reqs = r1_workload.generate_requests(
            n=args.n_requests, seed=args.seed, filler_chars=args.filler_chars
        )
        args.out.parent.mkdir(parents=True, exist_ok=True)
        payload = [
            {
                "request_id": r.request_id,
                "slice_id": r.slice_id,
                "gold": r.gold,
                "document_ids": list(r.document_ids),
                "question": r.question,
            }
            for r in reqs
        ]
        args.out.write_text(json.dumps(payload, indent=2) + "\n")
        print(f"Wrote workload preview {args.out} n={len(reqs)}", flush=True)
        return 0

    assert_model_load_allowed("call a remote LLM for R1 collect")

    reqs = r1_workload.generate_requests(
        n=args.n_requests, seed=args.seed, filler_chars=args.filler_chars
    )
    prior = FrequencyPrior(cold_start_n=args.cold_start_n)
    rng = random.Random(args.seed)
    c3_url = (args.c3_base_url or "").strip()
    trials: list[dict] = []

    print(
        f"r1 collect model={args.model} n={args.n_requests} runs={args.runs} "
        f"configs={configs} c3={'yes' if c3_url else 'skip'} base={args.base_url}",
        flush=True,
    )

    # Warm frequency prior with a pass of observe-only C1 orders
    for req in reqs:
        docs = [
            {"document_id": d, "content": req.bodies[d]} for d in req.document_ids
        ]
        reorder_documents(docs, "by_frequency_desc", prior=prior, observe=True)

    for req in reqs:
        for mode in configs:
            if mode == "C3" and not c3_url:
                trials.append(
                    {
                        "request_id": req.request_id,
                        "config": "C3",
                        "quality": 0.0,
                        "ttft_ms": 0.0,
                        "feasible": False,
                        "runtime_id": args.runtime_id,
                        "slice_id": req.slice_id,
                        "notes": "no --c3-base-url (LMCache CacheBlend server)",
                    }
                )
                continue
            salt = f"{req.request_id}-{mode}-{rng.randrange(1 << 30)}"
            prompt = _prompt_for(
                req,
                mode=mode,
                prior=prior,
                rng=rng,
                salt=salt,
                blend_special_str=args.blend_special_str,
            )
            url = c3_url if mode == "C3" else args.base_url
            try:
                ttft_ms, text = _timed_median(
                    base_url=url,
                    model=args.model,
                    prompt=prompt,
                    max_tokens=args.max_tokens,
                    timeout=args.timeout,
                    runs=args.runs,
                    warmup=True,
                )
                q = r1_workload.quality_contains(text, req.gold)
                trials.append(
                    {
                        "request_id": req.request_id,
                        "config": mode,
                        "quality": q,
                        "ttft_ms": ttft_ms,
                        "feasible": True,
                        "runtime_id": args.runtime_id,
                        "slice_id": req.slice_id,
                        "notes": (text or "")[:160],
                    }
                )
            except Exception as exc:  # noqa: BLE001
                trials.append(
                    {
                        "request_id": req.request_id,
                        "config": mode,
                        "quality": 0.0,
                        "ttft_ms": 0.0,
                        "feasible": False,
                        "runtime_id": args.runtime_id,
                        "slice_id": req.slice_id,
                        "notes": f"error: {exc}",
                    }
                )
                print(f"warn {req.request_id} {mode}: {exc}", flush=True)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w") as f:
        for row in trials:
            f.write(json.dumps(row) + "\n")
    print(f"Wrote {args.out} rows={len(trials)}", flush=True)

    # CPU oracle summary if enough feasible rows
    from contextweave.oracle import ConfigTrial, oracle_upside

    ct = [
        ConfigTrial(
            request_id=r["request_id"],
            config=r["config"],
            quality=float(r["quality"]),
            ttft_ms=float(r["ttft_ms"]),
            feasible=bool(r["feasible"]),
            runtime_id=str(r.get("runtime_id", "")),
            notes=str(r.get("notes", "")),
            slice_id=str(r.get("slice_id", "")),
        )
        for r in trials
    ]
    report = oracle_upside(ct)
    payload = report.to_dict()
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(payload, indent=2) + "\n")
        print(f"Wrote {args.report}", flush=True)
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(
            f"r1_pass={report.r1_pass} fixed={report.best_fixed_config} "
            f"ttft_red={report.ttft_reduction_fraction} "
            f"gate_need={report.gate_need_slices}",
            flush=True,
        )
    return 0 if report.r1_pass else 4


if __name__ == "__main__":
    raise SystemExit(main())
