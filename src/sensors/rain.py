"""Rain sensor: sim sawtooth-as-toggle for now.

Real driver lands when the YL-83 analog rain sensor is wired up through the
existing ADS1115 ADC channel.
"""

from __future__ import annotations

from src.sensors.base import SawtoothSim


class RainSim:
    """Sim YL-83: boolean-shaped sawtooth (0/1) — alternates dry/wet each
    read so downstream code exercises both branches over time.
    """

    def __init__(self) -> None:
        """Configure with the 0/1 oscillator."""
        # Sawtooth 0.0 -> 0.5 -> 1.0 -> wrap (3-tick cycle: dry, half, wet).
        self._sawtooth = SawtoothSim(
            min_value=0.0,
            max_value=1.0,
            step=0.5,
        )

    def read(self) -> bool:
        """True when raining."""
        return self._sawtooth.read() > 0.5
