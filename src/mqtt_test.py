"""Unit tests for the MQTT topic builder + sample payload."""

from datetime import UTC, datetime

from build import Config, LogLevel, Mode
from src.mqtt import FloatSample, dynamic_line_rating_topic, to_rfc3339

_TEST_CONFIG = Config(
    log_level=LogLevel.DEBUG,
    mqtt_host="10.0.0.1",
    wifi_ssid="test",
    mode=Mode.LOCAL,
    site_id="test_site",
    device_id="test_rtu",
)


def test_dynamic_line_rating_topic_builds_canonical_path() -> None:
    """Topic follows ADR-002's 6-segment measurements shape."""
    actual = dynamic_line_rating_topic(_TEST_CONFIG)
    expected = "sites/test_site/devices/test_rtu/measurements/dynamic_line_rating/amps"
    assert actual == expected


def test_float_sample_serializes_ts_and_value() -> None:
    """FloatSample round-trips to the ADR-002 {ts, value} wire shape."""
    sample = FloatSample(ts="2026-09-20T12:00:00Z", value=612.3)
    assert sample.model_dump() == {"ts": "2026-09-20T12:00:00Z", "value": 612.3}


def test_to_rfc3339_formats_with_z_suffix() -> None:
    """ADR-002 requires RFC3339 with a literal Z suffix, not +00:00."""
    dt = datetime(2026, 9, 20, 12, 0, 0, tzinfo=UTC)
    assert to_rfc3339(dt) == "2026-09-20T12:00:00Z"
