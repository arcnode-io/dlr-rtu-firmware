"""Anemometer driver: sim sawtooth for now. Real Calypso ULP via I2C lands
once the carrier rev with the JST+I2C breakout exists.

Wind speed + direction. IEEE 738 needs both — wind perpendicular to the
conductor cools dramatically more than parallel.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.sensors.base import SawtoothSim

# Realistic transmission-tower outdoor wind ranges (0-25 m/s ~= 0-56 mph).
_WIND_SPEED_MIN_MPS = 0.0
_WIND_SPEED_MAX_MPS = 25.0
_WIND_SPEED_STEP_MPS = 1.0

# Direction sweeps 0-359 deg.
_WIND_DIR_MIN_DEG = 0.0
_WIND_DIR_MAX_DEG = 359.0
_WIND_DIR_STEP_DEG = 15.0


@dataclass(frozen=True)
class WindReading:
    """One anemometer sample: wind speed + direction relative to true north."""

    speed_mps: float
    direction_deg: float


class WindSim:
    """Sim anemometer: independent sawtooths for speed + direction."""

    def __init__(self) -> None:
        """Configure with outdoor-tower-deployment ranges."""
        self._speed = SawtoothSim(
            min_value=_WIND_SPEED_MIN_MPS,
            max_value=_WIND_SPEED_MAX_MPS,
            step=_WIND_SPEED_STEP_MPS,
        )
        self._direction = SawtoothSim(
            min_value=_WIND_DIR_MIN_DEG,
            max_value=_WIND_DIR_MAX_DEG,
            step=_WIND_DIR_STEP_DEG,
        )

    def read(self) -> WindReading:
        """Advance both sawtooths + return the current sample."""
        return WindReading(
            speed_mps=self._speed.read(),
            direction_deg=self._direction.read(),
        )


class WindConstant:
    """Fixed wind reading -- always the same speed + direction.

    Reason: same as `ConstantSim` -- holds this input steady during a demo
    where a different sensor is the live one.
    """

    def __init__(self, *, speed_mps: float, direction_deg: float) -> None:
        """Configure with the fixed reading every read() returns."""
        self._reading = WindReading(speed_mps=speed_mps, direction_deg=direction_deg)

    def read(self) -> WindReading:
        """Return the fixed reading -- never advances."""
        return self._reading
