from .temperature_client import celsius_to_fahrenheit


def test_convert_celsius_to_fahrenheit() -> None:
    """Test conversion from Celsius to Fahrenheit."""
    # Arrange & Act & Assert
    assert celsius_to_fahrenheit(0.0) == 32.0
    assert celsius_to_fahrenheit(100.0) == 212.0
