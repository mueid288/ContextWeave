import pytest

from contextweave.runtime_adapters.registry import STRATEGIES, get_runner


def test_all_strategies_registered():
    for name in STRATEGIES:
        runner = get_runner(name)
        assert runner.name == name


def test_unknown_strategy_raises():
    """get_runner must reject unknown strategy names."""
    with pytest.raises(KeyError):
        get_runner("nonexistent_strategy")
