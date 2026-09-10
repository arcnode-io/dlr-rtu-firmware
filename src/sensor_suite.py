"""Per-mode sensor factory.

Centralizes the "which driver per sensor for this mode" decision. The rest
of the app receives a `SensorSuite` and never knows whether a reading came
from real hardware or a sim sawtooth.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from build import Mode
from src.sensors.anemometer import WindConstant, WindReading, WindSim
from src.sensors.base import ConstantSim
from src.sensors.dht import DhtReading, DhtSim
from src.sensors.rain import RainSim
from src.sensors.solar import SolarSim
from src.sensors.thermal import ConductorTempSim

# DEMO mode holds every input except DHT constant -- see ConstantSim's
# docstring. Mid-range values so the frozen inputs don't zero out the
# rating (e.g. solar heat alone exceeding available cooling).
_DEMO_CONDUCTOR_TEMP_C = 60.0
_DEMO_SOLAR_W_PER_M2 = 500.0
_DEMO_WIND_SPEED_MPS = 3.0
_DEMO_WIND_DIRECTION_DEG = 90.0


class _DhtReader(Protocol):
    """Anything that can produce a DhtReading on demand."""

    def read(self) -> DhtReading: ...


class _ConductorTempReader(Protocol):
    def read(self) -> float: ...


class _SolarReader(Protocol):
    def read(self) -> float: ...


class _RainReader(Protocol):
    def read(self) -> bool: ...


class _WindReader(Protocol):
    """Wind drivers may return None on invalid (cold / iced / void status /
    timeout / bad checksum). Upstream collapses None → V_w = 0 fallback."""

    def read(self) -> WindReading | None: ...


@dataclass(frozen=True)
class SensorSuite:
    """All five physical sensors as a bundle. The reader objects are
    duck-typed protocols so sim and real drivers swap freely.
    """

    dht: _DhtReader
    conductor_temp: _ConductorTempReader
    solar: _SolarReader
    rain: _RainReader
    wind: _WindReader


def build_sensor_suite(mode: Mode) -> SensorSuite:
    """Pick a driver per sensor based on the deployment mode.

    Today only DHT22 has a real driver. The rest are sim across all modes
    until each sensor's real driver lands (FLIR Lepton thermal, SI1145
    solar, YL-83 rain, Calypso ULP wind).

    DEMO mode additionally holds conductor_temp/solar/wind constant instead
    of sawtoothing: the point of DEMO is watching the rating react to a real
    DHT input (e.g. heating it by hand) on camera, and every other input
    stepping every tick regardless would swamp that signal.
    """
    if mode == Mode.DEMO:
        # Lazy import — adafruit_dht needs GPIO + only works on the Pi.
        from src.sensors.dht import DhtReal

        return SensorSuite(
            dht=DhtReal(),
            conductor_temp=ConstantSim(_DEMO_CONDUCTOR_TEMP_C),
            solar=ConstantSim(_DEMO_SOLAR_W_PER_M2),
            rain=RainSim(),
            wind=WindConstant(
                speed_mps=_DEMO_WIND_SPEED_MPS,
                direction_deg=_DEMO_WIND_DIRECTION_DEG,
            ),
        )
    return SensorSuite(
        dht=DhtSim(),
        conductor_temp=ConductorTempSim(),
        solar=SolarSim(),
        rain=RainSim(),
        wind=WindSim(),
    )
