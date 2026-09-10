"""WindSim unit tests."""

from src.sensors.anemometer import WindConstant, WindSim


def test_wind_sim_first_read_at_zero_wind_north() -> None:
    """Sawtooths default to min_value -> 0 m/s, 0 deg (true north)."""
    sim = WindSim()
    reading = sim.read()
    assert reading.speed_mps == 0.0
    assert reading.direction_deg == 0.0


def test_wind_sim_speed_advances_each_read() -> None:
    """Speed sawtooth steps 1 m/s per read."""
    sim = WindSim()
    sim.read()
    second = sim.read()
    assert second.speed_mps == 1.0


def test_wind_sim_direction_advances_each_read() -> None:
    """Direction sawtooth steps 15 deg per read."""
    sim = WindSim()
    sim.read()
    second = sim.read()
    assert second.direction_deg == 15.0


def test_wind_sim_direction_stays_within_compass_range() -> None:
    """Direction must wrap before exceeding 360 deg."""
    sim = WindSim()
    readings = [sim.read() for _ in range(30)]
    directions = [r.direction_deg for r in readings]
    assert max(directions) < 360.0
    assert min(directions) >= 0.0


def test_wind_constant_returns_same_reading_every_read() -> None:
    """No sweep -- always the configured speed + direction."""
    const = WindConstant(speed_mps=3.0, direction_deg=90.0)
    first = const.read()
    second = const.read()
    assert first.speed_mps == 3.0
    assert first.direction_deg == 90.0
    assert second.speed_mps == 3.0
    assert second.direction_deg == 90.0
