"""MQTT client for publishing sensor data."""

import logging
import os
from datetime import datetime

import aiomqtt
from pydantic import BaseModel

from build import CONFIG, Config


class FloatSample(BaseModel):
    """ADR-002 §6 wire shape for a measurements-family float sample."""

    ts: str
    """RFC3339/ISO8601 timestamp with a literal Z suffix (ADR-002 §5)."""
    value: float


def to_rfc3339(dt: datetime) -> str:
    """Format a UTC datetime as RFC3339 with a Z suffix (not +00:00).

    Args:
        dt: A timezone-aware UTC datetime.

    Returns:
        RFC3339 string, e.g. "2026-09-20T12:00:00Z".
    """
    return dt.isoformat(timespec="seconds").replace("+00:00", "Z")


def dynamic_line_rating_topic(config: Config) -> str:
    """Build the canonical measurements topic for IEEE 738 line rating.

    Per ADR-002 §2 (6-segment measurements topic) and edp-api's
    device_templates/leaf/line_rating.yaml (measurement=dynamic_line_rating,
    unit=amps).

    Args:
        config: Full app config -- carries site_id/device_id.

    Returns:
        The topic string to publish dynamic line rating samples to.
    """
    return (
        f"sites/{config.site_id}/devices/{config.device_id}"
        "/measurements/dynamic_line_rating/amps"
    )


async def get_mqtt_client() -> aiomqtt.Client:
    """
    Create MQTT client configured for broker connection.

    Uses configuration from build.py for broker host and port.
    For integration tests, uses localhost when MQTT_PORT env var is set.

    Returns:
        Configured aiomqtt.Client instance (not yet connected)

    Example:
        >>> async with await get_mqtt_client() as client:
        ...     await client.publish("test/temp/F", payload=72.5)
    """
    # Read MQTT_PORT dynamically to support integration tests with dynamic ports
    mqtt_port = int(os.environ.get("MQTT_PORT", "1883"))
    # Reason: MQTT_HOST override needed when broker runs on a different machine (e.g. dev machine during HIL tests)
    mqtt_host = os.environ.get("MQTT_HOST", CONFIG.mqtt_host)

    logging.info(f"Connecting to MQTT broker at {mqtt_host}:{mqtt_port}")

    return aiomqtt.Client(
        hostname=mqtt_host, port=mqtt_port, identifier="circuitpython"
    )
