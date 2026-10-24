#!/usr/bin/env python3
"""Live C1 proof: frequency-stable order vs shuffled order TTFT (HTTP).

Requires vLLM (or compatible) with **prefix caching enabled**.

  python scripts/product/eval_order_ttft.py \\
    --base-url http://127.0.0.1:8000 \\
    --model mistralai/Mistral-7B-Instruct-v0.2 \\
    --out artifacts/product-order-ttft/report.json --json
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
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from contextweave.product.frequency import FrequencyPrior  # noqa: E402
from contextweave.product.live_order import (  # noqa: E402
    apply_chat_documents,
    format_documents_block,
    reorder_documents,
)

DOC_IDS = ("doc-alpha", "doc-beta", "doc-gamma")
QUESTION = "Which city is named in Document Beta? Reply with only the city name."
GOLD = "Karachi"


def _doc_bodies(*, filler_chars: int) -> dict[str, str]:
    fill = ("ttft filler sentence. " * max(1, filler_chars // 20))[:filler_chars]
    return {
        "doc-alpha": f"Document Alpha. Secret code: ALPHA-9173.\n{fill}",
        "doc-beta": f"Document Beta. Named city: Karachi.\n{fill}",
        "doc-gamma": f"Document Gamma. Stated year: 2019.\n{fill}",
    }


def _p50(xs: list[float]) -> float:
    if not xs:
        return float("nan")
    return float(statistics.median(xs))


def _chat_ms(
    *,
    base_url: str,
    model: str,
    messages: list[dict],
    max_tokens: int,
    timeout: float,
) -> tuple[float, str, dict]:
    url = base_url.rstrip("/") + "/v1/chat/completions"
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.0,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code}: {e.read().decode('utf-8', errors='replace')}") from e
    ms = (time.perf_counter() - t0) * 1000.0
    body = json.loads(raw.decode("utf-8"))
    text = ((body.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
    usage = body.get("usage") or {}
    return ms, str(text), usage


def _messages_for(
    mode: str,
    *,
    bodies: dict[str, str],
    prior: FrequencyPrior,
    rng: random.Random,
) -> list[dict]:
    docs = [{"document_id": d, "content": bodies[d]} for d in DOC_IDS]
    if mode == "frequency":
        body = {
            "messages": [{"role": "user", "content": QUESTION}],
            "cw_documents": docs,
            "cw_chunk_order": "by_frequency_desc",
        }
        out = apply_chat_documents(body, prior=prior, observe=False)
        return list(out["messages"])
    if mode == "shuffled":
        order = list(DOC_IDS)
        rng.shuffle(order)
        chunks = reorder_documents(
            [{"document_id": d, "content": bodies[d]} for d in order],
            "natural",
            prior=None,
            observe=False,
        )
        block = format_documents_block(chunks)
        return [{"role": "user", "content": f"{block}\n\n{QUESTION}"}]
    raise ValueError(mode)


def run_bench(
    *,
    base_url: str,
    model: str,
    filler_chars: int,
    warm_trials: int,
    max_tokens: int,
    timeout: float,
    seed: int,
) -> dict:
    bodies = _doc_bodies(filler_chars=filler_chars)
    prior = FrequencyPrior(cold_start_n=0)
    # Hot: beta (matches city question + Zipf-like)
    prior.observe(["doc-beta"] * 5 + ["doc-alpha"] * 2 + ["doc-gamma"])
    rng = random.Random(seed)

    results: dict[str, dict] = {}
    for mode in ("shuffled", "frequency"):
        times: list[float] = []
        texts: list[str] = []
        usages: list[dict] = []
        # 1 warmup discarded
        _chat_ms(
            base_url=base_url,
            model=model,
            messages=_messages_for(mode, bodies=bodies, prior=prior, rng=rng),
            max_tokens=max_tokens,
            timeout=timeout,
        )
        for _ in range(warm_trials):
            ms, text, usage = _chat_ms(
                base_url=base_url,
                model=model,
                messages=_messages_for(mode, bodies=bodies, prior=prior, rng=rng),
                max_tokens=max_tokens,
                timeout=timeout,
            )
            times.append(ms)
            texts.append(text)
            usages.append(usage)
        contains = sum(1 for t in texts if GOLD.lower() in t.lower()) / max(1, len(texts))
        results[mode] = {
            "warm_ms": times,
            "warm_p50_ms": _p50(times),
            "warm_mean_ms": sum(times) / len(times),
            "contains_rate": contains,
            "usage_samples": usages[:3],
        }

    nat = results["shuffled"]["warm_p50_ms"]
    freq = results["frequency"]["warm_p50_ms"]
    speedup = (nat / freq) if freq > 0 else 0.0
    pass_heuristic = bool(speedup >= 1.15 and results["frequency"]["contains_rate"] >= 0.8)
    return {
        "pre_reg": "Docs/pre-reg/pre-reg-product-live-ttft.md",
        "model": model,
        "base_url": base_url,
        "filler_chars": filler_chars,
        "warm_trials": warm_trials,
        "modes": results,
        "speedup_shuffled_over_frequency": speedup,
        "pass_heuristic": pass_heuristic,
        "pass_bar": "warm p50 speedup >= 1.15 and frequency contains >= 0.8",
        "note": (
            "Requires --enable-prefix-caching on the server. "
            "Frequency keeps a stable doc order; shuffled breaks the prefix each trial."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--base-url", required=True)
    p.add_argument("--model", default="mistralai/Mistral-7B-Instruct-v0.2")
    p.add_argument("--filler-chars", type=int, default=2500)
    p.add_argument("--warm-trials", type=int, default=8)
    p.add_argument("--max-tokens", type=int, default=16)
    p.add_argument("--timeout", type=float, default=180.0)
    p.add_argument("--seed", type=int, default=7)
    p.add_argument("--out", type=Path, default=None)
    p.add_argument("--json", action="store_true")
    p.add_argument(
        "--dry-build",
        action="store_true",
        help="CPU only: print one message per mode, no HTTP",
    )
    args = p.parse_args(argv)

    if args.dry_build:
        bodies = _doc_bodies(filler_chars=200)
        prior = FrequencyPrior(cold_start_n=0)
        prior.observe(["doc-beta"] * 3)
        rng = random.Random(args.seed)
        payload = {
            mode: _messages_for(mode, bodies=bodies, prior=prior, rng=rng)[0]["content"][:200]
            for mode in ("shuffled", "frequency")
        }
        print(json.dumps({"dry_build": payload}, indent=2))
        return 0

    report = run_bench(
        base_url=args.base_url,
        model=args.model,
        filler_chars=args.filler_chars,
        warm_trials=args.warm_trials,
        max_tokens=args.max_tokens,
        timeout=args.timeout,
        seed=args.seed,
    )
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, indent=2) + "\n")
        print(f"Wrote {args.out}", flush=True)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(
            f"pass={report['pass_heuristic']} "
            f"speedup={report['speedup_shuffled_over_frequency']:.2f} "
            f"shuf_p50={report['modes']['shuffled']['warm_p50_ms']:.0f}ms "
            f"freq_p50={report['modes']['frequency']['warm_p50_ms']:.0f}ms"
        )
    return 0 if report["pass_heuristic"] else 4


if __name__ == "__main__":
    raise SystemExit(main())
