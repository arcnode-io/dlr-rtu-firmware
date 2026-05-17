"""Sensor abstraction layer.

Each sensor has a sim driver (deterministic sawtooth) and, where hardware
exists, a real driver behind the same interface. The mode env (`local | demo
| ci`) picks the driver at boot.

DHT22 is the only sensor with real hardware today (on the Pi); everything
else is sim-only until the corresponding driver lands.
"""

from src.sensors.base import SawtoothSim

__all__ = ["SawtoothSim"]
