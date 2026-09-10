"""Unit tests for SawtoothSim — deterministic step + wrap behavior."""

import pytest

from src.sensors.base import ConstantSim, SawtoothSim


def test_sawtooth_starts_at_min_by_default() -> None:
    """No `start` arg -> first read returns min_value."""
    saw = SawtoothSim(min_value=0.0, max_value=10.0, step=1.0)
    assert saw.read() == 0.0


def test_sawtooth_advances_by_step_each_read() -> None:
    """Consecutive reads return min, min+step, min+2*step, ..."""
    saw = SawtoothSim(min_value=0.0, max_value=10.0, step=2.5)
    assert saw.read() == 0.0
    assert saw.read() == 2.5
    assert saw.read() == 5.0
    assert saw.read() == 7.5


def test_sawtooth_wraps_at_max() -> None:
    """When the next value would exceed max, wraps back to min."""
    saw = SawtoothSim(min_value=0.0, max_value=10.0, step=4.0)
    assert saw.read() == 0.0
    assert saw.read() == 4.0
    assert saw.read() == 8.0
    assert saw.read() == 0.0  # 8+4=12 > 10 -> wrap to 0


def test_sawtooth_honors_start_value() -> None:
    """Explicit start -> first read returns that value."""
    saw = SawtoothSim(min_value=0.0, max_value=100.0, step=10.0, start=50.0)
    assert saw.read() == 50.0
    assert saw.read() == 60.0


def test_sawtooth_rejects_inverted_bounds() -> None:
    """min >= max is a config bug — fail fast."""
    with pytest.raises(ValueError, match=r"must be < max_value"):
        SawtoothSim(min_value=10.0, max_value=10.0, step=1.0)


def test_sawtooth_rejects_non_positive_step() -> None:
    """A non-advancing or backward step never wraps — fail fast."""
    with pytest.raises(ValueError, match=r"step .* must be > 0"):
        SawtoothSim(min_value=0.0, max_value=10.0, step=0.0)
    with pytest.raises(ValueError, match=r"step .* must be > 0"):
        SawtoothSim(min_value=0.0, max_value=10.0, step=-1.0)


def test_constant_sim_returns_same_value_every_read() -> None:
    """No sweep -- always the configured value, unlike SawtoothSim."""
    const = ConstantSim(42.0)
    assert const.read() == 42.0
    assert const.read() == 42.0
    assert const.read() == 42.0
