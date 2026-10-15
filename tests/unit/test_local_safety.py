import os

import pytest

from contextweave.runtime_adapters.registry import get_runner
from contextweave.safety import (
    ModelLoadBlockedError,
    assert_model_load_allowed,
    model_loads_allowed,
)
try:
    from contextweave.safety import get_heavy_imported_modules
except ImportError:
    from contextweave.safety import assert_heavy_imports_absent as get_heavy_imported_modules


def test_model_loads_blocked_by_default(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("CONTEXTWEAVE_ALLOW_MODEL_LOAD", raising=False)
    assert not model_loads_allowed()
    with pytest.raises(ModelLoadBlockedError, match="Refusing"):
        assert_model_load_allowed("unit-test action")


def test_baseline_setup_blocked_without_allow(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("CONTEXTWEAVE_ALLOW_MODEL_LOAD", raising=False)
    runner = get_runner("smoke")
    with pytest.raises(ModelLoadBlockedError):
        runner.setup()


def test_allow_flag_reaches_missing_impl(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("CONTEXTWEAVE_ALLOW_MODEL_LOAD", "1")
    runner = get_runner("smoke")
    with pytest.raises(RuntimeError, match="no local implementation"):
        runner.setup()


def test_no_heavy_ml_imports_in_harness():
    # Import package surface used on laptop; must not pull torch/vllm/etc.
    import contextweave.cli.analyze_trace  # noqa: F401
    import contextweave.cli.generate_workload  # noqa: F401
    import contextweave.runtime_adapters.registry  # noqa: F401
    import contextweave.trace_analysis  # noqa: F401
    import contextweave.workloads  # noqa: F401

    present = get_heavy_imported_modules()
    assert present == [], f"Heavy ML packages imported locally: {present}"
