"""NMEA 0183 anemometer driver.

Wire format: standard NMEA `$..MWV` (Wind Speed and Angle) sentence. Both the
high-wind variant (Calypso ULP STD, talker `II`) and the low-wind variant
(Vaisala WMT702, talker `WI`) speak this format when bench-configured at the
depot — see `project_anemometer_sku.md` and `theory.ipynb` §6.

Sentence shape:

    $XXMWV,<angle>,R,<speed>,M,A*hh

    XX      talker prefix (II / WI / etc.) — ignored
    angle   wind direction in degrees (0…359.9), R = relative to sensor north
    speed   wind speed numeric
    unit    K = km/h, M = m/s, N = knots
    A       status (A = valid, V = void)
    *hh     XOR checksum over all bytes between '$' and '*'

Parser is talker-agnostic per Q9 — we don't distinguish vendors in firmware;
the bench provisioning step (Q12) homogenises wire output across both SKUs.

Failure modes (Q10): every error class returns `None`. The upstream
`dlr-rtu-firmware/src/app.py` collapses None into `V_w = 0.0` (Q15) so
the IEEE 738 layer falls back to natural-convection-only ampacity = static
rating. Same conservative path used for the icing-fallback policy.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Protocol

from src.sensors.anemometer import WindReading

_log = logging.getLogger(__name__)

# `$..MWV,<angle>,<ref>,<speed>,<unit>,<status>*<hh>` plus optional CR/LF
_MWV_RE = re.compile(
    rb"^\$([A-Z]{2})MWV,"
    rb"([0-9.]+),"
    rb"([RT]),"
    rb"([0-9.]+),"
    rb"([KMN]),"
    rb"([AV])"
    rb"\*([0-9A-Fa-f]{2})\s*$"
)

# Convert reported speed unit → m/s
_SPEED_FACTOR_TO_MPS = {
    b"M": 1.0,  # already m/s
    b"K": 1.0 / 3.6,  # km/h → m/s
    b"N": 0.5144444,  # knots → m/s
}

_MAX_REASONABLE_SPEED_MPS = (
    90.0  # WMT702 max range = 90 m/s; anything beyond = bad parse
)
_MAX_REASONABLE_ANGLE_DEG = 360.0


def _nmea_checksum(payload: bytes) -> int:
    """XOR every byte of the NMEA payload (between '$' and '*' exclusive)."""
    cs = 0
    for b in payload:
        cs ^= b
    return cs


def parse_mwv(sentence: bytes) -> WindReading | None:
    """Parse one `$..MWV` sentence → WindReading. Return None on any error.

    All NMEA error classes funnel into a single return-None path so the
    upstream fallback policy (V_w = 0 → static rating) is one branch.
    """
    if not sentence:
        return None

    m = _MWV_RE.match(sentence.strip())
    if not m:
        _log.debug("nmea: malformed MWV sentence: %r", sentence)
        return None

    talker, angle_b, _ref, speed_b, unit, status, given_cs = m.groups()

    # XOR checksum over everything between '$' and '*'
    body = sentence.strip().split(b"*", 1)[0].lstrip(b"$")
    actual_cs = _nmea_checksum(body)
    if actual_cs != int(given_cs, 16):
        _log.debug("nmea: checksum %02X != given %s", actual_cs, given_cs)
        return None

    if status != b"A":
        _log.debug("nmea: status void (talker=%s)", talker)
        return None

    try:
        angle = float(angle_b)
        speed_native = float(speed_b)
    except ValueError:
        _log.debug("nmea: numeric parse failed: %r", sentence)
        return None

    if angle < 0.0 or angle >= _MAX_REASONABLE_ANGLE_DEG:
        return None

    factor = _SPEED_FACTOR_TO_MPS.get(unit)
    if factor is None:
        return None

    speed_mps = speed_native * factor
    if speed_mps < 0.0 or speed_mps > _MAX_REASONABLE_SPEED_MPS:
        return None

    return WindReading(speed_mps=speed_mps, direction_deg=angle)


class _LineSource(Protocol):
    """Anything that yields one NMEA sentence per `read_line()` call."""

    def read_line(self) -> bytes | None: ...


@dataclass(frozen=True)
class NmeaWind:
    """Real anemometer driver: read one line from RS-485 serial, parse MWV.

    Construct with a configured serial wrapper. The driver is pure logic
    over the line source — keeps the I/O surface narrow for testing.
    """

    line_source: _LineSource

    def read(self) -> WindReading | None:
        """Read latest NMEA line. Return None on any failure (timeout, void
        status, bad checksum, parse error). Upstream maps None → V_w = 0.
        """
        line = self.line_source.read_line()
        if line is None:
            return None
        return parse_mwv(line)


class PyserialLineSource:
    """Wraps `pyserial.Serial` with a single read_line() method.

    Lazy-imports pyserial so the driver remains importable on dev/CI
    machines without the package installed (same pattern as `DhtReal`).
    """

    def __init__(
        self,
        port: str = "/dev/ttyAMA2",  # CM4 UART2 — GPIO0/1 per dlr-pcb som.py
        baud: int = 4800,  # NMEA default per Calypso datasheet
        timeout_s: float = 2.0,  # one frame at 1 Hz + slack
    ) -> None:
        """Open the RS-485 serial port at given baud."""
        import serial  # type: ignore[import-not-found]

        self._ser = serial.Serial(
            port=port,
            baudrate=baud,
            timeout=timeout_s,
            bytesize=8,
            parity="N",
            stopbits=1,
        )

    def read_line(self) -> bytes | None:
        """Return one '\\n'-terminated line or None on timeout."""
        line = self._ser.readline()
        if not line:
            return None
        return line
