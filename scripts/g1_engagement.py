"""Engagement / Gate R helpers for CacheBlend G1 (CPU-safe).

Gate R (reuse proven): on reorder, retrieved/cached tokens ≥ ``min_frac`` of
chunk tokens AND (optionally) TTFT below native reorder. Without engagement
stats, Gate R fails closed as ``ENGAGEMENT_UNKNOWN``.
"""

from __future__ import annotations

from typing import Any


DEFAULT_MIN_FRAC = 0.70


def extract_engagement(generate_outs: Any) -> dict[str, Any]:
    """Best-effort pull of cached/retrieved token counts from a vLLM generate result."""
    out: dict[str, Any] = {
        "num_cached_tokens": None,
        "num_computed_tokens": None,
        "source": None,
    }
    if not generate_outs:
        return out
    req = generate_outs[0]
    for attr in ("num_cached_tokens", "num_computed_tokens"):
        if hasattr(req, attr):
            val = getattr(req, attr)
            if val is not None:
                out[attr] = int(val)
                out["source"] = out["source"] or f"RequestOutput.{attr}"
    metrics = getattr(req, "metrics", None)
    if metrics is not None:
        for attr in ("cached_tokens", "num_cached_tokens", "prefix_cache_hits"):
            if hasattr(metrics, attr):
                val = getattr(metrics, attr)
                if val is not None and out["num_cached_tokens"] is None:
                    out["num_cached_tokens"] = int(val)
                    out["source"] = f"metrics.{attr}"
    # Some builds stash usage on the request.
    usage = getattr(req, "usage", None)
    if usage is not None:
        details = getattr(usage, "prompt_tokens_details", None)
        if details is not None and getattr(details, "cached_tokens", None) is not None:
            out["num_cached_tokens"] = int(details.cached_tokens)
            out["source"] = "usage.prompt_tokens_details.cached_tokens"
    return out


def gate_r(
    *,
    cached_or_retrieved_tokens: int | None,
    chunk_token_total: int,
    min_frac: float = DEFAULT_MIN_FRAC,
    ttft_ms: float | None = None,
    native_reorder_p50_ms: float | None = None,
    require_ttft_win: bool = False,
) -> dict[str, Any]:
    """Evaluate Gate R.

    ``chunk_token_total`` = sum of doc-chunk token lengths (exclude system/sep/q).
    """
    need = int(min_frac * chunk_token_total)
    if cached_or_retrieved_tokens is None:
        return {
            "gate_r_pass": False,
            "status": "ENGAGEMENT_UNKNOWN",
            "need_tokens": need,
            "got_tokens": None,
            "min_frac": min_frac,
            "ttft_win": None,
            "note": "No cached/retrieved token metric exposed; fail closed.",
        }
    reuse_ok = cached_or_retrieved_tokens >= need
    ttft_win = None
    if ttft_ms is not None and native_reorder_p50_ms is not None:
        ttft_win = ttft_ms < native_reorder_p50_ms
    pass_r = reuse_ok and (ttft_win if require_ttft_win else True)
    if not reuse_ok:
        status = "ENGAGEMENT_FAIL"
    elif require_ttft_win and not ttft_win:
        status = "REUSE_NO_TTFT_WIN"
    else:
        status = "REUSE_OK"
    return {
        "gate_r_pass": bool(pass_r),
        "status": status,
        "need_tokens": need,
        "got_tokens": int(cached_or_retrieved_tokens),
        "min_frac": min_frac,
        "ttft_win": ttft_win,
        "note": (
            "Gate R: retrieved/cached ≥ min_frac × chunk tokens"
            + (" and TTFT < native reorder" if require_ttft_win else "")
        ),
    }


def summarize_trial_engagement(trials: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate per-trial engagement dicts (each may include num_cached_tokens)."""
    vals = [
        t["num_cached_tokens"]
        for t in trials
        if t.get("num_cached_tokens") is not None
    ]
    return {
        "n_trials": len(trials),
        "n_with_metric": len(vals),
        "cached_tokens_p50": sorted(vals)[len(vals) // 2] if vals else None,
        "cached_tokens_min": min(vals) if vals else None,
        "cached_tokens_max": max(vals) if vals else None,
        "samples": vals,
    }
