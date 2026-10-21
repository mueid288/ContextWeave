import pytest

from contextweave.runtime_adapters.base import NotAvailableOnCpu
from contextweave.runtime_adapters.registry import STRATEGIES, get_runner


def test_all_strategies_registered():
    for name in STRATEGIES:
        runner = get_runner(name)
        assert runner.name == name


def test_unknown_strategy_raises():
    """get_runner must reject unknown strategy names."""
    with pytest.raises(KeyError):
        get_runner("nonexistent_strategy")


def test_laptop_gets_cpu_stubs(monkeypatch: pytest.MonkeyPatch):
    """Without the allow flag, strategies stay NotAvailableOnCpu (no vLLM import)."""
    monkeypatch.delenv("CONTEXTWEAVE_ALLOW_MODEL_LOAD", raising=False)
    for name in ("full_prefill", "prefix_cache", "cacheblend", "epic", "smoke"):
        runner = get_runner(name)
        assert isinstance(runner, NotAvailableOnCpu)


def test_cacheblend_and_epic_remain_stubs_even_if_allow_set(
    monkeypatch: pytest.MonkeyPatch,
):
    """Live vLLM runners only cover full/prefix/smoke; CacheBlend/EPIC stay stubs."""
    monkeypatch.setenv("CONTEXTWEAVE_ALLOW_MODEL_LOAD", "1")
    # vLLM is not installed on the laptop — registry must still return stubs.
    assert isinstance(get_runner("cacheblend"), NotAvailableOnCpu)
    assert isinstance(get_runner("epic"), NotAvailableOnCpu)
