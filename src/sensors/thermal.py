"""Conductor temperature sensor: sim sawtooth for now.

Real driver lands when the FLIR Lepton thermal camera is wired up to the
carrier's SPI bus and we have an image-to-spot-temperature model trained on
the conductor view.
"""

from __future__ import annotations

from src.sensors.base import SawtoothSim

# Conductor design max ~ 90-100 degC for ACSR. Sim sweep 20-95 covers the
# operational band including hot-summer + heavy-load conditions.
_CONDUCTOR_TEMP_MIN_C = 20.0
_CONDUCTOR_TEMP_MAX_C = 95.0
_CONDUCTOR_TEMP_STEP_C = 2.5


class ConductorTempSim:
    """Sim FLIR Lepton: sawtooth between cold-line and at-design-max."""

    def __init__(self) -> None:
        """Configure with operational-band sawtooth."""
        self._sawtooth = SawtoothSim(
            min_value=_CONDUCTOR_TEMP_MIN_C,
            max_value=_CONDUCTOR_TEMP_MAX_C,
            step=_CONDUCTOR_TEMP_STEP_C,
        )

    def read(self) -> float:
        """Conductor temperature in degC."""
        return self._sawtooth.read()
