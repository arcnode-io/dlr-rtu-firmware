"""ConductorTempSim unit tests."""

from src.sensors.thermal import ConductorTempSim


def test_conductor_temp_sim_starts_at_min_operational() -> None:
    """First read is the cold-line baseline (20 degC)."""
    sim = ConductorTempSim()
    assert sim.read() == 20.0


def test_conductor_temp_sim_sweeps_up_to_design_max() -> None:
    """Sawtooth reaches up to ~design-max 95 degC."""
    sim = ConductorTempSim()
    readings = [sim.read() for _ in range(40)]
    assert max(readings) <= 95.0
    assert max(readings) >= 90.0  # confirms we actually hit the upper band
