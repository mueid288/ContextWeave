"""Section 2.2 demand metrics and Gate G0 evaluation."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable
import json
import math
import statistics

from contextweave.tokenization.boundaries import ChunkingConfig, canonicalize_segment_tokens
from contextweave.trace_analysis.hashing import hash_token_ids
from contextweave.trace_analysis.prefix_cache import PrefixCacheSimulator
from contextweave.trace_analysis.working_set import (
    WorkingSetConfig,
    WorkingSetMetrics,
    simulate_working_set,
)

# Default GPU HBM leftover for native prefix cache (~24 GB @ 128 KiB/token).
DEFAULT_PREFIX_CACHE_BUDGET_GB = 24.0
DEFAULT_BYTES_PER_TOKEN = 131072.0


@dataclass
class DemandMetrics:
    """Metrics from PRD Section 2.2 for Gate G0."""

    num_requests: int = 0
    total_prefill_tokens: int = 0
    prefix_cached_tokens: int = 0
    post_prefix_prefill_tokens: int = 0
    uncovered_prefix_tokens: int = 0
    recurring_non_prefix_tokens: int = 0
    unique_first_seen_chunk_tokens: int = 0
    query_tokens: int = 0

    # Distributions
    chunk_lengths: list[int] = field(default_factory=list)
    context_lengths: list[int] = field(default_factory=list)
    reuse_distances: list[int] = field(default_factory=list)
    chunk_popularity: dict[str, int] = field(default_factory=dict)

    lookup_requests: int = 0
    synthesis_requests: int = 0

    context_buckets: dict[str, int] = field(default_factory=dict)

    working_set: WorkingSetMetrics | None = None
    prefix_cache_budget_tokens: int | None = None
    prefix_cache_evictions: int = 0

    @property
    def share_prefix_cached(self) -> float:
        if self.total_prefill_tokens == 0:
            return 0.0
        return self.prefix_cached_tokens / self.total_prefill_tokens

    @property
    def share_recurring_non_prefix(self) -> float:
        """Share of *post-prefix-cache* prefill tokens that are recurring non-prefix chunks."""
        if self.post_prefix_prefill_tokens == 0:
            return 0.0
        return self.recurring_non_prefix_tokens / self.post_prefix_prefill_tokens

    @property
    def median_chunk_length(self) -> float:
        if not self.chunk_lengths:
            return 0.0
        return float(statistics.median(self.chunk_lengths))

    @property
    def synthesis_fraction(self) -> float:
        if self.num_requests == 0:
            return 0.0
        return self.synthesis_requests / self.num_requests

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["share_prefix_cached"] = self.share_prefix_cached
        d["share_recurring_non_prefix"] = self.share_recurring_non_prefix
        d["median_chunk_length"] = self.median_chunk_length
        d["synthesis_fraction"] = self.synthesis_fraction
        d["frac_requests_above_8k"] = _frac_above(self.context_lengths, 8000)
        d["frac_requests_above_32k"] = _frac_above(self.context_lengths, 32000)
        d["frac_requests_above_100k"] = _frac_above(self.context_lengths, 100000)
        if self.working_set is not None:
            d["working_set"] = self.working_set.to_dict()
        return d


@dataclass
class G0Result:
    passed: bool
    provisional: bool
    share_recurring_non_prefix: float
    median_chunk_length: float
    threshold_share: float
    threshold_median_chunk: float
    rationale: str
    working_set_hit_share: float | None = None
    working_set_budget_gb: float | None = None
    require_working_set: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _frac_above(values: list[int], threshold: int) -> float:
    if not values:
        return 0.0
    return sum(1 for v in values if v >= threshold) / len(values)


def _context_bucket(n: int) -> str:
    if n < 8000:
        return "<8k"
    if n < 32000:
        return "8k-32k"
    if n < 100000:
        return "32k-100k"
    return ">=100k"


def _chunk_key(token_ids: list[int]) -> str:
    if not token_ids:
        return "empty"
    return f"len={len(token_ids)}:{hash_token_ids(token_ids)}"


def iter_trace(path: Path) -> Iterable[dict[str, Any]]:
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)


def _canonical_segments(
    row: dict[str, Any],
    *,
    chunking: ChunkingConfig | None,
) -> tuple[list[int], list[list[int]], list[int]]:
    """
    Prefer stored token_ids when present; otherwise assemble with boundary-before-pad.

    When chunking is set and row lacks `segments_canonical`, re-canonicalize raw
    prefix/chunks so cursor lengths match assembled prompts.
    """
    prefix_ids = list(row.get("prefix_token_ids") or [])
    chunks = [list(c) for c in (row.get("chunk_token_ids") or [])]
    query_ids = list(row.get("query_token_ids") or [])
    token_ids = list(row.get("token_ids") or [])

    if row.get("segments_canonical") or chunking is None:
        return token_ids, chunks, prefix_ids

    cfg = chunking
    canon_prefix = (
        canonicalize_segment_tokens(prefix_ids, cfg, append_boundary=bool(chunks or query_ids))
        if prefix_ids
        else []
    )
    canon_chunks = [
        canonicalize_segment_tokens(c, cfg, append_boundary=True) for c in chunks
    ]
    assembled = list(canon_prefix)
    for body in canon_chunks:
        assembled.extend(body)
    assembled.extend(query_ids)
    return assembled, canon_chunks, canon_prefix


# Sentinel: callers that omit working_set_cfg get the v2.1 default 128 GB budget.
# Pass working_set_cfg=None to disable the simulation entirely.
_DEFAULT_WORKING_SET = object()


def analyze_rows(
    rows: Iterable[dict[str, Any]],
    *,
    working_set_cfg: WorkingSetConfig | None | object = _DEFAULT_WORKING_SET,
    prefix_cache_budget_gb: float | None = DEFAULT_PREFIX_CACHE_BUDGET_GB,
    bytes_per_token: float = DEFAULT_BYTES_PER_TOKEN,
    chunking: ChunkingConfig | None = None,
) -> DemandMetrics:
    """Analyze an in-memory iterable of canonical request rows."""
    metrics = DemandMetrics()
    budget_tokens: int | None = None
    if prefix_cache_budget_gb is not None and prefix_cache_budget_gb > 0:
        budget_tokens = max(1, int(prefix_cache_budget_gb * 1e9 / bytes_per_token))
    metrics.prefix_cache_budget_tokens = budget_tokens
    cache = PrefixCacheSimulator(budget_tokens=budget_tokens)

    last_seen: dict[str, int] = {}
    seen_chunks: set[str] = set()
    ws_events: list[tuple[str, int, int]] = []

    # Default working-set budget when caller omits the arg (v2.1 §G / Gemini_3 §1.5).
    # Explicit None disables the simulation (CLI --cache-budget-gb 0).
    if working_set_cfg is _DEFAULT_WORKING_SET:
        working_set_cfg = WorkingSetConfig.from_gb(128.0, bytes_per_token)

    for idx, row in enumerate(rows):
        metrics.num_requests += 1
        query_type = row.get("query_type", "lookup")
        doc_ids = row.get("document_ids") or []

        token_ids, chunks, prefix_ids = _canonical_segments(row, chunking=chunking)
        query_ids = list(row.get("query_token_ids") or [])
        if not doc_ids:
            doc_ids = [f"chunk-{i}" for i in range(len(chunks))]

        if query_type == "synthesis":
            metrics.synthesis_requests += 1
        else:
            metrics.lookup_requests += 1

        ctx_len = len(token_ids)
        metrics.context_lengths.append(ctx_len)
        bucket = _context_bucket(ctx_len)
        metrics.context_buckets[bucket] = metrics.context_buckets.get(bucket, 0) + 1

        hit = cache.lookup(token_ids)
        prefix_hit_tokens = hit.matched_tokens
        metrics.total_prefill_tokens += ctx_len
        metrics.prefix_cached_tokens += prefix_hit_tokens
        post_prefix = ctx_len - prefix_hit_tokens
        metrics.post_prefix_prefill_tokens += post_prefix

        prefix_len = len(prefix_ids)
        uncovered_prefix = max(0, prefix_len - prefix_hit_tokens)
        metrics.uncovered_prefix_tokens += uncovered_prefix

        cursor = prefix_len
        for doc_id, chunk in zip(doc_ids, chunks, strict=True):
            clen = len(chunk)
            metrics.chunk_lengths.append(clen)
            metrics.chunk_popularity[doc_id] = metrics.chunk_popularity.get(doc_id, 0) + 1
            key = _chunk_key(chunk)

            chunk_start = cursor
            chunk_end = cursor + clen
            uncovered = max(0, chunk_end - max(chunk_start, prefix_hit_tokens))
            if key in seen_chunks:
                metrics.recurring_non_prefix_tokens += uncovered
                prev = last_seen[key]
                metrics.reuse_distances.append(idx - prev)
            else:
                metrics.unique_first_seen_chunk_tokens += uncovered
                seen_chunks.add(key)
            last_seen[key] = idx
            if uncovered > 0:
                ws_events.append((key, clen, uncovered))
            cursor = chunk_end

        q_start = cursor
        q_end = q_start + len(query_ids)
        uncovered_q = max(0, q_end - max(q_start, prefix_hit_tokens))
        metrics.query_tokens += uncovered_q

        cache.insert(token_ids)

    metrics.prefix_cache_evictions = cache.evictions

    if working_set_cfg is not None:
        metrics.working_set = simulate_working_set(
            ws_events,
            working_set_cfg,
            post_prefix_prefill_tokens=metrics.post_prefix_prefill_tokens,
        )

    return metrics


def analyze_trace(
    path: Path,
    *,
    working_set_cfg: WorkingSetConfig | None | object = _DEFAULT_WORKING_SET,
    prefix_cache_budget_gb: float | None = DEFAULT_PREFIX_CACHE_BUDGET_GB,
    bytes_per_token: float = DEFAULT_BYTES_PER_TOKEN,
    chunking: ChunkingConfig | None = None,
    chunk_order: str = "natural",
) -> DemandMetrics:
    """
    Analyze a JSONL trace.

    Expected fields per request (synthetic generator output):
      - token_ids: full prompt
      - prefix_token_ids: system/instruction prefix
      - chunk_token_ids: list of document chunks
      - chunk_lengths / document_ids
      - query_token_ids
      - query_type: lookup | synthesis

    ``chunk_order``: natural | by_doc_id | by_sha256_doc_id | by_frequency_desc
    """
    from contextweave.trace_analysis.chunk_order import (
        build_doc_frequency,
        reorder_chunks,
    )

    rows = list(iter_trace(path))
    freq = build_doc_frequency(rows) if chunk_order == "by_frequency_desc" else None
    ordered = [
        reorder_chunks(r, chunk_order, freq=freq)  # type: ignore[arg-type]
        for r in rows
    ]
    return analyze_rows(
        ordered,
        working_set_cfg=working_set_cfg,
        prefix_cache_budget_gb=prefix_cache_budget_gb,
        bytes_per_token=bytes_per_token,
        chunking=chunking,
    )


def _kpi_payload(metrics: DemandMetrics) -> dict[str, Any]:
    ws = metrics.working_set
    return {
        "num_requests": metrics.num_requests,
        "share_prefix_cached": metrics.share_prefix_cached,
        "prefix_cached_tokens": metrics.prefix_cached_tokens,
        "total_prefill_tokens": metrics.total_prefill_tokens,
        "post_prefix_prefill_tokens": metrics.post_prefix_prefill_tokens,
        "share_recurring_non_prefix": metrics.share_recurring_non_prefix,
        "working_set_hit_share": (
            None if ws is None else ws.hit_share_of_post_prefix
        ),
    }


def compare_chunk_orders(
    path: Path,
    *,
    modes: tuple[str, ...] | None = None,
    working_set_cfg: WorkingSetConfig | None | object = _DEFAULT_WORKING_SET,
    prefix_cache_budget_gb: float | None = DEFAULT_PREFIX_CACHE_BUDGET_GB,
    bytes_per_token: float = DEFAULT_BYTES_PER_TOKEN,
) -> dict[str, Any]:
    """A/B chunk-order modes; primary KPI is share_prefix_cached (not G0 PASS)."""
    from contextweave.trace_analysis.chunk_order import (
        CHUNK_ORDER_MODES,
        build_doc_frequency,
        reorder_chunks,
    )

    modes = modes or CHUNK_ORDER_MODES
    rows = list(iter_trace(path))
    freq = build_doc_frequency(rows)
    multi = [r for r in rows if len(r.get("chunk_token_ids") or []) >= 2]

    def _run(subset: list[dict[str, Any]], mode: str) -> dict[str, Any]:
        ordered = [
            reorder_chunks(r, mode, freq=freq)  # type: ignore[arg-type]
            for r in subset
        ]
        m = analyze_rows(
            ordered,
            working_set_cfg=working_set_cfg,
            prefix_cache_budget_gb=prefix_cache_budget_gb,
            bytes_per_token=bytes_per_token,
        )
        return _kpi_payload(m)

    overall: dict[str, Any] = {}
    multi_doc: dict[str, Any] = {}
    for mode in modes:
        overall[mode] = _run(rows, mode)
        multi_doc[mode] = _run(multi, mode) if multi else _kpi_payload(DemandMetrics())

    natural_pp = overall["natural"]["post_prefix_prefill_tokens"]
    natural_share = overall["natural"]["share_prefix_cached"]
    natural_multi_pp = multi_doc["natural"]["post_prefix_prefill_tokens"]
    natural_multi_share = multi_doc["natural"]["share_prefix_cached"]

    deltas: dict[str, Any] = {}
    for mode in modes:
        if mode == "natural":
            continue
        o = overall[mode]
        md = multi_doc[mode]
        deltas[mode] = {
            "overall_share_prefix_cached_pp": (o["share_prefix_cached"] - natural_share)
            * 100.0,
            "overall_post_prefix_reduction_pct": (
                0.0
                if natural_pp == 0
                else (1.0 - o["post_prefix_prefill_tokens"] / natural_pp) * 100.0
            ),
            "multi_doc_share_prefix_cached_pp": (
                md["share_prefix_cached"] - natural_multi_share
            )
            * 100.0,
            "multi_doc_post_prefix_reduction_pct": (
                0.0
                if natural_multi_pp == 0
                else (1.0 - md["post_prefix_prefill_tokens"] / natural_multi_pp) * 100.0
            ),
            "note_recurrence": (
                "Recurrence absorbed into native prefix cache (C1)"
                if o["share_recurring_non_prefix"]
                < overall["natural"]["share_recurring_non_prefix"]
                else None
            ),
        }

    # Pre-reg bar on by_frequency_desc
    freq_d = deltas.get("by_frequency_desc", {})
    pass_heuristic = bool(
        freq_d.get("overall_share_prefix_cached_pp", 0) >= 10.0
        or freq_d.get("multi_doc_share_prefix_cached_pp", 0) >= 10.0
        or freq_d.get("multi_doc_post_prefix_reduction_pct", 0) >= 20.0
    )

    return {
        "trace": str(path),
        "n_requests": len(rows),
        "n_multi_doc": len(multi),
        "overall": overall,
        "multi_doc": multi_doc,
        "deltas_vs_natural": deltas,
        "pass_heuristic_frequency": pass_heuristic,
        "pass_bar": (
            "by_frequency_desc: ≥+10pp share_prefix_cached (overall or multi-doc) "
            "OR ≥20% multi-doc post_prefix reduction"
        ),
    }


def evaluate_g0(
    metrics: DemandMetrics,
    *,
    threshold_share: float = 0.30,
    threshold_median_chunk: float = 512.0,
    provisional: bool = True,
    require_working_set: bool = True,
    threshold_working_set_share: float = 0.30,
) -> G0Result:
    share = metrics.share_recurring_non_prefix
    median = metrics.median_chunk_length
    # Decision metric uses same denominator as unconstrained share (Gemini_2 §1.1).
    ws_share = (
        metrics.working_set.hit_share_of_post_prefix
        if metrics.working_set is not None
        else None
    )
    ws_budget = metrics.working_set.budget_gb if metrics.working_set is not None else None

    passed = share >= threshold_share and median >= threshold_median_chunk
    reasons: list[str] = []
    if share < threshold_share:
        reasons.append(f"unconstrained share {share:.1%} < {threshold_share:.0%}")
    if median < threshold_median_chunk:
        reasons.append(f"median chunk {median:.0f} < {threshold_median_chunk:.0f}")

    if require_working_set:
        if ws_share is None:
            passed = False
            reasons.append("working-set simulation required but missing")
        elif ws_share < threshold_working_set_share:
            passed = False
            reasons.append(
                f"working-set hit share {ws_share:.1%} < {threshold_working_set_share:.0%} "
                f"(budget={ws_budget:.0f} GB)"
            )

    if passed and not reasons:
        parts = [
            f"unconstrained recurring non-prefix={share:.1%} (≥{threshold_share:.0%})",
            f"median chunk={median:.0f} (≥{threshold_median_chunk:.0f})",
        ]
        if ws_share is not None:
            parts.append(
                f"LRU hit share={ws_share:.1%} @ {ws_budget:.0f} GB"
                + (
                    f" (≥{threshold_working_set_share:.0%} required)"
                    if require_working_set
                    else " (informational)"
                )
            )
        rationale = f"G0 PASS: {'; '.join(parts)}."
    else:
        rationale = "G0 FAIL: " + "; ".join(reasons) + "."

    if provisional:
        rationale += " Marked provisional."
    return G0Result(
        passed=passed,
        provisional=provisional,
        share_recurring_non_prefix=share,
        median_chunk_length=median,
        threshold_share=threshold_share,
        threshold_median_chunk=threshold_median_chunk,
        rationale=rationale,
        working_set_hit_share=ws_share,
        working_set_budget_gb=ws_budget,
        require_working_set=require_working_set,
    )


def render_report(
    metrics: DemandMetrics,
    g0: G0Result,
    *,
    trace_path: Path,
    title: str = "Phase 0A Demand Analysis (Gate G0)",
) -> str:
    pop = sorted(metrics.chunk_popularity.items(), key=lambda x: -x[1])
    top = pop[:10]
    reuse = metrics.reuse_distances
    reuse_summary = "n/a"
    if reuse:
        reuse_summary = (
            f"median={statistics.median(reuse):.0f}, "
            f"p90={_percentile(reuse, 90):.0f}, "
            f"mean={statistics.mean(reuse):.1f}"
        )

    accounted = (
        metrics.uncovered_prefix_tokens
        + metrics.recurring_non_prefix_tokens
        + metrics.unique_first_seen_chunk_tokens
        + metrics.query_tokens
    )

    lines = [
        f"# {title}",
        "",
        f"- Trace: `{trace_path}`",
        f"- Requests: {metrics.num_requests}",
        f"- Provisional: **{g0.provisional}**",
        f"- Gate G0: **{'PASS' if g0.passed else 'FAIL'}**",
        f"- Rationale: {g0.rationale}",
        "",
        "## Section 2.2 metrics",
        "",
        f"| Metric | Value |",
        f"|---|---|",
        f"| Total prefill tokens | {metrics.total_prefill_tokens:,} |",
        f"| Served by native prefix cache | {metrics.prefix_cached_tokens:,} ({metrics.share_prefix_cached:.1%}) |",
        f"| Post-prefix prefill tokens | {metrics.post_prefix_prefill_tokens:,} |",
        f"| Cold / uncovered system-prefix tokens | {metrics.uncovered_prefix_tokens:,} |",
        f"| Recurring non-prefix tokens (unconstrained) | {metrics.recurring_non_prefix_tokens:,} ({metrics.share_recurring_non_prefix:.1%} of post-prefix) |",
        f"| First-seen chunk tokens (post-prefix) | {metrics.unique_first_seen_chunk_tokens:,} |",
        f"| Query tokens (post-prefix) | {metrics.query_tokens:,} |",
        f"| Post-prefix bucket sum (must match) | {accounted:,} |",
        f"| Median chunk length (tokens) | {metrics.median_chunk_length:.0f} |",
        f"| Synthesis request fraction | {metrics.synthesis_fraction:.1%} |",
        f"| Requests ≥8k / ≥32k / ≥100k | {_frac_above(metrics.context_lengths, 8000):.1%} / {_frac_above(metrics.context_lengths, 32000):.1%} / {_frac_above(metrics.context_lengths, 100000):.1%} |",
        f"| Reuse distance (requests) | {reuse_summary} |",
        "",
    ]
    if metrics.prefix_cache_budget_tokens is not None:
        lines.extend(
            [
                f"- Prefix-cache token budget: {metrics.prefix_cache_budget_tokens:,} "
                f"(evictions={metrics.prefix_cache_evictions})",
                "",
            ]
        )
    if metrics.working_set is not None:
        ws = metrics.working_set
        lines.extend(
            [
                "### Working-set constrained hits (v2.1 amendment G)",
                "",
                f"| Metric | Value |",
                f"|---|---|",
                f"| Cache budget | {ws.budget_gb:.1f} GB ({ws.policy.upper()}) |",
                f"| Bytes / token (KV) | {ws.bytes_per_token:,.0f} |",
                f"| Post-prefix prefill tokens (decision denom) | {ws.post_prefix_prefill_tokens:,} |",
                f"| Post-prefix chunk tokens (diagnostic) | {ws.post_prefix_chunk_tokens:,} |",
                f"| Hit tokens under budget | {ws.hit_tokens:,} ({ws.hit_share_of_post_prefix:.1%} of post-prefix) |",
                f"| Hit share of chunks only | {ws.hit_share_of_post_prefix_chunks:.1%} |",
                f"| Miss tokens | {ws.miss_tokens:,} |",
                f"| Evictions | {ws.evictions:,} |",
                f"| Peak resident | {ws.peak_bytes / 1e9:.2f} GB |",
                "",
            ]
        )
    lines.extend(
        [
            "### Context length buckets",
            "",
        ]
    )
    for k in ("<8k", "8k-32k", "32k-100k", ">=100k"):
        lines.append(f"- {k}: {metrics.context_buckets.get(k, 0)}")
    lines.extend(["", "### Top-10 document popularity", ""])
    for doc_id, count in top:
        lines.append(f"- `{doc_id}`: {count}")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "G0 thresholds (PRD v2 + v2.1): unconstrained recurring non-prefix ≥ 30% of "
            "post-prefix tokens; median chunk ≥ 512; and by default, LRU hit share under the "
            "declared GB budget also ≥ 30% (same post-prefix denominator).",
            "",
            "Unconstrained recurrence is an upper bound; working-set hits are the decision metric "
            "for achievable cache value. Replace Path C / synthetic traces with a serving log "
            "before treating G0 as final.",
            "",
        ]
    )
    return "\n".join(lines)


def _percentile(values: list[int], p: float) -> float:
    if not values:
        return math.nan
    s = sorted(values)
    k = (len(s) - 1) * (p / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return float(s[int(k)])
    return s[f] * (c - k) + s[c] * (k - f)
