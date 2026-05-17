"""SensorSuite factory tests."""

from build import Mode
from src.sensor_suite import build_sensor_suite
from src.sensors.dht import DhtSim


def test_local_mode_uses_sim_dht() -> None:
    """Local mode -> sim drivers everywhere (no hardware available)."""
    suite = build_sensor_suite(Mode.LOCAL)
    assert isinstance(suite.dht, DhtSim)


def test_ci_mode_uses_sim_dht() -> None:
    """CI runner has no GPIO -> sim DHT."""
    suite = build_sensor_suite(Mode.CI)
    assert isinstance(suite.dht, DhtSim)


def test_suite_exposes_all_five_sensors() -> None:
    """Suite must wire all five physical sensors so the tick loop has them."""
    suite = build_sensor_suite(Mode.LOCAL)
    assert suite.dht is not None
    assert suite.conductor_temp is not None
    assert suite.solar is not None
    assert suite.rain is not None
    assert suite.wind is not None


def test_suite_readers_are_independently_advancing() -> None:
    """Two reads from each sensor return different values (sawtooths step)."""
    suite = build_sensor_suite(Mode.LOCAL)
    dht_first = suite.dht.read()
    dht_second = suite.dht.read()
    assert dht_first != dht_second

    solar_first = suite.solar.read()
    solar_second = suite.solar.read()
    assert solar_first != solar_second
