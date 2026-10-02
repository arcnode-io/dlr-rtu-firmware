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
    """Build the utility-namespace topic for IEEE 738 line rating.

    The RTU is the utility's equipment on the utility's conductor, outside
    the EMS (edp-api f19e44b dropped the line_rating device template on this
    reasoning), so the topic carries no site_id. Contract with
    mock-derms-dispatch-api's DlrRatingSubscriber (commit 1a98578).

    Args:
        config: Full app config -- carries device_id.

    Returns:
        The topic string to publish dynamic line rating samples to.
    """
    return f"utility/dlr/{config.device_id}/dynamic_line_rating/amps"


def mqtt_credentials() -> tuple[str | None, str | None]:
    """Read broker auth from env vars, per template-secrets.env.

    Local/CI brokers have no RBAC and stay anonymous by default. Demo/prod
    brokers (File RBAC, no Allow-All) reject anonymous connects and need
    these set at deploy time.

    Returns:
        (username, password) -- both None when unset (anonymous connect).
    """
    return os.environ.get("MQTT_USERNAME"), os.environ.get("MQTT_PASSWORD")


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
    username, password = mqtt_credentials()

    logging.info(f"Connecting to MQTT broker at {mqtt_host}:{mqtt_port}")

    return aiomqtt.Client(
        hostname=mqtt_host,
        port=mqtt_port,
        identifier="circuitpython",
        username=username,
        password=password,
    )
