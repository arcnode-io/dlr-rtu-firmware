"""SolarSim unit tests."""

from src.sensors.solar import SolarSim


def test_solar_sim_starts_at_night() -> None:
    """First read is 0 W/m^2 (night)."""
    sim = SolarSim()
    assert sim.read() == 0.0


def test_solar_sim_sweeps_to_peak_sun() -> None:
    """Sawtooth reaches 1000 W/m^2 peak, then wraps back to night (0)."""
    sim = SolarSim()
    readings = [sim.read() for _ in range(25)]
    assert max(readings) == 1000.0  # peak sun achieved before wrap
    assert min(readings) == 0.0
    # readings[20] = 0 + 20*50 = 1000; readings[21] wraps to 0.
    assert readings[20] == 1000.0
    assert readings[21] == 0.0
