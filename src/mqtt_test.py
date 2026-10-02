"""Unit tests for the MQTT topic builder + sample payload."""

from datetime import UTC, datetime

import pytest

from build import Config, LogLevel, Mode
from src.mqtt import (
    FloatSample,
    dynamic_line_rating_topic,
    mqtt_credentials,
    to_rfc3339,
)

_TEST_CONFIG = Config(
    log_level=LogLevel.DEBUG,
    mqtt_host="10.0.0.1",
    wifi_ssid="test",
    mode=Mode.LOCAL,
    device_id="test_rtu",
)


def test_dynamic_line_rating_topic_builds_utility_path() -> None:
    """Topic carries no site_id -- the RTU is utility equipment, outside the EMS."""
    actual = dynamic_line_rating_topic(_TEST_CONFIG)
    expected = "utility/dlr/test_rtu/dynamic_line_rating/amps"
    assert actual == expected


def test_float_sample_serializes_ts_and_value() -> None:
    """FloatSample round-trips to the ADR-002 {ts, value} wire shape."""
    sample = FloatSample(ts="2026-09-20T12:00:00Z", value=612.3)
    assert sample.model_dump() == {"ts": "2026-09-20T12:00:00Z", "value": 612.3}


def test_to_rfc3339_formats_with_z_suffix() -> None:
    """ADR-002 requires RFC3339 with a literal Z suffix, not +00:00."""
    dt = datetime(2026, 9, 20, 12, 0, 0, tzinfo=UTC)
    assert to_rfc3339(dt) == "2026-09-20T12:00:00Z"


def test_mqtt_credentials_reads_env_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    """Broker auth (demo/prod) comes from env vars, not cfg.yml."""
    monkeypatch.setenv("MQTT_USERNAME", "dlr_rtu")
    monkeypatch.setenv("MQTT_PASSWORD", "hunter2")
    assert mqtt_credentials() == ("dlr_rtu", "hunter2")


def test_mqtt_credentials_defaults_to_anonymous(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Local/CI brokers have no RBAC -- unset env vars mean anonymous connect."""
    monkeypatch.delenv("MQTT_USERNAME", raising=False)
    monkeypatch.delenv("MQTT_PASSWORD", raising=False)
    assert mqtt_credentials() == (None, None)
