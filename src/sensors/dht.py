"""DHT22 driver: real adafruit_dht on Pi, deterministic sawtooth elsewhere.

DHT22 reads ambient temperature (degC) + relative humidity (percent). Real
hardware works on the Pi via GPIO; on dev / CI machines it raises at import
so we lazy-import it only when the real driver is constructed.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.sensors.base import SawtoothSim

# Reasonable ambient ranges for an outdoor transmission-tower deployment.
_AMBIENT_TEMP_MIN_C = 15.0
_AMBIENT_TEMP_MAX_C = 35.0
_AMBIENT_TEMP_STEP_C = 0.5

_HUMIDITY_MIN_PCT = 20.0
_HUMIDITY_MAX_PCT = 80.0
_HUMIDITY_STEP_PCT = 1.0


@dataclass(frozen=True)
class DhtReading:
    """One DHT22 sample: ambient temperature + relative humidity."""

    temperature_c: float
    humidity_percent: float


class DhtSim:
    """Sim DHT22: independent sawtooths for temp + humidity."""

    def __init__(self) -> None:
        """Configure with outdoor-tower-deployment ranges."""
        self._temp = SawtoothSim(
            min_value=_AMBIENT_TEMP_MIN_C,
            max_value=_AMBIENT_TEMP_MAX_C,
            step=_AMBIENT_TEMP_STEP_C,
        )
        self._humidity = SawtoothSim(
            min_value=_HUMIDITY_MIN_PCT,
            max_value=_HUMIDITY_MAX_PCT,
            step=_HUMIDITY_STEP_PCT,
        )

    def read(self) -> DhtReading:
        """Advance both sawtooths + return the current sample."""
        return DhtReading(
            temperature_c=self._temp.read(),
            humidity_percent=self._humidity.read(),
        )


class DhtReal:
    """Real DHT22 on the Pi via adafruit_dht. Constructs the GPIO handle
    lazily so `import dht` works on non-Pi machines as long as nobody
    actually instantiates this class.
    """

    def __init__(self, pin: int = 4) -> None:
        """Open the DHT22 on the given GPIO pin (default GPIO 4 / BCM)."""
        # Reason: lazy import — `board` + `adafruit_dht` require GPIO hardware
        # and fail at import on dev/CI machines.
        import adafruit_dht  # type: ignore[import-not-found]
        import board  # type: ignore[import-not-found]

        # Reason: use_pulseio=False forces the bit-bang read path. The default
        # (pulseio/libgpiod pulse capture) does not work on the Pi 5's RP1 GPIO —
        # every read returns "DHT sensor not found". Bit-bang via lgpio works.
        pin_attr = f"D{pin}"
        self._device = adafruit_dht.DHT22(getattr(board, pin_attr), use_pulseio=False)

    def read(self) -> DhtReading:
        """Read the DHT22. May raise RuntimeError on transient bus errors."""
        return DhtReading(
            temperature_c=self._device.temperature,
            humidity_percent=self._device.humidity,
        )
