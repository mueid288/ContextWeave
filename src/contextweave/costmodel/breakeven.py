"""PRD §7.5 cost model and break-even bandwidth (planning estimates, CPU-only)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class ModelCostParams:
    """Dense decoder-only model assumptions for KV size and prefill FLOPs."""

    name: str = "dense-8b-gqa"
    params: float = 8e9  # P
    num_layers: int = 32  # L
    d_model: int = 4096
    num_kv_heads: int = 8  # H_kv
    head_dim: int = 128  # d_h
    bytes_per_scalar: float = 2.0  # bf16
    effective_tflops: float = 450.0  # assumed GPU effective TFLOP/s
    # HBM bandwidth for repair roofline (v2.1 amendment D). A100 ~2 TB/s class.
    hbm_bandwidth_gb_s: float = 2000.0
    kv_block_size: int = 16
    # Scattered repair does not sustain peak TFLOP/s (Gemini 2.3).
    # Effective efficiency vs dense prefill; lower => higher T_repair.
    repair_tflop_efficiency: float = 0.25

    @property
    def bytes_per_token(self) -> float:
        # S_KV / N = L * H_kv * d_h * 2 * b  (K and V)
        return (
            self.num_layers
            * self.num_kv_heads
            * self.head_dim
            * 2
            * self.bytes_per_scalar
        )


@dataclass
class LinkProfile:
    name: str
    bandwidth_gb_s: float


DEFAULT_LINKS: tuple[LinkProfile, ...] = (
    LinkProfile("PCIe_5.0", 50.0),
    LinkProfile("PCIe_4.0", 25.0),
    LinkProfile("100GbE", 11.0),
    LinkProfile("NVMe_Gen4", 6.0),
    LinkProfile("25GbE", 2.8),
)


@dataclass
class CostRow:
    n_tokens: int
    kv_bytes: float
    kv_gb: float
    t_prefill_s: float
    t_load_by_link_s: dict[str, float]
    breakeven_gb_s_no_repair: float
    breakeven_gb_s_with_repair: float
    repair_fraction: float
    t_repair_naive_s: float = 0.0
    t_repair_roofline_s: float = 0.0
    t_hbm_read_s: float = 0.0
    wins_serialized: dict[str, bool] = field(default_factory=dict)
    wins_serialized_roofline: dict[str, bool] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def kv_bytes(n_tokens: int, model: ModelCostParams) -> float:
    return n_tokens * model.bytes_per_token


def prefill_flops(n_tokens: int, model: ModelCostParams) -> float:
    """Approx causal prefill FLOPs: 2PN + 2 L N^2 d_model (PRD §7.5)."""
    n = float(n_tokens)
    return 2.0 * model.params * n + 2.0 * model.num_layers * (n**2) * model.d_model


def prefill_time_s(n_tokens: int, model: ModelCostParams) -> float:
    flops = prefill_flops(n_tokens, model)
    return flops / (model.effective_tflops * 1e12)


def load_time_s(n_tokens: int, bandwidth_gb_s: float, model: ModelCostParams) -> float:
    if bandwidth_gb_s <= 0:
        return float("inf")
    return kv_bytes(n_tokens, model) / (bandwidth_gb_s * 1e9)


def hbm_read_time_s(n_tokens: int, model: ModelCostParams) -> float:
    """Time to read full S_KV from HBM once (lower bound on sparse-repair attention)."""
    if model.hbm_bandwidth_gb_s <= 0:
        return float("inf")
    return kv_bytes(n_tokens, model) / (model.hbm_bandwidth_gb_s * 1e9)


def repair_time_roofline_s(
    n_tokens: int,
    model: ModelCostParams,
    *,
    repair_fraction: float,
) -> float:
    """
    v2.1 amendment D / Gemini_2 §2.1 / Gemini_3 §1.6:

    T_repair(r) ≈ T_linear(rN) + max(T_attn_compute_eff(rN→N), T_HBM_read(S_KV))

    Dense linear GEMMs over r·N tokens run near peak TFLOP/s (bounded by model-weight
    HBM read). Only ragged attention is scaled by 1/repair_tflop_efficiency.
    """
    if repair_fraction <= 0:
        return 0.0
    n = float(n_tokens)
    r_n = repair_fraction * n
    eff = max(model.repair_tflop_efficiency, 1e-6)

    # 1. Dense linear GEMMs over r*N tokens vs HBM model-weight read
    linear_flops = 2.0 * model.params * r_n
    t_linear_compute = linear_flops / (model.effective_tflops * 1e12)
    weight_bytes = model.params * model.bytes_per_scalar
    t_weight_hbm = weight_bytes / (model.hbm_bandwidth_gb_s * 1e9)
    t_linear = max(t_linear_compute, t_weight_hbm)

    # 2. Ragged attention: r*N queries attending to ~N keys (causal avg ~N/2 → use N upper)
    attn_flops = 2.0 * model.num_layers * r_n * n * model.d_model
    t_attn_compute = attn_flops / (eff * model.effective_tflops * 1e12)
    t_kv_hbm = hbm_read_time_s(n_tokens, model)

    return t_linear + max(t_attn_compute, t_kv_hbm)


def max_tolerable_bailout_rate(
    n_tokens: int,
    model: ModelCostParams,
    *,
    bandwidth_gb_s: float,
    repair_fraction: float = 0.15,
    alpha_load: float = 0.15,
    t_stage1_check_s: float = 0.0,
) -> float:
    """
    v2.1.1 §B: maximum Stage-1 bailout rate before routing slice to C0.

    p_bail^max = (T_prefill - T_reuse) /
                 (T_prefill - T_reuse + T_stage1 + α_load · T_load)
    where T_reuse = T_load + T_repair.
    """
    t_prefill = prefill_time_s(n_tokens, model)
    t_load = load_time_s(n_tokens, bandwidth_gb_s, model)
    t_repair = repair_time_roofline_s(n_tokens, model, repair_fraction=repair_fraction)
    t_reuse = t_load + t_repair
    numer = t_prefill - t_reuse
    if numer <= 0:
        return 0.0
    denom = numer + t_stage1_check_s + alpha_load * t_load
    if denom <= 0:
        return 0.0
    return numer / denom


def breakeven_bandwidth_gb_s(
    n_tokens: int,
    model: ModelCostParams,
    *,
    repair_fraction: float = 0.0,
    t_other_s: float = 0.0,
    use_roofline_repair: bool = True,
) -> float:
    """
    B* = S_KV / (T_prefill - T_repair - T_other) for fully serialized load.
    Returns GB/s. If denominator <= 0, reuse cannot win under these assumptions.
    """
    t_prefill = prefill_time_s(n_tokens, model)
    if repair_fraction <= 0:
        t_repair = 0.0
    elif use_roofline_repair:
        t_repair = repair_time_roofline_s(n_tokens, model, repair_fraction=repair_fraction)
    else:
        t_repair = repair_fraction * t_prefill
    denom = t_prefill - t_repair - t_other_s
    if denom <= 0:
        return float("inf")
    return (kv_bytes(n_tokens, model) / denom) / 1e9


def evaluate_lengths(
    lengths: list[int],
    model: ModelCostParams | None = None,
    *,
    repair_fraction: float = 0.15,
    links: tuple[LinkProfile, ...] = DEFAULT_LINKS,
) -> list[CostRow]:
    model = model or ModelCostParams()
    rows: list[CostRow] = []
    for n in lengths:
        kv = kv_bytes(n, model)
        t_prefill = prefill_time_s(n, model)
        loads = {link.name: load_time_s(n, link.bandwidth_gb_s, model) for link in links}
        t_repair_naive = repair_fraction * t_prefill
        t_hbm = hbm_read_time_s(n, model)
        t_repair_roof = repair_time_roofline_s(n, model, repair_fraction=repair_fraction)
        wins = {
            name: loads[name] + t_repair_naive < t_prefill
            for name in loads
        }
        wins_roof = {
            name: loads[name] + t_repair_roof < t_prefill
            for name in loads
        }
        rows.append(
            CostRow(
                n_tokens=n,
                kv_bytes=kv,
                kv_gb=kv / 1e9,
                t_prefill_s=t_prefill,
                t_load_by_link_s=loads,
                breakeven_gb_s_no_repair=breakeven_bandwidth_gb_s(
                    n, model, repair_fraction=0.0
                ),
                breakeven_gb_s_with_repair=breakeven_bandwidth_gb_s(
                    n, model, repair_fraction=repair_fraction, use_roofline_repair=True
                ),
                repair_fraction=repair_fraction,
                t_repair_naive_s=t_repair_naive,
                t_repair_roofline_s=t_repair_roof,
                t_hbm_read_s=t_hbm,
                wins_serialized=wins,
                wins_serialized_roofline=wins_roof,
            )
        )
    return rows


def corpus_storage_gb(num_cached_tokens: int, model: ModelCostParams | None = None) -> float:
    model = model or ModelCostParams()
    return kv_bytes(num_cached_tokens, model) / 1e9


def render_markdown(
    rows: list[CostRow],
    model: ModelCostParams,
    *,
    links: tuple[LinkProfile, ...] = DEFAULT_LINKS,
) -> str:
    if not rows:
        return "No lengths to evaluate.\n"
    link_names = [l.name for l in links]
    header = (
        "| Context N | KV size | Est. full prefill | "
        + " | ".join(link_names)
        + " | Break-even GB/s (0% / "
        + f"{rows[0].repair_fraction:.0%} repair)"
        + " |"
    )
    sep = "|" + "|".join(["---"] * (3 + len(link_names) + 1)) + "|"
    lines = [
        "# Cost model — PRD §7.5 (planning estimates)",
        "",
        "**CPU-only. Not a measurement.** Overlap (pipelined load/recompute) would improve reuse further.",
        "",
        f"- Model: `{model.name}` P={model.params:.2e}, L={model.num_layers}, "
        f"d_model={model.d_model}, H_kv={model.num_kv_heads}, d_h={model.head_dim}",
        f"- KV dtype bytes/scalar: {model.bytes_per_scalar} → "
        f"**{model.bytes_per_token / 1024:.0f} KiB/token**",
        f"- Assumed effective compute: {model.effective_tflops} TFLOP/s",
        f"- Assumed HBM bandwidth: {model.hbm_bandwidth_gb_s:.0f} GB/s (repair roofline)",
        f"- KV block size (alignment): {model.kv_block_size}",
        f"- Repair fraction r={rows[0].repair_fraction:.0%} — **roofline** used for break-even "
        f"(naive r×T_prefill shown for contrast)",
        f"- Storage: 1e6 cached tokens ≈ **{corpus_storage_gb(1_000_000, model):.1f} GB**",
        "",
        header,
        sep,
    ]
    for r in rows:
        load_cells = " | ".join(f"{r.t_load_by_link_s[n]:.2f} s" for n in link_names)
        lines.append(
            f"| {r.n_tokens:,} | {r.kv_gb:.2f} GB | {r.t_prefill_s:.2f} s | {load_cells} | "
            f"{r.breakeven_gb_s_no_repair:.1f} / {r.breakeven_gb_s_with_repair:.1f} |"
        )
    lines.extend(
        [
            "",
            "## Repair time: naive vs HBM roofline (v2.1)",
            "",
            "| N | Naive r×T_prefill | HBM read S_KV | Roofline T_repair |",
            "|---|---|---|---|",
        ]
    )
    for r in rows:
        lines.append(
            f"| {r.n_tokens:,} | {r.t_repair_naive_s:.3f} s | {r.t_hbm_read_s:.4f} s | "
            f"{r.t_repair_roofline_s:.3f} s |"
        )
    lines.extend(
        [
            "",
            "## Serialized win matrix (load + **roofline** repair < prefill)",
            "",
        ]
    )
    for r in rows:
        winners = [k for k, v in r.wins_serialized_roofline.items() if v]
        losers = [k for k, v in r.wins_serialized_roofline.items() if not v]
        lines.append(
            f"- N={r.n_tokens:,}: wins on {', '.join(winners) or 'none'}; "
            f"loses on {', '.join(losers) or 'none'}"
        )
    lines.extend(
        [
            "",
            "## Implications (PRD + v2.1)",
            "",
            "- Host memory / fast PCIe often clear the load bar; **scattered repair** may still "
            "be HBM-bound and erase naive TFLOP savings.",
            "- Short contexts over slow links (e.g. 25 GbE at 10k) can lose if load is serialized.",
            "- Chunk lengths should be multiples of `kv_block_size` (pad/mask tails).",
            "- Corpus storage, not just per-request TTFT, drives cost.",
            "- Confirm with measurement when a GPU is available; do not treat these as G1 results.",
            "",
        ]
    )
    return "\n".join(lines)
