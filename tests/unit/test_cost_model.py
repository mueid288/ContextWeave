from contextweave.costmodel.breakeven import (
    ModelCostParams,
    breakeven_bandwidth_gb_s,
    corpus_storage_gb,
    evaluate_lengths,
    kv_bytes,
    max_tolerable_bailout_rate,
    prefill_time_s,
    repair_time_roofline_s,
)


def test_bytes_per_token_matches_prd_128kib():
    model = ModelCostParams()
    # 32 * 8 * 128 * 2 * 2 = 131072 bytes = 128 KiB
    assert model.bytes_per_token == 131072


def test_kv_size_10k_about_1_31_gb():
    model = ModelCostParams()
    gb = kv_bytes(10_000, model) / 1e9
    assert 1.25 < gb < 1.35


def test_breakeven_order_of_magnitude_prd():
    model = ModelCostParams()
    # PRD table: ~3.2 GB/s at 10k with no repair
    b0 = breakeven_bandwidth_gb_s(10_000, model, repair_fraction=0.0)
    b15_naive = breakeven_bandwidth_gb_s(
        10_000, model, repair_fraction=0.15, use_roofline_repair=False
    )
    b15_roof = breakeven_bandwidth_gb_s(
        10_000, model, repair_fraction=0.15, use_roofline_repair=True
    )
    assert 2.5 < b0 < 4.5
    assert 3.0 < b15_naive < 5.0
    assert b15_naive > b0
    # Roofline repair is costlier => less headroom => higher break-even bandwidth
    assert b15_roof >= b15_naive


def test_25gbe_loses_at_10k_serialized():
    rows = evaluate_lengths([10_000], repair_fraction=0.15)
    assert rows[0].wins_serialized["PCIe_5.0"]
    assert not rows[0].wins_serialized["25GbE"]


def test_million_tokens_storage():
    assert 120 < corpus_storage_gb(1_000_000) < 140


def test_prefill_grows_superlinear():
    model = ModelCostParams()
    t10 = prefill_time_s(10_000, model)
    t100 = prefill_time_s(100_000, model)
    assert t100 > 10 * t10  # attention term dominates


def test_roofline_repair_ge_naive():
    model = ModelCostParams()
    naive = 0.15 * prefill_time_s(32_000, model)
    roof = repair_time_roofline_s(32_000, model, repair_fraction=0.15)
    assert roof >= naive


def test_roofline_not_inflating_linear_by_efficiency():
    """15% repair must not approach 60% of full prefill (Gemini_2 §2.1 bug)."""
    model = ModelCostParams()
    t_prefill = prefill_time_s(100_000, model)
    roof = repair_time_roofline_s(100_000, model, repair_fraction=0.15)
    assert roof < 0.45 * t_prefill


def test_max_tolerable_bailout_rate():
    model = ModelCostParams()
    p = max_tolerable_bailout_rate(32_000, model, bandwidth_gb_s=50.0, alpha_load=0.15)
    assert 0.0 < p <= 1.0

