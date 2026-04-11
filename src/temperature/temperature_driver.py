"""Temperature driver implementations."""


class TemperatureDriver:
    """Generic temperature sensor driver (DHT22 implementation)."""

    def __init__(self, gpio_pin: str = "D4") -> None:
        """
        Initialize temperature sensor driver.

        Args:
            gpio_pin: GPIO pin designation (e.g., "D4" for GPIO 4)
        """
        # Lazy import hardware-specific modules only when driver is instantiated
        import adafruit_dht
        import board

        pin = getattr(board, gpio_pin)
        self._dht = adafruit_dht.DHT22(pin, use_pulseio=False)

    def read_celsius(self) -> float:
        """
        Read temperature from sensor in Celsius.

        Returns:
            Temperature in degrees Celsius
        """
        return float(self._dht.temperature)
