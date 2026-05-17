"""Solar irradiance sensor: sim sawtooth for now.

Real driver lands when the SI1145 UV/Vis/IR sensor is wired up to the
carrier's I2C bus (already there for the existing breakout).
"""

from __future__ import annotations

from src.sensors.base import SawtoothSim

# Realistic daytime range: 0 W/m^2 (night/overcast) -> 1000 W/m^2 (peak sun).
_SOLAR_MIN_W_PER_M2 = 0.0
_SOLAR_MAX_W_PER_M2 = 1000.0
_SOLAR_STEP_W_PER_M2 = 50.0


class SolarSim:
    """Sim SI1145: sawtooth across the night-to-peak-sun range."""

    def __init__(self) -> None:
        """Configure with daytime irradiance sawtooth."""
        self._sawtooth = SawtoothSim(
            min_value=_SOLAR_MIN_W_PER_M2,
            max_value=_SOLAR_MAX_W_PER_M2,
            step=_SOLAR_STEP_W_PER_M2,
        )

    def read(self) -> float:
        """Solar irradiance in W/m^2."""
        return self._sawtooth.read()
