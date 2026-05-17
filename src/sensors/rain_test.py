"""RainSim unit tests."""

from src.sensors.rain import RainSim


def test_rain_sim_oscillates_dry_wet() -> None:
    """3-tick cycle (0.0, 0.5, 1.0): only the third tick reads True."""
    sim = RainSim()
    cycle = [sim.read() for _ in range(6)]
    # 0.0 -> False; 0.5 -> False (not > 0.5); 1.0 -> True; wrap -> repeat
    assert cycle == [False, False, True, False, False, True]
