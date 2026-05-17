"""DhtSim unit tests. DhtReal exercised by HIL tests on the Pi."""

from src.sensors.dht import DhtReading, DhtSim


def test_dht_sim_first_read_at_min_temp_and_min_humidity() -> None:
    """Sawtooths default to min_value -> known first sample."""
    sim = DhtSim()
    reading = sim.read()
    assert reading.temperature_c == 15.0
    assert reading.humidity_percent == 20.0


def test_dht_sim_temp_advances_independently_of_humidity() -> None:
    """Each axis has its own sawtooth -> independent steps."""
    sim = DhtSim()
    first = sim.read()
    second = sim.read()
    assert second.temperature_c == first.temperature_c + 0.5
    assert second.humidity_percent == first.humidity_percent + 1.0


def test_dht_sim_temp_wraps_at_max() -> None:
    """Temp sawtooth reaches max then wraps back to min."""
    sim = DhtSim()
    readings = [sim.read() for _ in range(42)]
    temps = [r.temperature_c for r in readings]
    assert min(temps) == 15.0
    assert max(temps) == 35.0  # max IS achievable; wrap happens on the next advance
    # readings[40] returns 35.0 (15 + 40*0.5), then advance makes 35.5 > 35 -> wrap.
    # readings[41] returns the wrapped value: 15.0.
    assert temps[40] == 35.0
    assert temps[41] == 15.0


def test_dht_reading_is_frozen() -> None:
    """DhtReading immutable so consumers can't tamper after read."""
    reading = DhtReading(temperature_c=20.0, humidity_percent=50.0)
    import pytest

    with pytest.raises((AttributeError, TypeError)):
        reading.temperature_c = 0.0  # ty: ignore[invalid-assignment]
