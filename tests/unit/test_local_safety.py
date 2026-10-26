import pytest

from contextweave.safety import (
    ModelLoadBlockedError,
    assert_model_load_allowed,
    get_heavy_imported_modules,
    model_loads_allowed,
)


def test_model_loads_blocked_by_default(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("CONTEXTWEAVE_ALLOW_MODEL_LOAD", raising=False)
    assert not model_loads_allowed()
    with pytest.raises(ModelLoadBlockedError, match="Refusing"):
        assert_model_load_allowed("unit-test action")


def test_no_heavy_ml_imports_in_product_surface():
    # Import package surface used on laptop; must not pull torch/vllm/etc.
    import contextweave.cli.analyze_trace  # noqa: F401
    import contextweave.cli.generate_workload  # noqa: F401
    import contextweave.cli.serve_order  # noqa: F401
    import contextweave.product  # noqa: F401
    import contextweave.trace_analysis  # noqa: F401
    import contextweave.workloads  # noqa: F401

    present = get_heavy_imported_modules()
    assert present == [], f"Heavy ML packages imported locally: {present}"
