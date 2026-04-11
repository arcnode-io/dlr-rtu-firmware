"""Temperature conversion client utilities."""

from .temperature_driver import TemperatureDriver


class TemperatureClient:
    """High-level temperature client that manages driver internally."""

    def __init__(self) -> None:
        """Initialize temperature client with driver."""
        self._driver = TemperatureDriver()

    def read_fahrenheit(self) -> float:
        """
        Read temperature from sensor and return Fahrenheit.

        Returns:
            Temperature in Fahrenheit
        """
        celsius = self._driver.read_celsius()
        return celsius_to_fahrenheit(celsius)


def celsius_to_fahrenheit(celsius: float) -> float:
    """
    Convert Celsius to Fahrenheit.

    Args:
        celsius: Temperature in Celsius

    Returns:
        Temperature in Fahrenheit
    """
    return (celsius * 9 / 5) + 32
