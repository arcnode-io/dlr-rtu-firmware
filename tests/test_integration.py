"""Integration tests. Validates sensor hardware. Uses pytest-xdist to run on device."""

from src.temperature.temperature_client import TemperatureClient


def test_temperature_sensor() -> None:
    """
    Test temperature sensor reads valid Fahrenheit values.

    Validates temperature sensor can communicate and return reasonable readings.
    Checks that readings are within expected range and consistent across multiple reads.
    """
    # Arrange - Initialize real hardware client
    client = TemperatureClient()

    # Act - Read temperature
    fahrenheit = client.read_fahrenheit()

    # Assert - Temperature is in reasonable range (50-104°F)
    assert 50.0 <= fahrenheit <= 104.0

    # Act - Read again for consistency check
    fahrenheit2 = client.read_fahrenheit()

    # Assert - Readings are consistent (within 9°F tolerance)
    diff = abs(fahrenheit - fahrenheit2)
    assert diff < 9.0
