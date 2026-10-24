"""A/B warm latency: shuffled retrieval order vs frequency via shim."""

from __future__ import annotations

from copy import deepcopy
import json
import random
import statistics
from pathlib import Path
from typing import Any

import yaml

from contextweave.product.rag_demo.client import AskResult, ask, build_ask_body
from contextweave.product.rag_demo.index import LexicalIndex, ensure_index
from contextweave.product.rag_demo.retrieve import retrieve


def _p50(xs: list[float]) -> float:
    if not xs:
        return float("nan")
    return float(statistics.median(xs))


def load_questions(path: Path) -> list[dict[str, Any]]:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, dict):
        qs = data.get("questions") or []
    elif isinstance(data, list):
        qs = data
    else:
        raise ValueError(f"unexpected questions file shape: {path}")
    out = []
    for i, q in enumerate(qs):
        if isinstance(q, str):
            out.append({"id": f"q{i}", "question": q, "gold": None})
        else:
            out.append(
                {
                    "id": str(q.get("id") or f"q{i}"),
                    "question": str(q["question"]),
                    "gold": q.get("gold"),
                }
            )
    return out


def build_mode_payload(
    mode: str,
    *,
    question: str,
    documents: list[dict[str, str]],
    model: str,
    rng: random.Random,
) -> dict[str, Any]:
    """
    Construct the chat body for a mode (no HTTP).

    - frequency: cw_chunk_order=by_frequency_desc (shim reorders)
    - shuffled: permute retrieved chunk order; cw_chunk_order=natural
    """
    docs = deepcopy(documents)
    if mode == "shuffled":
        rng.shuffle(docs)
        order = "natural"
    elif mode == "frequency":
        order = "by_frequency_desc"
    else:
        raise ValueError(f"unknown mode: {mode}")
    return build_ask_body(question, docs, model=model, chunk_order=order)


def _gold_ok(answer: str, gold: Any) -> bool | None:
    if gold is None:
        return None
    needle = str(gold).lower()
    return needle in (answer or "").lower()


def run_bench(
    *,
    index: LexicalIndex,
    questions: list[dict[str, Any]],
    base_url: str,
    model: str,
    k: int = 3,
    warm_trials: int = 8,
    seed: int = 7,
    max_tokens: int = 64,
    timeout: float = 180.0,
    prewarm_observations: int = 40,
) -> dict[str, Any]:
    """
    For each mode: 1 warmup discard + warm_trials timed asks.

    Frequency mode relies on the shim's rolling prior. We first POST the full
    question suite once with by_frequency_desc so the prior is warm (or the
    operator can start cw-serve-order with --cold-start-n 0 and we still observe).
    """
    if len(questions) < 1:
        raise ValueError("need at least one question")
    rng = random.Random(seed)

    # Cache retrieval per question id (deterministic)
    retrieved: dict[str, list[dict[str, str]]] = {}
    for q in questions:
        retrieved[q["id"]] = retrieve(index, q["question"], k=k)

    # Pre-warm shim prior by walking the suite (discarded for timing)
    for q in questions:
        ask(
            base_url=base_url,
            question=q["question"],
            documents=retrieved[q["id"]],
            model=model,
            chunk_order="by_frequency_desc",
            max_tokens=8,
            timeout=timeout,
        )

    results: dict[str, dict[str, Any]] = {}
    trial_log: list[dict[str, Any]] = []

    for mode in ("shuffled", "frequency"):
        times: list[float] = []
        golds: list[bool] = []
        answers: list[str] = []
        # 1 warmup discard — cycle first question
        q0 = questions[0]
        ask(
            base_url=base_url,
            question=q0["question"],
            documents=_docs_for_mode(mode, retrieved[q0["id"]], rng),
            model=model,
            chunk_order=("by_frequency_desc" if mode == "frequency" else "natural"),
            max_tokens=max_tokens,
            timeout=timeout,
        )
        for t in range(warm_trials):
            q = questions[t % len(questions)]
            docs = _docs_for_mode(mode, retrieved[q["id"]], rng)
            order = "by_frequency_desc" if mode == "frequency" else "natural"
            res: AskResult = ask(
                base_url=base_url,
                question=q["question"],
                documents=docs,
                model=model,
                chunk_order=order,
                max_tokens=max_tokens,
                timeout=timeout,
            )
            times.append(res.wall_ms)
            answers.append(res.answer)
            ok = _gold_ok(res.answer, q.get("gold"))
            if ok is not None:
                golds.append(ok)
            trial_log.append(
                {
                    "mode": mode,
                    "trial": t,
                    "question_id": q["id"],
                    "wall_ms": res.wall_ms,
                    "gold_ok": ok,
                    "retrieved_ids": [d["document_id"] for d in docs],
                    "answer_preview": (res.answer or "")[:200],
                }
            )
        gold_rate = (sum(golds) / len(golds)) if golds else None
        results[mode] = {
            "warm_ms": times,
            "warm_p50_ms": _p50(times),
            "warm_mean_ms": sum(times) / len(times) if times else float("nan"),
            "gold_ok_rate": gold_rate,
            "n_gold_checked": len(golds),
        }

    shuf = results["shuffled"]["warm_p50_ms"]
    freq = results["frequency"]["warm_p50_ms"]
    speedup = (shuf / freq) if freq and freq > 0 else 0.0
    # Functional: count unique questions with gold that succeeded at least once in frequency
    functional_hits = 0
    checked = 0
    for q in questions:
        if q.get("gold") is None:
            continue
        checked += 1
        # any frequency trial for this q
        hits = [
            t
            for t in trial_log
            if t["mode"] == "frequency"
            and t["question_id"] == q["id"]
            and t["gold_ok"] is True
        ]
        if hits:
            functional_hits += 1
    pass_latency = bool(speedup >= 1.15)
    pass_functional = functional_hits >= min(5, checked) if checked else True
    return {
        "pre_reg": "Docs/pre-reg/pre-reg-own-rag-demo.md",
        "model": model,
        "base_url": base_url,
        "k": k,
        "warm_trials": warm_trials,
        "n_questions": len(questions),
        "modes": results,
        "speedup_shuffled_over_frequency": speedup,
        "pass_heuristic": pass_latency,
        "pass_functional": pass_functional,
        "functional_gold_hits": functional_hits,
        "functional_gold_checked": checked,
        "pass_bar": "warm p50 shuffled/frequency >= 1.15",
        "trials": trial_log,
        "prewarm_observations": prewarm_observations,
        "note": (
            "Demo corpus ≠ partner traffic. "
            "Requires vLLM --enable-prefix-caching and cw-serve-order upstream."
        ),
    }


def _docs_for_mode(
    mode: str,
    documents: list[dict[str, str]],
    rng: random.Random,
) -> list[dict[str, str]]:
    docs = deepcopy(documents)
    if mode == "shuffled":
        rng.shuffle(docs)
    return docs


def dry_build_report(
    *,
    index: LexicalIndex,
    questions: list[dict[str, Any]],
    model: str,
    k: int = 3,
    seed: int = 7,
) -> dict[str, Any]:
    rng = random.Random(seed)
    q = questions[0]
    docs = retrieve(index, q["question"], k=k)
    return {
        "dry_build": {
            mode: build_mode_payload(
                mode, question=q["question"], documents=docs, model=model, rng=rng
            )
            for mode in ("shuffled", "frequency")
        },
        "retrieved_ids": [d["document_id"] for d in docs],
        "question_id": q["id"],
    }


def write_report(report: dict[str, Any], out: Path) -> None:
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
