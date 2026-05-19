"""NMEA $..MWV parser tests.

Per Q11 we validate against synthetic fixtures spanning both supported
talker prefixes (`II` Calypso, `WI` Vaisala WMT702) plus every documented
error class (void status, bad checksum, truncated frame, out-of-range
speed/angle, unknown speed unit, gibberish). All error classes funnel
into `parse_mwv(...) == None` so the upstream fallback policy (V_w = 0)
has a single branch to handle (Q15).

Checksums are real XOR-of-payload values computed by hand against
NMEA 0183 §6.2.4. Don't "fix" them.
"""

from __future__ import annotations

from src.sensors.nmea_anemometer import NmeaWind, parse_mwv

# -----------------------------------------------------------------------
# Pure parser (parse_mwv) — fixtures cover every error class
# -----------------------------------------------------------------------


def test_parse_golden_calypso() -> None:
    """Calypso ULP STD datasheet example: $IIMWV,316,R,06.9,N,A*18.

    Talker `II`, angle 316°, speed 6.9 knots = 3.55 m/s.
    """
    r = parse_mwv(b"$IIMWV,316,R,06.9,N,A*18\r\n")
    assert r is not None
    assert r.direction_deg == 316.0
    assert abs(r.speed_mps - 6.9 * 0.5144444) < 1e-6


def test_parse_golden_wmt702() -> None:
    """Vaisala WMT702 talker `WI`: $WIMWV,090.0,R,12.3,N,A*1A.

    Different talker, same fields. Driver must be talker-agnostic (Q9).
    """
    r = parse_mwv(b"$WIMWV,090.0,R,12.3,N,A*1A\r\n")
    assert r is not None
    assert r.direction_deg == 90.0
    assert abs(r.speed_mps - 12.3 * 0.5144444) < 1e-6


def test_parse_speed_unit_mps() -> None:
    """Unit `M` (m/s) passes through unchanged."""
    # IIMWV,000.0,R,05.0,M,A → recomputed checksum
    r = parse_mwv(b"$IIMWV,000.0,R,05.0,M,A*0B\r\n")
    assert r is not None
    assert abs(r.speed_mps - 5.0) < 1e-6


def test_parse_speed_unit_kmh() -> None:
    """Unit `K` (km/h) converts: 36 km/h = 10 m/s."""
    r = parse_mwv(b"$IIMWV,000.0,R,036.0,K,A*3D\r\n")
    assert r is not None
    assert abs(r.speed_mps - 10.0) < 1e-6


def test_parse_void_status() -> None:
    """Status field 'V' (void) → None per Q10 single-fallback policy."""
    r = parse_mwv(b"$IIMWV,316,R,06.9,N,V*0F\r\n")
    assert r is None


def test_parse_bad_checksum() -> None:
    """Computed XOR mismatch → None (line noise / EMI / cable corruption)."""
    r = parse_mwv(b"$IIMWV,316,R,06.9,N,A*FF\r\n")
    assert r is None


def test_parse_truncated_frame() -> None:
    """Sentence cut short before `*hh` → regex won't match → None."""
    r = parse_mwv(b"$IIMWV,316,R\r\n")
    assert r is None


def test_parse_gibberish() -> None:
    """Random bytes (cable cross-talk, wrong baud) → None."""
    r = parse_mwv(b"hello world\r\n")
    assert r is None


def test_parse_angle_out_of_range() -> None:
    """Angle >= 360° → reject (sensor reported nonsense)."""
    r = parse_mwv(b"$IIMWV,400.0,R,05.0,M,A*0F\r\n")
    assert r is None


def test_parse_speed_out_of_range() -> None:
    """Speed > 90 m/s → reject (beyond physical range)."""
    # IIMWV,000.0,R,099.0,M,A* — checksum recomputed
    r = parse_mwv(b"$IIMWV,000.0,R,099.0,M,A*3E\r\n")
    assert r is None


def test_parse_empty_input() -> None:
    """Empty bytes → None (timed-out serial read)."""
    assert parse_mwv(b"") is None


# -----------------------------------------------------------------------
# NmeaWind wrapper — line source injected for testability
# -----------------------------------------------------------------------


class _OneLineSource:
    """Stub line source: returns a fixed line once, then None forever."""

    def __init__(self, line: bytes | None) -> None:
        self._line: bytes | None = line
        self._used = False

    def read_line(self) -> bytes | None:
        if self._used:
            return None
        self._used = True
        return self._line


def test_driver_returns_reading_on_good_line() -> None:
    """Real-driver wrapper passes through valid sentences."""
    drv = NmeaWind(line_source=_OneLineSource(b"$IIMWV,316,R,06.9,N,A*18\r\n"))
    r = drv.read()
    assert r is not None
    assert r.direction_deg == 316.0


def test_driver_returns_none_on_timeout() -> None:
    """Line source returning None (timeout) → driver returns None."""
    drv = NmeaWind(line_source=_OneLineSource(None))
    assert drv.read() is None


def test_driver_returns_none_on_corrupt_line() -> None:
    """Bad checksum bubbles up as None from the wrapper."""
    drv = NmeaWind(line_source=_OneLineSource(b"$IIMWV,316,R,06.9,N,A*FF\r\n"))
    assert drv.read() is None
